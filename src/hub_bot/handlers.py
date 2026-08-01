import logging
from datetime import datetime

import pytz
from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InaccessibleMessage, Message
from sqlalchemy.exc import SQLAlchemyError

from hub_bot.apps import get_app
from hub_bot.auth import create_auth_token_for_user
from hub_bot.callback_data import (
    AppCallback,
    FeedbackCallback,
    FeedbackCancelCallback,
    HomeCallback,
    PostboxRefreshCallback,
)
from hub_bot.db import UserRepository
from hub_bot.db.connection import get_session
from hub_bot.keyboards import (
    build_app_keyboard,
    build_app_menu,
    build_back_to_hub,
    build_feedback_form_keyboard,
    build_postbox_auth_keyboard,
)
from hub_bot.renderers import render_app_screen
from hub_bot.settings import (
    get_admin_telegram_id,
    get_app_timezone,
    get_postbox_url,
)
from hub_bot.states import FeedbackForm
from hub_bot.urls import build_postbox_auth_url

logger = logging.getLogger(__name__)

router = Router()


async def _build_auth_url_for_user(telegram_user_id: int, audience: str, postbox_url: str) -> str:
    async with get_session() as session:
        token = await create_auth_token_for_user(session, telegram_user_id=telegram_user_id, audience=audience)
    return build_postbox_auth_url(postbox_url, token)


@router.message(Command("start"))
async def start_handler(message: Message) -> None:
    """Handle /start command."""
    response = "The Hub\n\nЕдиная точка входа в мои приложения."
    keyboard = build_app_menu()
    await message.answer(response, reply_markup=keyboard)


@router.callback_query(AppCallback.filter())
async def app_handler(query: CallbackQuery, callback_data: AppCallback) -> None:
    """Handle app selection callback."""
    await query.answer()

    if not query.message or isinstance(query.message, InaccessibleMessage):
        return

    app = get_app(callback_data.app)
    if not app:
        response = "The Hub\n\nЕдиная точка входа в мои приложения."
        keyboard = build_app_menu()
        await query.message.edit_text(response, reply_markup=keyboard)
        return

    # App with authentication integration
    if app.auth_path:
        postbox_url = get_postbox_url()
        if not postbox_url:
            logger.error("POSTBOX_URL not configured")
            await query.message.edit_text(
                "Приложение сейчас недоступно.\n\nПопробуй немного позже.",
                reply_markup=build_back_to_hub(),
            )
            return

        try:
            # Use Telegram user ID from callback (not from client state)
            user_id = query.from_user.id
            auth_url = await _build_auth_url_for_user(user_id, app.slug, postbox_url)
        except (ValueError, SQLAlchemyError, RuntimeError) as e:
            logger.error("Failed to create auth token for %s: %s", app.slug, type(e).__name__)
            await query.message.edit_text(
                "Приложение сейчас недоступно.\n\nПопробуй немного позже.",
                reply_markup=build_back_to_hub(),
            )
            return

        screen = render_app_screen(app)
        response = f"{screen}\n\nСсылка для входа действует 5 минут."
        keyboard = build_postbox_auth_keyboard(auth_url)
        await query.message.edit_text(response, reply_markup=keyboard)
        return

    # App without authentication (show screen only)
    screen = render_app_screen(app)
    response = f"{screen}\n\nИнтеграция будет подключена в следующем обновлении."
    keyboard = build_app_keyboard(app)
    await query.message.edit_text(response, reply_markup=keyboard)


@router.callback_query(PostboxRefreshCallback.filter())
async def postbox_refresh_handler(query: CallbackQuery, callback_data: PostboxRefreshCallback) -> None:
    """Handle Postbox auth link refresh callback."""
    await query.answer()

    if not query.message or isinstance(query.message, InaccessibleMessage):
        return

    app = get_app("postbox")
    if not app or not app.auth_path:
        logger.error("Postbox app not found")
        await query.message.edit_text(
            "Приложение недоступно.\n\nПопробуй немного позже.",
            reply_markup=build_back_to_hub(),
        )
        return

    postbox_url = get_postbox_url()
    if not postbox_url:
        logger.error("POSTBOX_URL not configured")
        await query.message.edit_text(
            "Приложение сейчас недоступно.\n\nПопробуй немного позже.",
            reply_markup=build_back_to_hub(),
        )
        return

    try:
        user_id = query.from_user.id
        auth_url = await _build_auth_url_for_user(user_id, app.slug, postbox_url)
    except (ValueError, SQLAlchemyError, RuntimeError) as e:
        logger.error("Failed to refresh auth token for %s: %s", app.slug, type(e).__name__)
        await query.message.edit_text(
            "Не смог обновить ссылку.\n\nПопробуй немного позже.",
            reply_markup=build_back_to_hub(),
        )
        return

    screen = render_app_screen(app)
    response = f"{screen}\n\nСсылка для входа действует 5 минут."
    keyboard = build_postbox_auth_keyboard(auth_url)
    await query.message.edit_text(response, reply_markup=keyboard)


@router.callback_query(HomeCallback.filter())
async def home_handler(query: CallbackQuery, callback_data: HomeCallback) -> None:
    """Handle return to home callback."""
    await query.answer()

    if not query.message or isinstance(query.message, InaccessibleMessage):
        return

    response = "The Hub\n\nЕдиная точка входа в мои приложения."
    keyboard = build_app_menu()
    await query.message.edit_text(response, reply_markup=keyboard)


@router.callback_query(FeedbackCallback.filter())
async def feedback_handler(query: CallbackQuery, callback_data: FeedbackCallback, state: FSMContext) -> None:
    """Handle feedback button click."""
    await query.answer()

    if not query.message or isinstance(query.message, InaccessibleMessage):
        return

    # Validate app exists
    app = get_app(callback_data.app)
    if not app:
        response = "The Hub\n\nЕдиная точка входа в мои приложения."
        keyboard = build_app_menu()
        await query.message.edit_text(response, reply_markup=keyboard)
        return

    # Store app slug in FSM state
    await state.set_state(FeedbackForm.waiting_for_feedback)
    await state.update_data(app_slug=callback_data.app)

    response = (
        f"💬 Обратная связь — {app.title}\n\n"
        "Напиши одним сообщением всё, что хочешь передать:\n"
        "баг, идею, неудобство или просто впечатление.\n\n"
        "Твой Telegram-профиль будет указан вместе с сообщением, "
        "чтобы я мог ответить."
    )
    keyboard = build_feedback_form_keyboard()
    await query.message.edit_text(response, reply_markup=keyboard)


@router.message(FeedbackForm.waiting_for_feedback, Command("cancel"))
async def feedback_cancel_command_handler(message: Message, state: FSMContext) -> None:
    """Handle /cancel command during feedback form."""
    if not message.from_user:
        await state.clear()
        return

    data = await state.get_data()
    app_slug = data.get("app_slug")

    await state.clear()
    await message.answer("Отмена ✓")

    if app_slug:
        app = get_app(str(app_slug))
        if app:
            screen = render_app_screen(app)
            response = f"{screen}\n\nСсылка для входа действует 5 минут."
            if app.auth_path:
                postbox_url = get_postbox_url()
                if postbox_url:
                    try:
                        user_id = message.from_user.id
                        auth_url = await _build_auth_url_for_user(user_id, app.slug, postbox_url)
                        keyboard = build_postbox_auth_keyboard(auth_url)
                    except (ValueError, SQLAlchemyError, RuntimeError):
                        keyboard = build_app_keyboard(app)
                else:
                    keyboard = build_app_keyboard(app)
            else:
                keyboard = build_app_keyboard(app)
            await message.answer(response, reply_markup=keyboard)
            return

    # Fallback to home
    response = "The Hub\n\nЕдиная точка входа в мои приложения."
    keyboard = build_app_menu()
    await message.answer(response, reply_markup=keyboard)


@router.message(FeedbackForm.waiting_for_feedback)
async def feedback_form_handler(message: Message, state: FSMContext, bot: Bot) -> None:
    """Handle feedback text submission."""
    if not message.from_user:
        await state.clear()
        return

    # Only accept text messages
    if not message.text:
        await message.reply("Пока обратную связь можно отправить только текстом.")
        return

    # Check feedback length (Telegram limit is 4096, be conservative)
    max_feedback_length = 2000
    if len(message.text) > max_feedback_length:
        await message.reply(
            f"Сообщение слишком длинное ({len(message.text)} символов, "
            f"максимум {max_feedback_length}). "
            f"Попробуй сократить текст."
        )
        return

    data = await state.get_data()
    app_slug = data.get("app_slug")

    # Get app info
    app = get_app(str(app_slug) if app_slug else "")
    if not app:
        await message.reply("Приложение больше недоступно. Попробуй позже.")
        await state.clear()
        return

    # Get admin ID
    admin_id = get_admin_telegram_id()
    if not admin_id:
        logger.warning("ADMIN_TELEGRAM_ID not configured, feedback not sent")
        await message.reply("Сейчас обратную связь отправить не получилось. Попробуй позже.")
        await state.clear()
        return

    # Format admin message
    from_text = f"Telegram ID: {message.from_user.id}"
    if message.from_user.username:
        from_text += f"\nUsername: @{message.from_user.username}"
    if message.from_user.first_name:
        from_text += f"\nName: {message.from_user.first_name}"

    admin_message = f"💬 Feedback · {app.title}\n\n{message.text}\n\nFrom:\n{from_text}"

    # Send to admin
    try:
        await bot.send_message(chat_id=admin_id, text=admin_message)
    except Exception as e:
        logger.error("Failed to send feedback to admin: %s", type(e).__name__)
        await message.reply("Сейчас обратную связь отправить не получилось. Попробуй позже.")
        await state.clear()
        return

    # Success response
    await message.reply(f"Спасибо! Получил обратную связь по {app.title} 🙌")
    await state.clear()

    # Show app screen again
    screen = render_app_screen(app)
    response = f"{screen}\n\nВернёмся к приложению?"
    if app.auth_path:
        postbox_url = get_postbox_url()
        if postbox_url:
            try:
                user_id = message.from_user.id
                auth_url = await _build_auth_url_for_user(user_id, app.slug, postbox_url)
                keyboard = build_postbox_auth_keyboard(auth_url)
            except (ValueError, SQLAlchemyError, RuntimeError):
                keyboard = build_app_keyboard(app)
        else:
            keyboard = build_app_keyboard(app)
    else:
        keyboard = build_app_keyboard(app)
    await message.answer(response, reply_markup=keyboard)


@router.callback_query(FeedbackCancelCallback.filter())
async def feedback_cancel_handler(query: CallbackQuery, state: FSMContext) -> None:
    """Handle cancel button in feedback form."""
    await query.answer()

    if not query.message or isinstance(query.message, InaccessibleMessage):
        return

    data = await state.get_data()
    app_slug = data.get("app_slug")

    await state.clear()

    if app_slug:
        app = get_app(str(app_slug))
        if app:
            screen = render_app_screen(app)
            response = f"{screen}\n\nСсылка для входа действует 5 минут."
            if app.auth_path:
                postbox_url = get_postbox_url()
                if postbox_url:
                    try:
                        user_id = query.from_user.id
                        auth_url = await _build_auth_url_for_user(user_id, app.slug, postbox_url)
                        keyboard = build_postbox_auth_keyboard(auth_url)
                    except (ValueError, SQLAlchemyError, RuntimeError):
                        keyboard = build_app_keyboard(app)
                else:
                    keyboard = build_app_keyboard(app)
            else:
                keyboard = build_app_keyboard(app)
            await query.message.edit_text(response, reply_markup=keyboard)
            return

    # Fallback to home
    response = "The Hub\n\nЕдиная точка входа в мои приложения."
    keyboard = build_app_menu()
    await query.message.edit_text(response, reply_markup=keyboard)


@router.message(Command("stats"))
async def stats_handler(message: Message) -> None:
    """Handle /stats command - show statistics (admin only).

    Statistics include:
    - Total users
    - New users today
    - New users in last 7 days
    - Active users in last 7 days
    """
    admin_id = get_admin_telegram_id()

    if not admin_id or not message.from_user:
        await message.answer("Команда недоступна.")
        return

    if message.from_user.id != admin_id:
        await message.answer("Команда недоступна.")
        return

    try:
        async with get_session() as session:
            total = await UserRepository.count_total(session)
            new_7_days = await UserRepository.count_new_7_days(session)
            active_7_days = await UserRepository.count_active_7_days(session)

            # Calculate "new today" using app timezone
            tz_name = get_app_timezone()
            tz = pytz.timezone(tz_name)
            now_tz = datetime.now(tz)

            new_today = await UserRepository.count_new_today(session, now_tz)

        response = (
            "Статистика The Hub\n\n"
            f"Всего пользователей: {total}\n"
            f"Новых сегодня: {new_today}\n"
            f"Новых за 7 дней: {new_7_days}\n"
            f"Активных за 7 дней: {active_7_days}"
        )
        await message.answer(response)
    except Exception as e:
        logger.error("Error generating stats: %s", type(e).__name__, exc_info=True)
        await message.answer("Ошибка при получении статистики. Попробуйте позже.")
