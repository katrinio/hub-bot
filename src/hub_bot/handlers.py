import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InaccessibleMessage, Message

from hub_bot.apps import get_app
from hub_bot.auth import create_auth_token
from hub_bot.callback_data import AppCallback, HomeCallback, PostboxRefreshCallback
from hub_bot.keyboards import build_app_menu, build_back_to_hub, build_postbox_auth_keyboard
from hub_bot.renderers import render_app_screen
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
            token = create_auth_token(telegram_user_id=user_id, audience=app.slug)
            auth_url = build_postbox_auth_url(postbox_url, token)
        except ValueError as e:
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
    keyboard = build_back_to_hub()
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
        token = create_auth_token(telegram_user_id=user_id, audience=app.slug)
        auth_url = build_postbox_auth_url(postbox_url, token)
    except ValueError as e:
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

    response = (
        "The Hub\n\n"
        "Единая точка входа в мои приложения."
    )
    keyboard = build_app_menu()
    await query.message.edit_text(response, reply_markup=keyboard)
