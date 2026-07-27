from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from hub_bot.apps import APPS
from hub_bot.callback_data import AppCallback, HomeCallback


def build_app_menu() -> InlineKeyboardMarkup:
    """Build inline keyboard with registered applications."""
    buttons = []
    for app in APPS:
        button = InlineKeyboardButton(
            text=f"{app.emoji} {app.title}",
            callback_data=AppCallback(app=app.slug).pack(),
        )
        buttons.append([button])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_back_to_hub() -> InlineKeyboardMarkup:
    """Build inline keyboard with back to Hub button."""
    button = InlineKeyboardButton(
        text="← The Hub",
        callback_data=HomeCallback().pack(),
    )
    return InlineKeyboardMarkup(inline_keyboard=[[button]])
