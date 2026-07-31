from unittest.mock import AsyncMock, patch

import pytest

from hub_bot.bot import create_bot, create_dispatcher


@pytest.mark.asyncio
async def test_create_bot() -> None:
    """Test that bot is created without calling real Telegram API."""
    token = "123:ABC-xyz"

    # Mock Bot to avoid real API calls
    with patch("hub_bot.bot.Bot") as mock_bot_class:
        mock_bot_instance = AsyncMock()
        mock_bot_instance.set_my_commands = AsyncMock()
        mock_bot_class.return_value = mock_bot_instance

        await create_bot(token)

        # Verify Bot was instantiated with token
        mock_bot_class.assert_called_once_with(token=token)

        # Verify set_my_commands was called to register /start and /stats
        mock_bot_instance.set_my_commands.assert_called_once()
        commands = mock_bot_instance.set_my_commands.call_args[1]["commands"]
        assert len(commands) == 2
        command_names = {cmd.command for cmd in commands}
        assert "start" in command_names
        assert "stats" in command_names


def test_create_dispatcher() -> None:
    """Test that dispatcher is created and routers are registered."""
    dp = create_dispatcher()

    # Verify dispatcher is created
    assert dp is not None

    # Verify handlers router is registered
    assert len(dp.sub_routers) > 0
