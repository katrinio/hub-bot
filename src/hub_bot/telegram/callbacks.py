from aiogram.filters.callback_data import CallbackData


class AppCallback(CallbackData, prefix="hub"):
    app: str


class HomeCallback(CallbackData, prefix="hub"):
    action: str = "home"


class PostboxRefreshCallback(CallbackData, prefix="hub"):
    action: str = "postbox_refresh"


class FeedbackCallback(CallbackData, prefix="hub"):
    action: str = "feedback"
    app: str


class FeedbackCancelCallback(CallbackData, prefix="hub"):
    action: str = "feedback_cancel"
