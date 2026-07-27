from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InaccessibleMessage, Message

from hub_bot.apps import get_app
from hub_bot.callback_data import AppCallback, HomeCallback
from hub_bot.keyboards import build_app_menu, build_back_to_hub

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

    response = f"{app.emoji} {app.title}\n\nИнтеграция с {app.title} будет подключена следующим этапом."
    keyboard = build_back_to_hub()
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
