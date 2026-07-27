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
async def test_app_handler_postbox() -> None:
    """Test that Postbox callback shows app placeholder."""
    query = AsyncMock()
    query.message = AsyncMock()
    query.message.edit_text = AsyncMock()
    query.answer = AsyncMock()

    callback_data = AppCallback(app="postbox")
    await app_handler(query, callback_data)

    query.answer.assert_called_once()
    query.message.edit_text.assert_called_once()
    call_args = query.message.edit_text.call_args
    response_text = call_args[0][0]

    assert "Postbox" in response_text
    assert "📦" in response_text
    assert "интеграция" in response_text.lower()


@pytest.mark.asyncio
async def test_app_handler_unknown_app() -> None:
    """Test that unknown app callback is handled safely."""
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

    assert "недоступно" in response_text.lower()


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
