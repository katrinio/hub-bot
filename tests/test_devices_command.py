"""Tests for the /devices Telegram command."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hub_bot.telegram.handlers.devices import devices_handler
from watcher.parse_devices import DeviceRecord


@pytest.mark.asyncio
async def test_devices_handler_sends_current_devices_to_current_chat() -> None:
    records = [DeviceRecord("j274ap", "Mac mini (M1, 2020)", "11.0", False)]
    message = MagicMock()
    message.chat.id = 123456789
    bot = MagicMock()

    with (
        patch("hub_bot.telegram.handlers.devices.fetch_devices", new=AsyncMock(return_value=records)) as fetch,
        patch("hub_bot.telegram.handlers.devices.send_devices_to_telegram", new=AsyncMock(return_value=1)) as send,
    ):
        await devices_handler(message, bot)

    fetch.assert_awaited_once_with()
    send.assert_awaited_once_with(records, bot, 123456789)


@pytest.mark.asyncio
async def test_devices_handler_reports_download_or_parse_error() -> None:
    message = MagicMock()
    message.answer = AsyncMock()
    bot = MagicMock()

    with patch(
        "hub_bot.telegram.handlers.devices.fetch_devices",
        new=AsyncMock(side_effect=ValueError("invalid DEVICES")),
    ):
        await devices_handler(message, bot)

    message.answer.assert_awaited_once_with(
        "Не удалось загрузить список устройств. Попробуй позже."
    )
