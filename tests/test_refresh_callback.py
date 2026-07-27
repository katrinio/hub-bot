"""Tests for Postbox auth link refresh callback."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import CallbackQuery, Chat, Message, User

from hub_bot.callback_data import PostboxRefreshCallback
from hub_bot.handlers import postbox_refresh_handler


@pytest.fixture
def postbox_refresh_callback() -> PostboxRefreshCallback:
    """Create a PostboxRefreshCallback instance."""
    return PostboxRefreshCallback()


@pytest.fixture
def mock_user() -> User:
    """Create a mock Telegram user."""
    return User(id=123456789, is_bot=False, first_name="Test")


@pytest.fixture
def mock_chat() -> Chat:
    """Create a mock chat."""
    return Chat(id=123456789, type="private")


@pytest.fixture
def mock_message() -> MagicMock:
    """Create a mock message with edit_text method."""
    message = MagicMock(spec=Message)
    message.edit_text = AsyncMock()
    return message


@pytest.fixture
def mock_callback_query(mock_user: User, mock_message: MagicMock) -> MagicMock:
    """Create a mock CallbackQuery."""
    query = MagicMock(spec=CallbackQuery)
    query.from_user = mock_user
    query.message = mock_message
    query.answer = AsyncMock()
    return query


class TestPostboxRefreshCallback:
    """Tests for postbox_refresh_handler."""

    @pytest.mark.asyncio
    async def test_refresh_generates_new_token(
        self,
        mock_callback_query: MagicMock,
        postbox_refresh_callback: PostboxRefreshCallback,
    ) -> None:
        """Refresh callback should generate a new auth token and URL."""
        with patch("hub_bot.handlers.get_postbox_url", return_value="http://postbox:8000"), \
             patch("hub_bot.handlers.create_auth_token", return_value="new-jwt-token") as mock_create, \
             patch("hub_bot.handlers.build_postbox_auth_url", return_value="http://postbox:8000/auth/hub?token=new-jwt-token"):

            await postbox_refresh_handler(mock_callback_query, postbox_refresh_callback)

            # Verify token creation used correct user ID and audience
            mock_create.assert_called_once_with(telegram_user_id=123456789, audience="postbox")

            # Verify message was edited
            assert mock_callback_query.message.edit_text.called

    @pytest.mark.asyncio
    async def test_refresh_updates_message_with_new_url(
        self,
        mock_callback_query: MagicMock,
        postbox_refresh_callback: PostboxRefreshCallback,
    ) -> None:
        """Refresh callback should edit the message with new auth URL."""
        with patch("hub_bot.handlers.get_postbox_url", return_value="http://postbox:8000"), \
             patch("hub_bot.handlers.create_auth_token", return_value="fresh-token"), \
             patch("hub_bot.handlers.build_postbox_auth_url", return_value="http://postbox:8000/auth/hub?token=fresh-token"):

            await postbox_refresh_handler(mock_callback_query, postbox_refresh_callback)

            # Verify edit_text was called with new keyboard
            mock_callback_query.message.edit_text.assert_called_once()
            call_args = mock_callback_query.message.edit_text.call_args
            assert call_args is not None
            # Check that response text contains app description and roadmap
            response = call_args[0][0].lower()
            assert "трекер" in response or "почты" in response
            assert "в планах" in response

    @pytest.mark.asyncio
    async def test_refresh_answers_callback(
        self,
        mock_callback_query: MagicMock,
        postbox_refresh_callback: PostboxRefreshCallback,
    ) -> None:
        """Refresh callback should answer the query."""
        with patch("hub_bot.handlers.get_postbox_url", return_value="http://postbox:8000"), \
             patch("hub_bot.handlers.create_auth_token", return_value="token"), \
             patch("hub_bot.handlers.build_postbox_auth_url", return_value="http://postbox:8000/auth/hub?token=token"):

            await postbox_refresh_handler(mock_callback_query, postbox_refresh_callback)

            mock_callback_query.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_handles_missing_postbox_url(
        self,
        mock_callback_query: MagicMock,
        postbox_refresh_callback: PostboxRefreshCallback,
    ) -> None:
        """Refresh should show error if POSTBOX_URL not configured."""
        with patch("hub_bot.handlers.get_postbox_url", return_value=None):
            await postbox_refresh_handler(mock_callback_query, postbox_refresh_callback)

            # Verify error message was shown
            mock_callback_query.message.edit_text.assert_called_once()
            call_args = mock_callback_query.message.edit_text.call_args
            assert call_args is not None
            assert "недоступ" in call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_refresh_handles_token_creation_error(
        self,
        mock_callback_query: MagicMock,
        postbox_refresh_callback: PostboxRefreshCallback,
    ) -> None:
        """Refresh should handle token creation errors gracefully."""
        with patch("hub_bot.handlers.get_postbox_url", return_value="http://postbox:8000"), \
             patch("hub_bot.handlers.create_auth_token", side_effect=ValueError("Auth error")):

            await postbox_refresh_handler(mock_callback_query, postbox_refresh_callback)

            # Verify error message was shown
            mock_callback_query.message.edit_text.assert_called_once()
            call_args = mock_callback_query.message.edit_text.call_args
            assert call_args is not None
            assert "не смог обновить" in call_args[0][0].lower() or "недоступен" in call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_refresh_handles_inaccessible_message(
        self,
        mock_callback_query: MagicMock,
        postbox_refresh_callback: PostboxRefreshCallback,
        mock_chat: Chat,
    ) -> None:
        """Refresh should handle inaccessible message gracefully."""
        from aiogram.types import InaccessibleMessage

        mock_callback_query.message = InaccessibleMessage(message_id=1, date=0, chat=mock_chat)

        await postbox_refresh_handler(mock_callback_query, postbox_refresh_callback)

        # Should answer but not edit
        mock_callback_query.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_handles_no_message(
        self,
        mock_callback_query: MagicMock,
        postbox_refresh_callback: PostboxRefreshCallback,
    ) -> None:
        """Refresh should handle missing message gracefully."""
        mock_callback_query.message = None

        await postbox_refresh_handler(mock_callback_query, postbox_refresh_callback)

        # Should answer but not edit
        mock_callback_query.answer.assert_called_once()


class TestPostboxRefreshCallbackData:
    """Tests for PostboxRefreshCallback structure."""

    def test_callback_has_correct_prefix(self) -> None:
        """PostboxRefreshCallback should have 'hub' prefix."""
        callback = PostboxRefreshCallback()
        packed = callback.pack()
        assert packed.startswith("hub:")

    def test_callback_has_correct_action(self) -> None:
        """PostboxRefreshCallback should have 'postbox_refresh' action."""
        callback = PostboxRefreshCallback()
        packed = callback.pack()
        assert "postbox_refresh" in packed

    def test_callback_pack_unpack_roundtrip(self) -> None:
        """PostboxRefreshCallback should support pack/unpack roundtrip."""
        original = PostboxRefreshCallback()
        packed = original.pack()
        unpacked = PostboxRefreshCallback.unpack(packed)
        assert unpacked.action == "postbox_refresh"


class TestRefreshKeyboardIntegration:
    """Integration tests for refresh keyboard in handler."""

    @pytest.mark.asyncio
    async def test_refresh_keyboard_contains_refresh_button(
        self,
        mock_callback_query: MagicMock,
        postbox_refresh_callback: PostboxRefreshCallback,
    ) -> None:
        """Refresh response should include refresh button in keyboard."""
        with patch("hub_bot.handlers.get_postbox_url", return_value="http://postbox:8000"), \
             patch("hub_bot.handlers.create_auth_token", return_value="token"), \
             patch("hub_bot.handlers.build_postbox_auth_url", return_value="http://postbox:8000/auth/hub?token=token"):

            await postbox_refresh_handler(mock_callback_query, postbox_refresh_callback)

            # Verify that keyboard was passed to edit_text
            call_args = mock_callback_query.message.edit_text.call_args
            assert call_args is not None
            # kwargs should contain reply_markup
            assert "reply_markup" in call_args[1]

    @pytest.mark.asyncio
    async def test_refresh_uses_callback_user_id(
        self,
        postbox_refresh_callback: PostboxRefreshCallback,
        mock_message: MagicMock,
    ) -> None:
        """Refresh should use user ID from callback, not client state."""
        # Create callback with different user ID
        different_user = User(id=987654321, is_bot=False, first_name="Different")
        query = MagicMock(spec=CallbackQuery)
        query.from_user = different_user
        query.message = mock_message
        query.answer = AsyncMock()

        with patch("hub_bot.handlers.get_postbox_url", return_value="http://postbox:8000"), \
             patch("hub_bot.handlers.create_auth_token", return_value="token") as mock_create, \
             patch("hub_bot.handlers.build_postbox_auth_url", return_value="http://postbox:8000/auth/hub?token=token"):

            await postbox_refresh_handler(query, postbox_refresh_callback)

            # Verify correct user ID was used
            mock_create.assert_called_once_with(telegram_user_id=987654321, audience="postbox")

    @pytest.mark.asyncio
    async def test_refresh_always_uses_postbox_audience(
        self,
        mock_callback_query: MagicMock,
        postbox_refresh_callback: PostboxRefreshCallback,
    ) -> None:
        """Refresh should always use 'postbox' audience."""
        with patch("hub_bot.handlers.get_postbox_url", return_value="http://postbox:8000"), \
             patch("hub_bot.handlers.create_auth_token", return_value="token") as mock_create, \
             patch("hub_bot.handlers.build_postbox_auth_url", return_value="http://postbox:8000/auth/hub?token=token"):

            await postbox_refresh_handler(mock_callback_query, postbox_refresh_callback)

            # Verify audience is always 'postbox'
            call_args = mock_create.call_args
            assert call_args is not None
            assert call_args[1]["audience"] == "postbox"

    @pytest.mark.asyncio
    async def test_refresh_multiple_calls_generate_different_tokens(
        self,
        mock_callback_query: MagicMock,
        postbox_refresh_callback: PostboxRefreshCallback,
    ) -> None:
        """Multiple refresh calls should generate different tokens (due to iat/exp)."""
        tokens_generated: list[str] = []

        def capture_token(telegram_user_id: int, audience: str) -> str:
            token = f"token_{len(tokens_generated)}"
            tokens_generated.append(token)
            return token

        with patch("hub_bot.handlers.get_postbox_url", return_value="http://postbox:8000"), \
             patch("hub_bot.handlers.create_auth_token", side_effect=capture_token), \
             patch("hub_bot.handlers.build_postbox_auth_url", side_effect=lambda url, token: f"{url}?token={token}"):

            # First refresh
            await postbox_refresh_handler(mock_callback_query, postbox_refresh_callback)

            # Reset mock for second call
            mock_callback_query.message.edit_text.reset_mock()

            # Second refresh
            await postbox_refresh_handler(mock_callback_query, postbox_refresh_callback)

            # Should have created 2 different tokens
            assert len(tokens_generated) == 2
            assert tokens_generated[0] != tokens_generated[1]
