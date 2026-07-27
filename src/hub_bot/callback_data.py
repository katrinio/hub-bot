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


class FeedbackCallback(CallbackData, prefix="hub"):
    """Callback for opening feedback form."""

    action: str = "feedback"
    app: str


class FeedbackCancelCallback(CallbackData, prefix="hub"):
    """Callback for cancelling feedback form."""

    action: str = "feedback_cancel"
