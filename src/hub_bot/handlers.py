import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InaccessibleMessage, Message

from hub_bot.apps import get_app
from hub_bot.auth import create_auth_token
from hub_bot.callback_data import AppCallback, HomeCallback, PostboxRefreshCallback
from hub_bot.keyboards import build_app_menu, build_back_to_hub, build_postbox_auth_keyboard
from hub_bot.settings import get_postbox_url
from hub_bot.urls import build_postbox_auth_url

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("start"))
async def start_handler(message: Message) -> None:
    """Handle /start command."""
    response = (
        "The Hub\n\n"
        "Единая точка входа в мои приложения."
    )
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
        await query.message.edit_text(
            "Приложение недоступно.\n\nПопробуйте вернуться в The Hub.",
            reply_markup=build_back_to_hub(),
        )
        return

    # Postbox auth: generate JWT and show URL button
    if app.slug == "postbox":
        postbox_url = get_postbox_url()
        if not postbox_url:
            logger.error("POSTBOX_URL not configured")
            await query.message.edit_text(
                "Postbox сейчас недоступен.\n\nПопробуй немного позже.",
                reply_markup=build_back_to_hub(),
            )
            return

        try:
            # Use Telegram user ID from callback (not from client state)
            user_id = query.from_user.id
            token = create_auth_token(telegram_user_id=user_id, audience="postbox")
            auth_url = build_postbox_auth_url(postbox_url, token)
        except ValueError as e:
            logger.error("Failed to create Postbox auth token: %s", type(e).__name__)
            await query.message.edit_text(
                "Postbox сейчас недоступен.\n\nПопробуй немного позже.",
                reply_markup=build_back_to_hub(),
            )
            return

        response = f"{app.emoji} {app.title}\n\nВсё готово. Ссылка для входа действует 5 минут."
        keyboard = build_postbox_auth_keyboard(auth_url)
        await query.message.edit_text(response, reply_markup=keyboard)
        return

    # Default response for apps without auth integration
    response = f"{app.emoji} {app.title}\n\nИнтеграция с {app.title} будет подключена следующим этапом."
    keyboard = build_back_to_hub()
    await query.message.edit_text(response, reply_markup=keyboard)


@router.callback_query(PostboxRefreshCallback.filter())
async def postbox_refresh_handler(query: CallbackQuery, callback_data: PostboxRefreshCallback) -> None:
    """Handle Postbox auth link refresh callback."""
    await query.answer()

    if not query.message or isinstance(query.message, InaccessibleMessage):
        return

    postbox_url = get_postbox_url()
    if not postbox_url:
        logger.error("POSTBOX_URL not configured")
        await query.message.edit_text(
            "Postbox сейчас недоступен.\n\nПопробуй немного позже.",
            reply_markup=build_back_to_hub(),
        )
        return

    try:
        user_id = query.from_user.id
        token = create_auth_token(telegram_user_id=user_id, audience="postbox")
        auth_url = build_postbox_auth_url(postbox_url, token)
    except ValueError as e:
        logger.error("Failed to refresh Postbox auth token: %s", type(e).__name__)
        await query.message.edit_text(
            "Не смог обновить ссылку.\n\nПопробуй немного позже.",
            reply_markup=build_back_to_hub(),
        )
        return

    response = "Постbox\n\nНовая ссылка готова. Действует 5 минут."
    keyboard = build_postbox_auth_keyboard(auth_url)
    await query.message.edit_text(response, reply_markup=keyboard)


@router.callback_query(HomeCallback.filter())
async def home_handler(query: CallbackQuery, callback_data: HomeCallback) -> None:
    """Handle return to home callback."""
    await query.answer()

    if not query.message or isinstance(query.message, InaccessibleMessage):
        return

    response = (
        "The Hub\n\n"
        "Единая точка входа в мои приложения."
    )
    keyboard = build_app_menu()
    await query.message.edit_text(response, reply_markup=keyboard)
