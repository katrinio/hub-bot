from unittest.mock import AsyncMock

import pytest

from hub_bot.handlers import start_handler


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
