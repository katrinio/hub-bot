import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InaccessibleMessage, Message
from sqlalchemy.exc import SQLAlchemyError

from hub_bot.applications.handoff import build_auth_url_for_user
from hub_bot.applications.registry import get_app
from hub_bot.config import get_postbox_url
from hub_bot.telegram.callbacks import AppCallback, HomeCallback, PostboxRefreshCallback
from hub_bot.telegram.keyboards import (
    build_app_keyboard,
    build_app_menu,
    build_back_to_hub,
    build_postbox_auth_keyboard,
)
from hub_bot.telegram.texts import HOME_TEXT
from hub_bot.telegram.views import render_app_screen

logger = logging.getLogger(__name__)
router = Router(name=__name__)

@router.message(Command("start"))
async def start_handler(message: Message) -> None:
    await message.answer(HOME_TEXT, reply_markup=build_app_menu())


@router.callback_query(AppCallback.filter())
async def app_handler(query: CallbackQuery, callback_data: AppCallback) -> None:
    await query.answer()
    if not query.message or isinstance(query.message, InaccessibleMessage):
        return

    app = get_app(callback_data.app)
    if not app:
        await query.message.edit_text(HOME_TEXT, reply_markup=build_app_menu())
        return

    if not app.auth_path:
        screen = render_app_screen(app)
        await query.message.edit_text(
            f"{screen}\n\nИнтеграция будет подключена в следующем обновлении.",
            reply_markup=build_app_keyboard(app),
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
        auth_url = await build_auth_url_for_user(query.from_user.id, app.slug, postbox_url)
    except (ValueError, SQLAlchemyError, RuntimeError) as error:
        logger.error("Failed to create auth token for %s: %s", app.slug, type(error).__name__)
        await query.message.edit_text(
            "Приложение сейчас недоступно.\n\nПопробуй немного позже.",
            reply_markup=build_back_to_hub(),
        )
        return

    screen = render_app_screen(app)
    await query.message.edit_text(
        f"{screen}\n\nСсылка для входа действует 5 минут.",
        reply_markup=build_postbox_auth_keyboard(auth_url),
    )


@router.callback_query(PostboxRefreshCallback.filter())
async def postbox_refresh_handler(query: CallbackQuery, callback_data: PostboxRefreshCallback) -> None:
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
        auth_url = await build_auth_url_for_user(query.from_user.id, app.slug, postbox_url)
    except (ValueError, SQLAlchemyError, RuntimeError) as error:
        logger.error("Failed to refresh auth token for %s: %s", app.slug, type(error).__name__)
        await query.message.edit_text(
            "Не смог обновить ссылку.\n\nПопробуй немного позже.",
            reply_markup=build_back_to_hub(),
        )
        return

    screen = render_app_screen(app)
    await query.message.edit_text(
        f"{screen}\n\nСсылка для входа действует 5 минут.",
        reply_markup=build_postbox_auth_keyboard(auth_url),
    )


@router.callback_query(HomeCallback.filter())
async def home_handler(query: CallbackQuery, callback_data: HomeCallback) -> None:
    await query.answer()
    if query.message and not isinstance(query.message, InaccessibleMessage):
        await query.message.edit_text(HOME_TEXT, reply_markup=build_app_menu())
