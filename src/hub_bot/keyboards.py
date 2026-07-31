from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from hub_bot.apps import APPS, HubApp
from hub_bot.callback_data import (
    AppCallback,
    FeedbackCallback,
    FeedbackCancelCallback,
    HomeCallback,
    PostboxRefreshCallback,
)


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


def build_postbox_auth_keyboard(auth_url: str) -> InlineKeyboardMarkup:
    """Build inline keyboard for Postbox auth with URL button and refresh link.

    Args:
        auth_url: Full URL to Postbox /auth/hub endpoint with JWT token

    Returns:
        InlineKeyboardMarkup with open, refresh, and back buttons.
    """
    open_button = InlineKeyboardButton(
        text="Открыть Postbox ↗",
        url=auth_url,
    )
    refresh_button = InlineKeyboardButton(
        text="🔄 Обновить ссылку",
        callback_data=PostboxRefreshCallback().pack(),
    )
    feedback_button = InlineKeyboardButton(
        text="💬 Обратная связь",
        callback_data=FeedbackCallback(app="postbox").pack(),
    )
    back_button = InlineKeyboardButton(
        text="← The Hub",
        callback_data=HomeCallback().pack(),
    )
    return InlineKeyboardMarkup(inline_keyboard=[[open_button], [refresh_button], [feedback_button], [back_button]])


def build_app_keyboard(app: HubApp) -> InlineKeyboardMarkup:
    """Build generic inline keyboard for app screen without auth.

    Args:
        app: The HubApp to build keyboard for

    Returns:
        InlineKeyboardMarkup with feedback and back buttons.
    """
    feedback_button = InlineKeyboardButton(
        text="💬 Обратная связь",
        callback_data=FeedbackCallback(app=app.slug).pack(),
    )
    back_button = InlineKeyboardButton(
        text="← The Hub",
        callback_data=HomeCallback().pack(),
    )
    return InlineKeyboardMarkup(inline_keyboard=[[feedback_button], [back_button]])


def build_feedback_form_keyboard() -> InlineKeyboardMarkup:
    """Build inline keyboard for feedback form (cancel button only)."""
    cancel_button = InlineKeyboardButton(
        text="Отмена",
        callback_data=FeedbackCancelCallback().pack(),
    )
    return InlineKeyboardMarkup(inline_keyboard=[[cancel_button]])
