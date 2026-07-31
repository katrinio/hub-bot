"""Tests for user tracking middleware."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from aiogram.types import CallbackQuery, Chat, Message, Update
from aiogram.types import User as TelegramUser

from hub_bot.db.middleware import UserTrackingMiddleware


@pytest.mark.asyncio
async def test_middleware_tracks_message_sender() -> None:
    """Test that middleware tracks user from message."""
    middleware = UserTrackingMiddleware()

    # Create message update with proper Chat object and from_user in constructor
    from_user = TelegramUser(
        id=123456789,
        is_bot=False,
        first_name="Test",
        last_name="User",
        username="testuser",
        language_code="en",
    )
    chat = Chat(id=1, type="private")
    message = Message(message_id=1, date=datetime.now(UTC), chat=chat, from_user=from_user)

    update = Update(update_id=1, message=message)

    # Mock handler and data
    handler = AsyncMock(return_value=None)
    data: dict[str, object] = {}

    # Mock get_session to avoid DB init
    mock_session = AsyncMock()

    with (
        patch("hub_bot.db.middleware.get_session") as mock_get_session,
        patch("hub_bot.db.middleware.UserRepository.upsert", new_callable=AsyncMock) as mock_upsert,
    ):
        mock_get_session.return_value.__aenter__.return_value = mock_session

        await middleware(handler, update, data)

        # Verify upsert was called with correct data
        mock_upsert.assert_called_once()
        call_kwargs = mock_upsert.call_args.kwargs
        assert call_kwargs["telegram_id"] == 123456789
        assert call_kwargs["username"] == "testuser"
        assert call_kwargs["first_name"] == "Test"

    # Handler should be called
    handler.assert_called_once()


@pytest.mark.asyncio
async def test_middleware_tracks_callback_query_sender() -> None:
    """Test that middleware tracks user from callback_query."""
    middleware = UserTrackingMiddleware()

    # Create callback_query update
    from_user = TelegramUser(id=987654321, is_bot=False, first_name="Callback", username="cbuser")
    callback_query = CallbackQuery(id="callback_id", from_user=from_user, chat_instance="instance")

    update = Update(update_id=2, callback_query=callback_query)

    # Mock handler and data
    handler = AsyncMock(return_value=None)
    data: dict[str, object] = {}

    # Mock get_session
    mock_session = AsyncMock()

    with (
        patch("hub_bot.db.middleware.get_session") as mock_get_session,
        patch("hub_bot.db.middleware.UserRepository.upsert", new_callable=AsyncMock) as mock_upsert,
    ):
        mock_get_session.return_value.__aenter__.return_value = mock_session

        await middleware(handler, update, data)

        # Verify upsert was called
        mock_upsert.assert_called_once()
        call_kwargs = mock_upsert.call_args.kwargs
        assert call_kwargs["telegram_id"] == 987654321
        assert call_kwargs["username"] == "cbuser"


@pytest.mark.asyncio
async def test_middleware_handles_update_without_from_user() -> None:
    """Test that middleware doesn't crash on updates without from_user."""
    middleware = UserTrackingMiddleware()

    # Create update without from_user (e.g., channel_post)
    update = Update(update_id=3)  # No message, callback_query, etc.

    # Mock handler and data
    handler = AsyncMock(return_value="success")
    data: dict[str, object] = {}

    with patch("hub_bot.db.middleware.UserRepository.upsert", new_callable=AsyncMock) as mock_upsert:
        result = await middleware(handler, update, data)

        # upsert should NOT be called (no from_user)
        mock_upsert.assert_not_called()

    # Handler should still be called and return normally
    handler.assert_called_once()
    assert result == "success"


@pytest.mark.asyncio
async def test_middleware_continues_on_db_error() -> None:
    """Test that middleware doesn't break the chain on DB error."""
    middleware = UserTrackingMiddleware()

    # Create message update
    from_user = TelegramUser(id=111, is_bot=False, first_name="Test")
    chat = Chat(id=1, type="private")
    message = Message(message_id=1, date=datetime.now(UTC), chat=chat, from_user=from_user)

    update = Update(update_id=1, message=message)

    # Mock handler to return success
    handler = AsyncMock(return_value="handler_success")
    data: dict[str, object] = {}

    # Mock upsert to raise an error
    mock_session = AsyncMock()

    with (
        patch("hub_bot.db.middleware.get_session") as mock_get_session,
        patch(
            "hub_bot.db.middleware.UserRepository.upsert",
            new_callable=AsyncMock,
            side_effect=Exception("DB error"),
        ) as mock_upsert,
    ):
        mock_get_session.return_value.__aenter__.return_value = mock_session
        result = await middleware(handler, update, data)

        # upsert was attempted
        mock_upsert.assert_called_once()

    # Handler should still be called and return (middleware error is logged but doesn't break chain)
    handler.assert_called_once()
    assert result == "handler_success"


@pytest.mark.asyncio
async def test_middleware_handles_user_without_username() -> None:
    """Test that middleware handles user without username."""
    middleware = UserTrackingMiddleware()

    # Create user without username
    from_user = TelegramUser(id=222, is_bot=False, first_name="NoUsername")
    chat = Chat(id=1, type="private")
    message = Message(message_id=1, date=datetime.now(UTC), chat=chat, from_user=from_user)

    update = Update(update_id=1, message=message)

    handler = AsyncMock(return_value=None)
    data: dict[str, object] = {}

    mock_session = AsyncMock()

    with (
        patch("hub_bot.db.middleware.get_session") as mock_get_session,
        patch("hub_bot.db.middleware.UserRepository.upsert", new_callable=AsyncMock) as mock_upsert,
    ):
        mock_get_session.return_value.__aenter__.return_value = mock_session

        await middleware(handler, update, data)

        call_kwargs = mock_upsert.call_args.kwargs
        assert call_kwargs["username"] is None  # No username provided
        assert call_kwargs["first_name"] == "NoUsername"


@pytest.mark.asyncio
async def test_middleware_calls_handler_when_no_from_user() -> None:
    """Test that handler is called even when update has no from_user (e.g., channel_post)."""
    middleware = UserTrackingMiddleware()

    # Update without from_user (e.g., channel_post)
    update = Update(update_id=3)

    # Mock handler that returns a distinct value
    handler = AsyncMock(return_value="handler_result")
    data: dict[str, object] = {}

    # Don't mock upsert - we want to verify it's not called
    with patch("hub_bot.db.middleware.UserRepository.upsert", new_callable=AsyncMock) as mock_upsert:
        result = await middleware(handler, update, data)

        # upsert should NOT be called (no from_user)
        mock_upsert.assert_not_called()

    # Handler MUST be called and return its result
    handler.assert_called_once_with(update, data)
    assert result == "handler_result"


@pytest.mark.asyncio
async def test_middleware_calls_handler_when_user_is_bot() -> None:
    """Test that handler is called even when user is a bot."""
    middleware = UserTrackingMiddleware()

    # Create bot user
    from_user = TelegramUser(id=333, is_bot=True, first_name="BotUser")
    chat = Chat(id=1, type="private")
    message = Message(message_id=1, date=datetime.now(UTC), chat=chat, from_user=from_user)

    update = Update(update_id=1, message=message)

    # Mock handler
    handler = AsyncMock(return_value="bot_handler_result")
    data: dict[str, object] = {}

    with patch("hub_bot.db.middleware.UserRepository.upsert", new_callable=AsyncMock) as mock_upsert:
        result = await middleware(handler, update, data)

        # upsert should NOT be called (user is bot)
        mock_upsert.assert_not_called()

    # Handler MUST be called and return its result
    handler.assert_called_once_with(update, data)
    assert result == "bot_handler_result"


@pytest.mark.asyncio
async def test_middleware_calls_handler_on_db_error() -> None:
    """Test that handler is called even when DB error occurs."""
    middleware = UserTrackingMiddleware()

    # Create valid user
    from_user = TelegramUser(id=444, is_bot=False, first_name="TestUser")
    chat = Chat(id=1, type="private")
    message = Message(message_id=1, date=datetime.now(UTC), chat=chat, from_user=from_user)

    update = Update(update_id=1, message=message)

    # Mock handler that returns a result
    handler = AsyncMock(return_value="error_handled")
    data: dict[str, object] = {}

    mock_session = AsyncMock()

    # upsert throws an error
    with (
        patch("hub_bot.db.middleware.get_session") as mock_get_session,
        patch(
            "hub_bot.db.middleware.UserRepository.upsert",
            new_callable=AsyncMock,
            side_effect=Exception("DB is down"),
        ),
    ):
        mock_get_session.return_value.__aenter__.return_value = mock_session

        result = await middleware(handler, update, data)

    # Handler MUST still be called despite DB error
    handler.assert_called_once_with(update, data)
    assert result == "error_handled"
