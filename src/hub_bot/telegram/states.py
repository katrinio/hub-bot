from aiogram.fsm.state import State, StatesGroup


class FeedbackForm(StatesGroup):
    """State machine for feedback collection."""

    waiting_for_feedback = State()
