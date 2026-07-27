from aiogram.filters.callback_data import CallbackData


class AppCallback(CallbackData, prefix="hub"):
    """Callback for app selection."""

    app: str


class HomeCallback(CallbackData, prefix="hub"):
    """Callback for returning to home menu."""

    action: str = "home"


class PostboxRefreshCallback(CallbackData, prefix="hub"):
    """Callback for refreshing Postbox auth link."""

    action: str = "postbox_refresh"
