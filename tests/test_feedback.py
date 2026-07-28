import os
from unittest.mock import AsyncMock

import pytest
from aiogram.fsm.context import FSMContext

from hub_bot.callback_data import FeedbackCallback, FeedbackCancelCallback
from hub_bot.handlers import (
    feedback_cancel_handler,
    feedback_form_handler,
    feedback_handler,
)
from hub_bot.states import FeedbackForm


@pytest.mark.asyncio
async def test_feedback_button_appears_in_app_keyboard() -> None:
    """Test that HubApp supports feedback button."""
    from hub_bot.keyboards import build_postbox_auth_keyboard

    keyboard = build_postbox_auth_keyboard("https://test.com/auth?token=xyz")
    buttons = keyboard.inline_keyboard

    # Should have: open, refresh, feedback, back
    assert len(buttons) == 4

    # Feedback button should be third
    feedback_button = buttons[2][0]
    assert "💬" in feedback_button.text
    assert "Обратная связь" in feedback_button.text


@pytest.mark.asyncio
async def test_feedback_callback_contains_app_slug() -> None:
    """Test that feedback callback contains correct app slug."""
    callback = FeedbackCallback(app="postbox")
    packed = callback.pack()

    assert "postbox" in packed
    assert "feedback" in packed


@pytest.mark.asyncio
async def test_feedback_handler_accepts_valid_app() -> None:
    """Test that feedback handler accepts valid app slug."""
    query = AsyncMock()
    query.message = AsyncMock()
    query.message.edit_text = AsyncMock()
    query.answer = AsyncMock()

    state = AsyncMock(spec=FSMContext)
    state.set_state = AsyncMock()
    state.update_data = AsyncMock()

    callback_data = FeedbackCallback(app="postbox")
    await feedback_handler(query, callback_data, state)

    query.answer.assert_called_once()
    state.set_state.assert_called_once_with(FeedbackForm.waiting_for_feedback)
    state.update_data.assert_called_once_with(app_slug="postbox")

    call_args = query.message.edit_text.call_args
    response_text = call_args[0][0]
    assert "Обратная связь" in response_text
    assert "Postbox" in response_text


@pytest.mark.asyncio
async def test_feedback_handler_rejects_unknown_app() -> None:
    """Test that feedback handler safely returns to hub menu for unknown app."""
    query = AsyncMock()
    query.message = AsyncMock()
    query.message.edit_text = AsyncMock()
    query.answer = AsyncMock()

    state = AsyncMock(spec=FSMContext)

    callback_data = FeedbackCallback(app="unknown_app")
    await feedback_handler(query, callback_data, state)

    query.answer.assert_called_once()
    query.message.edit_text.assert_called_once()
    call_args = query.message.edit_text.call_args
    response_text = call_args[0][0]

    # Should return to hub menu, not crash
    assert "The Hub" in response_text
    assert "Единая точка входа" in response_text


@pytest.mark.asyncio
async def test_feedback_form_stores_app_slug() -> None:
    """Test that app slug is stored in FSM state."""
    query = AsyncMock()
    query.message = AsyncMock()
    query.message.edit_text = AsyncMock()
    query.answer = AsyncMock()

    state = AsyncMock(spec=FSMContext)
    state.set_state = AsyncMock()
    state.update_data = AsyncMock()

    callback_data = FeedbackCallback(app="postbox")
    await feedback_handler(query, callback_data, state)

    # Verify app_slug is stored
    state.update_data.assert_called_once()
    call_kwargs = state.update_data.call_args[1]
    assert call_kwargs["app_slug"] == "postbox"


@pytest.mark.asyncio
async def test_feedback_form_accepts_text_message() -> None:
    """Test that text feedback is accepted and sent to admin."""
    os.environ["HUB_ADMIN_TELEGRAM_ID"] = "123456789"

    try:
        message = AsyncMock()
        message.text = "This is a bug report"
        message.from_user = AsyncMock()
        message.from_user.id = 987654321
        message.from_user.username = "testuser"
        message.from_user.first_name = "Test"
        message.reply = AsyncMock()
        message.answer = AsyncMock()

        state = AsyncMock(spec=FSMContext)
        state.get_data = AsyncMock(return_value={"app_slug": "postbox"})
        state.clear = AsyncMock()

        bot = AsyncMock()
        bot.send_message = AsyncMock()

        await feedback_form_handler(message, state, bot)

        # Verify admin received message
        bot.send_message.assert_called_once()
        call_kwargs = bot.send_message.call_args.kwargs
        assert call_kwargs["chat_id"] == 123456789
        admin_message = call_kwargs["text"]

        # Check message format
        assert "Feedback" in admin_message
        assert "Postbox" in admin_message
        assert "This is a bug report" in admin_message
        assert "987654321" in admin_message
        assert "@testuser" in admin_message

        # Verify success message
        message.reply.assert_called_once()
        reply_text = message.reply.call_args[0][0]
        assert "Спасибо" in reply_text
        assert "Postbox" in reply_text

        # Verify state cleared
        state.clear.assert_called_once()
    finally:
        os.environ.pop("HUB_ADMIN_TELEGRAM_ID", None)


@pytest.mark.asyncio
async def test_feedback_form_rejects_non_text_message() -> None:
    """Test that non-text messages are rejected gracefully."""
    message = AsyncMock()
    message.text = None  # Photo, voice, etc.
    message.reply = AsyncMock()

    state = AsyncMock(spec=FSMContext)
    bot = AsyncMock()

    await feedback_form_handler(message, state, bot)

    # Should not send to admin
    bot.send_message.assert_not_called()

    # Should ask for text
    message.reply.assert_called_once()
    reply_text = message.reply.call_args[0][0]
    assert "текстом" in reply_text.lower()


@pytest.mark.asyncio
async def test_feedback_form_rejects_too_long_text() -> None:
    """Test that feedback exceeding length limit is rejected."""
    message = AsyncMock()
    message.text = "x" * 2001  # Exceeds max_feedback_length
    message.reply = AsyncMock()

    state = AsyncMock(spec=FSMContext)
    bot = AsyncMock()

    await feedback_form_handler(message, state, bot)

    # Should not send to admin
    bot.send_message.assert_not_called()

    # Should ask to shorten
    message.reply.assert_called_once()
    reply_text = message.reply.call_args[0][0]
    assert "слишком длинное" in reply_text.lower()


@pytest.mark.asyncio
async def test_feedback_without_admin_id_shows_error() -> None:
    """Test that missing HUB_ADMIN_TELEGRAM_ID is handled safely."""
    os.environ.pop("HUB_ADMIN_TELEGRAM_ID", None)

    try:
        message = AsyncMock()
        message.text = "Feedback text"
        message.from_user = AsyncMock()
        message.from_user.id = 987654321
        message.reply = AsyncMock()

        state = AsyncMock(spec=FSMContext)
        state.get_data = AsyncMock(return_value={"app_slug": "postbox"})
        state.clear = AsyncMock()

        bot = AsyncMock()
        bot.send_message = AsyncMock()

        await feedback_form_handler(message, state, bot)

        # Should not crash, should show error
        bot.send_message.assert_not_called()
        message.reply.assert_called_once()
        reply_text = message.reply.call_args[0][0]
        assert "не получилось" in reply_text.lower()

        state.clear.assert_called_once()
    finally:
        pass


@pytest.mark.asyncio
async def test_feedback_admin_message_includes_user_id() -> None:
    """Test that admin message includes Telegram user ID."""
    os.environ["HUB_ADMIN_TELEGRAM_ID"] = "123456789"

    try:
        message = AsyncMock()
        message.text = "Bug report"
        message.from_user = AsyncMock()
        message.from_user.id = 111222333
        message.from_user.username = None
        message.from_user.first_name = None
        message.reply = AsyncMock()
        message.answer = AsyncMock()

        state = AsyncMock(spec=FSMContext)
        state.get_data = AsyncMock(return_value={"app_slug": "postbox"})
        state.clear = AsyncMock()

        bot = AsyncMock()
        bot.send_message = AsyncMock()

        await feedback_form_handler(message, state, bot)

        call_kwargs = bot.send_message.call_args.kwargs
        admin_message = call_kwargs["text"]

        assert "111222333" in admin_message
    finally:
        os.environ.pop("HUB_ADMIN_TELEGRAM_ID", None)


@pytest.mark.asyncio
async def test_feedback_admin_message_includes_username_if_exists() -> None:
    """Test that admin message includes username only if it exists."""
    os.environ["HUB_ADMIN_TELEGRAM_ID"] = "123456789"

    try:
        message = AsyncMock()
        message.text = "Feedback"
        message.from_user = AsyncMock()
        message.from_user.id = 111222333
        message.from_user.username = "realuser"
        message.from_user.first_name = "John"
        message.reply = AsyncMock()
        message.answer = AsyncMock()

        state = AsyncMock(spec=FSMContext)
        state.get_data = AsyncMock(return_value={"app_slug": "postbox"})
        state.clear = AsyncMock()

        bot = AsyncMock()
        bot.send_message = AsyncMock()

        await feedback_form_handler(message, state, bot)

        call_kwargs = bot.send_message.call_args.kwargs
        admin_message = call_kwargs["text"]

        assert "@realuser" in admin_message
    finally:
        os.environ.pop("HUB_ADMIN_TELEGRAM_ID", None)


@pytest.mark.asyncio
async def test_feedback_cancel_clears_state() -> None:
    """Test that cancel button clears FSM state."""
    os.environ["POSTBOX_URL"] = "https://postbox.finpipe.net"
    os.environ["HUB_AUTH_SECRET"] = "test-secret"

    try:
        query = AsyncMock()
        query.message = AsyncMock()
        query.message.edit_text = AsyncMock()
        query.answer = AsyncMock()
        query.from_user = AsyncMock()
        query.from_user.id = 123456789

        state = AsyncMock(spec=FSMContext)
        state.get_data = AsyncMock(return_value={"app_slug": "postbox"})
        state.clear = AsyncMock()

        await feedback_cancel_handler(query, state)

        state.clear.assert_called_once()
        query.answer.assert_called_once()
    finally:
        os.environ.pop("POSTBOX_URL", None)
        os.environ.pop("HUB_AUTH_SECRET", None)


@pytest.mark.asyncio
async def test_feedback_cancel_returns_to_app() -> None:
    """Test that cancel returns user to app screen."""
    query = AsyncMock()
    query.message = AsyncMock()
    query.message.edit_text = AsyncMock()
    query.answer = AsyncMock()
    query.from_user = AsyncMock()
    query.from_user.id = 123456789

    state = AsyncMock(spec=FSMContext)
    state.get_data = AsyncMock(return_value={"app_slug": "postbox"})
    state.clear = AsyncMock()

    await feedback_cancel_handler(query, state)

    # Should edit message with app screen
    query.message.edit_text.assert_called_once()
    call_args = query.message.edit_text.call_args
    response_text = call_args[0][0]

    assert "Postbox" in response_text
    state.clear.assert_called_once()


@pytest.mark.asyncio
async def test_feedback_cancel_fallback_to_home_when_app_missing() -> None:
    """Test that cancel returns to home if app slug is lost."""
    query = AsyncMock()
    query.message = AsyncMock()
    query.message.edit_text = AsyncMock()
    query.answer = AsyncMock()

    state = AsyncMock(spec=FSMContext)
    state.get_data = AsyncMock(return_value={"app_slug": "unknown"})
    state.clear = AsyncMock()

    await feedback_cancel_handler(query, state)

    call_args = query.message.edit_text.call_args
    response_text = call_args[0][0]

    # Should show home screen
    assert "The Hub" in response_text
    state.clear.assert_called_once()


@pytest.mark.asyncio
async def test_feedback_success_shows_app_screen() -> None:
    """Test that successful feedback shows app screen for return."""
    os.environ["HUB_ADMIN_TELEGRAM_ID"] = "123456789"
    os.environ["POSTBOX_URL"] = "https://postbox.finpipe.net"
    os.environ["HUB_AUTH_SECRET"] = "test-secret"

    try:
        message = AsyncMock()
        message.text = "Great app!"
        message.from_user = AsyncMock()
        message.from_user.id = 987654321
        message.from_user.username = "user"
        message.from_user.first_name = None
        message.reply = AsyncMock()
        message.answer = AsyncMock()

        state = AsyncMock(spec=FSMContext)
        state.get_data = AsyncMock(return_value={"app_slug": "postbox"})
        state.clear = AsyncMock()

        bot = AsyncMock()
        bot.send_message = AsyncMock()

        await feedback_form_handler(message, state, bot)

        # Should show success
        message.reply.assert_called_once()
        reply_text = message.reply.call_args[0][0]
        assert "Спасибо" in reply_text

        # Should show app screen
        message.answer.assert_called_once()
        answer_text = message.answer.call_args[0][0]
        assert "Postbox" in answer_text
    finally:
        os.environ.pop("HUB_ADMIN_TELEGRAM_ID", None)
        os.environ.pop("POSTBOX_URL", None)
        os.environ.pop("HUB_AUTH_SECRET", None)


@pytest.mark.asyncio
async def test_feedback_delivery_failure_shown_to_user() -> None:
    """Test that delivery failure to admin is handled safely."""
    os.environ["HUB_ADMIN_TELEGRAM_ID"] = "123456789"

    try:
        message = AsyncMock()
        message.text = "Feedback"
        message.from_user = AsyncMock()
        message.from_user.id = 987654321
        message.from_user.username = "user"
        message.from_user.first_name = None
        message.reply = AsyncMock()
        message.answer = AsyncMock()

        state = AsyncMock(spec=FSMContext)
        state.get_data = AsyncMock(return_value={"app_slug": "postbox"})
        state.clear = AsyncMock()

        bot = AsyncMock()
        bot.send_message = AsyncMock(side_effect=Exception("Telegram API error"))

        await feedback_form_handler(message, state, bot)

        # Should NOT claim success
        message.reply.assert_called_once()
        reply_text = message.reply.call_args[0][0]
        assert "не получилось" in reply_text.lower()

        # Should clear state
        state.clear.assert_called_once()

        # Should NOT show app screen after error
        message.answer.assert_not_called()
    finally:
        os.environ.pop("HUB_ADMIN_TELEGRAM_ID", None)


@pytest.mark.asyncio
async def test_feedback_callback_packed_format() -> None:
    """Test that FeedbackCallback packs correctly."""
    callback = FeedbackCallback(app="postbox")
    packed = callback.pack()

    # Should be able to unpack
    assert isinstance(packed, str)
    assert "hub" in packed
    assert "postbox" in packed


@pytest.mark.asyncio
async def test_feedback_cancel_callback_packed_format() -> None:
    """Test that FeedbackCancelCallback packs correctly."""
    callback = FeedbackCancelCallback()
    packed = callback.pack()

    assert isinstance(packed, str)
    assert "hub" in packed
    assert "feedback_cancel" in packed
