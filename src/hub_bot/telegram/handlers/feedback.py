import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InaccessibleMessage, Message
from sqlalchemy.exc import SQLAlchemyError

from hub_bot.core.settings import get_admin_telegram_id, get_postbox_url
from hub_bot.db.connection import get_session
from hub_bot.db.repository import FeedbackRepository
from hub_bot.domain.apps import HubApp, get_app
from hub_bot.services.app_links import build_auth_url_for_user
from hub_bot.telegram.callbacks import FeedbackCallback, FeedbackCancelCallback
from hub_bot.telegram.keyboards import (
    build_app_keyboard,
    build_app_menu,
    build_feedback_form_keyboard,
    build_postbox_auth_keyboard,
)
from hub_bot.telegram.renderers import render_app_screen
from hub_bot.telegram.states import FeedbackForm
from hub_bot.telegram.texts import HOME_TEXT

logger = logging.getLogger(__name__)
router = Router(name=__name__)
MAX_FEEDBACK_LENGTH = 2000


async def _build_return_keyboard(app: HubApp, telegram_user_id: int):  # type: ignore[no-untyped-def]
    """Build an app keyboard, adding a fresh auth link when possible."""
    if not app.auth_path:
        return build_app_keyboard(app)
    postbox_url = get_postbox_url()
    if not postbox_url:
        return build_app_keyboard(app)
    try:
        auth_url = await build_auth_url_for_user(telegram_user_id, app.slug, postbox_url)
    except (ValueError, SQLAlchemyError, RuntimeError):
        return build_app_keyboard(app)
    return build_postbox_auth_keyboard(auth_url)


@router.callback_query(FeedbackCallback.filter())
async def feedback_handler(query: CallbackQuery, callback_data: FeedbackCallback, state: FSMContext) -> None:
    await query.answer()
    if not query.message or isinstance(query.message, InaccessibleMessage):
        return

    app = get_app(callback_data.app)
    if not app:
        await query.message.edit_text(HOME_TEXT, reply_markup=build_app_menu())
        return

    await state.set_state(FeedbackForm.waiting_for_feedback)
    await state.update_data(app_slug=callback_data.app)
    response = (
        f"💬 Обратная связь — {app.title}\n\n"
        "Напиши одним сообщением всё, что хочешь передать:\n"
        "баг, идею, неудобство или просто впечатление.\n\n"
        "Твой Telegram-профиль будет указан вместе с сообщением, чтобы я мог ответить."
    )
    await query.message.edit_text(response, reply_markup=build_feedback_form_keyboard())


@router.message(FeedbackForm.waiting_for_feedback, Command("cancel"))
async def feedback_cancel_command_handler(message: Message, state: FSMContext) -> None:
    if not message.from_user:
        await state.clear()
        return

    app_slug = (await state.get_data()).get("app_slug")
    await state.clear()
    await message.answer("Отмена ✓")
    app = get_app(str(app_slug)) if app_slug else None
    if not app:
        await message.answer(HOME_TEXT, reply_markup=build_app_menu())
        return

    keyboard = await _build_return_keyboard(app, message.from_user.id)
    await message.answer(
        f"{render_app_screen(app)}\n\nСсылка для входа действует 5 минут.",
        reply_markup=keyboard,
    )


@router.message(FeedbackForm.waiting_for_feedback, ~F.text.startswith("/"))
async def feedback_form_handler(message: Message, state: FSMContext, bot: Bot) -> None:
    if not message.from_user:
        await state.clear()
        return
    if not message.text:
        await message.reply("Пока обратную связь можно отправить только текстом.")
        return
    if len(message.text) > MAX_FEEDBACK_LENGTH:
        await message.reply(
            f"Сообщение слишком длинное ({len(message.text)} символов, "
            f"максимум {MAX_FEEDBACK_LENGTH}). Попробуй сократить текст."
        )
        return

    app_slug = (await state.get_data()).get("app_slug")
    app = get_app(str(app_slug) if app_slug else "")
    if not app:
        await message.reply("Приложение больше недоступно. Попробуй позже.")
        await state.clear()
        return

    admin_id = get_admin_telegram_id()
    if not admin_id:
        logger.warning("ADMIN_TELEGRAM_ID not configured, feedback not sent")
        await message.reply("Сейчас обратную связь отправить не получилось. Попробуй позже.")
        await state.clear()
        return

    try:
        async with get_session() as session:
            feedback = await FeedbackRepository.create(
                session,
                telegram_id=message.from_user.id,
                app_id=app.slug,
                message=message.text,
            )
    except ValueError as error:
        logger.error("Feedback validation error: %s", error)
        await message.reply("Ошибка при обработке обратной связи. Попробуй ещё раз.")
        return
    except SQLAlchemyError as error:
        logger.error("Failed to save feedback: %s", type(error).__name__, exc_info=True)
        await message.reply("Ошибка при сохранении обратной связи. Попробуй ещё раз.")
        return

    profile = f"Telegram ID: {message.from_user.id}"
    if message.from_user.username:
        profile += f"\nUsername: @{message.from_user.username}"
    if message.from_user.first_name:
        profile += f"\nName: {message.from_user.first_name}"
    try:
        await bot.send_message(
            chat_id=admin_id,
            text=f"💬 Feedback · {app.title}\n\n{message.text}\n\nFrom:\n{profile}",
        )
    except Exception as error:
        logger.error("Failed to notify admin about feedback id=%s: %s", feedback.id, type(error).__name__)

    await message.reply(f"Спасибо! Получил обратную связь по {app.title} 🙌")
    await state.clear()
    keyboard = await _build_return_keyboard(app, message.from_user.id)
    await message.answer(
        f"{render_app_screen(app)}\n\nВернёмся к приложению?",
        reply_markup=keyboard,
    )


@router.callback_query(FeedbackCancelCallback.filter())
async def feedback_cancel_handler(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    if not query.message or isinstance(query.message, InaccessibleMessage):
        return

    app_slug = (await state.get_data()).get("app_slug")
    await state.clear()
    app = get_app(str(app_slug)) if app_slug else None
    if not app:
        await query.message.edit_text(HOME_TEXT, reply_markup=build_app_menu())
        return

    keyboard = await _build_return_keyboard(app, query.from_user.id)
    await query.message.edit_text(
        f"{render_app_screen(app)}\n\nСсылка для входа действует 5 минут.",
        reply_markup=keyboard,
    )
