import os
from unittest.mock import AsyncMock

import pytest

from hub_bot.callback_data import AppCallback, HomeCallback
from hub_bot.handlers import app_handler, home_handler, start_handler


@pytest.mark.asyncio
async def test_start_handler_response() -> None:
    """Test that /start handler returns expected message."""
    message = AsyncMock()
    message.answer = AsyncMock()

    await start_handler(message)

    message.answer.assert_called_once()
    call_args = message.answer.call_args
    response_text = call_args[0][0]

    assert "The Hub" in response_text
    assert "Единая точка входа" in response_text
    assert "приложения" in response_text


@pytest.mark.asyncio
async def test_start_handler_sends_keyboard() -> None:
    """Test that /start handler includes application menu keyboard."""
    message = AsyncMock()
    message.answer = AsyncMock()

    await start_handler(message)

    message.answer.assert_called_once()
    call_kwargs = message.answer.call_args.kwargs
    assert "reply_markup" in call_kwargs
    keyboard = call_kwargs["reply_markup"]
    assert keyboard is not None


@pytest.mark.asyncio
async def test_app_handler_postbox_with_config() -> None:
    """Test that Postbox callback generates auth URL when POSTBOX_URL is configured."""
    os.environ["POSTBOX_URL"] = "https://postbox.finpipe.net"
    os.environ["HUB_AUTH_SECRET"] = "test-secret-key"

    try:
        query = AsyncMock()
        query.message = AsyncMock()
        query.message.edit_text = AsyncMock()
        query.answer = AsyncMock()
        query.from_user = AsyncMock()
        query.from_user.id = 123456789

        callback_data = AppCallback(app="postbox")
        await app_handler(query, callback_data)

        query.answer.assert_called_once()
        query.message.edit_text.assert_called_once()
        call_args = query.message.edit_text.call_args
        response_text = call_args[0][0]

        assert "Postbox" in response_text
        assert "📦" in response_text
        assert "действует" in response_text.lower()  # "действует 5 минут"

        # Check app description is shown
        assert "Трекер" in response_text or "почты" in response_text

        # Check planned features are shown
        assert "В планах:" in response_text
        assert "•" in response_text

        # Check that keyboard was provided
        call_kwargs = query.message.edit_text.call_args.kwargs
        assert "reply_markup" in call_kwargs
        keyboard = call_kwargs["reply_markup"]
        assert keyboard is not None
    finally:
        os.environ.pop("POSTBOX_URL", None)
        os.environ.pop("HUB_AUTH_SECRET", None)


@pytest.mark.asyncio
async def test_app_handler_postbox_without_config() -> None:
    """Test that Postbox callback shows error when POSTBOX_URL is not configured."""
    os.environ.pop("POSTBOX_URL", None)
    os.environ["HUB_AUTH_SECRET"] = "test-secret-key"

    try:
        query = AsyncMock()
        query.message = AsyncMock()
        query.message.edit_text = AsyncMock()
        query.answer = AsyncMock()
        query.from_user = AsyncMock()
        query.from_user.id = 123456789

        callback_data = AppCallback(app="postbox")
        await app_handler(query, callback_data)

        query.answer.assert_called_once()
        query.message.edit_text.assert_called_once()
        call_args = query.message.edit_text.call_args
        response_text = call_args[0][0]

        # Should show neutral error message (no config details)
        assert "недоступ" in response_text.lower() or "unavailable" in response_text.lower()
    finally:
        os.environ.pop("HUB_AUTH_SECRET", None)


@pytest.mark.asyncio
async def test_app_handler_postbox_uses_callback_user_id() -> None:
    """Test that Postbox auth uses callback.from_user.id (not client state)."""
    os.environ["POSTBOX_URL"] = "https://postbox.finpipe.net"
    os.environ["HUB_AUTH_SECRET"] = "test-secret-key"

    try:
        query = AsyncMock()
        query.message = AsyncMock()
        query.message.edit_text = AsyncMock()
        query.answer = AsyncMock()
        query.from_user = AsyncMock()
        query.from_user.id = 987654321  # Different from any client state

        callback_data = AppCallback(app="postbox")
        await app_handler(query, callback_data)

        # Verify create_auth_token was called (indirectly through URL generation)
        call_args = query.message.edit_text.call_args
        call_kwargs = call_args.kwargs
        keyboard = call_kwargs["reply_markup"]

        # Extract URL from keyboard
        url_button = keyboard.inline_keyboard[0][0]
        auth_url = url_button.url

        # URL should contain a valid token
        assert "token=" in auth_url
        assert auth_url.startswith("https://postbox.finpipe.net/auth/hub?")
    finally:
        os.environ.pop("POSTBOX_URL", None)
        os.environ.pop("HUB_AUTH_SECRET", None)


@pytest.mark.asyncio
async def test_app_handler_unknown_app() -> None:
    """Test that unknown app callback returns to hub menu."""
    query = AsyncMock()
    query.message = AsyncMock()
    query.message.edit_text = AsyncMock()
    query.answer = AsyncMock()

    callback_data = AppCallback(app="unknown")
    await app_handler(query, callback_data)

    query.answer.assert_called_once()
    query.message.edit_text.assert_called_once()
    call_args = query.message.edit_text.call_args
    response_text = call_args[0][0]

    # Should return to hub menu, not show error
    assert "The Hub" in response_text
    assert "Единая точка входа" in response_text


@pytest.mark.asyncio
async def test_app_handler_calls_answer() -> None:
    """Test that callback query is acknowledged."""
    query = AsyncMock()
    query.message = AsyncMock()
    query.message.edit_text = AsyncMock()
    query.answer = AsyncMock()

    callback_data = AppCallback(app="postbox")
    await app_handler(query, callback_data)

    query.answer.assert_called_once()


@pytest.mark.asyncio
async def test_home_handler_returns_to_menu() -> None:
    """Test that home callback returns to app menu."""
    query = AsyncMock()
    query.message = AsyncMock()
    query.message.edit_text = AsyncMock()
    query.answer = AsyncMock()

    callback_data = HomeCallback()
    await home_handler(query, callback_data)

    query.answer.assert_called_once()
    query.message.edit_text.assert_called_once()
    call_args = query.message.edit_text.call_args
    response_text = call_args[0][0]

    assert "The Hub" in response_text
    assert "приложения" in response_text
