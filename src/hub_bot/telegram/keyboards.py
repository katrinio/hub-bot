from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from hub_bot.applications.registry import APPS, HubApp
from hub_bot.telegram.callbacks import (
    AppCallback,
    FeedbackCallback,
    FeedbackCancelCallback,
    HomeCallback,
    PostboxRefreshCallback,
)


def build_app_menu() -> InlineKeyboardMarkup:
    """Build the main menu from the application registry."""
    buttons = [
        [InlineKeyboardButton(text=f"{app.emoji} {app.title}", callback_data=AppCallback(app=app.slug).pack())]
        for app in APPS
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_back_to_hub() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="← The Hub", callback_data=HomeCallback().pack())]]
    )


def build_postbox_auth_keyboard(auth_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Открыть Postbox ↗", url=auth_url)],
            [InlineKeyboardButton(text="🔄 Обновить ссылку", callback_data=PostboxRefreshCallback().pack())],
            [InlineKeyboardButton(text="💬 Обратная связь", callback_data=FeedbackCallback(app="postbox").pack())],
            [InlineKeyboardButton(text="← The Hub", callback_data=HomeCallback().pack())],
        ]
    )


def build_app_keyboard(app: HubApp) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Обратная связь", callback_data=FeedbackCallback(app=app.slug).pack())],
            [InlineKeyboardButton(text="← The Hub", callback_data=HomeCallback().pack())],
        ]
    )


def build_feedback_form_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="Отмена", callback_data=FeedbackCancelCallback().pack())
        ]]
    )
