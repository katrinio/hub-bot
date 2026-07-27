from aiogram.fsm.state import State, StatesGroup


class FeedbackForm(StatesGroup):
    """States for feedback form FSM."""

    waiting_for_feedback = State()
