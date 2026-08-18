"""Tests for the /devices Telegram command."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram import Bot
from aiogram.types import Chat, Message, MessageEntity
from aiogram.types import User as TelegramUser

from hub_bot.telegram.handlers import devices as devices_module
from hub_bot.telegram.handlers import router
from hub_bot.telegram.states import FeedbackForm
from watcher.parse_devices import DeviceRecord

RECORDS = [DeviceRecord("j274ap", "Mac mini (M1, 2020)", "11.0", False)]


def _message(text: str = "/devices", thread_id: int | None = None) -> Message:
    return Message(
        message_id=1,
        date=datetime.now(UTC),
        chat=Chat(id=123456789, type="private"),
        from_user=TelegramUser(id=987654321, is_bot=False, first_name="Test"),
        text=text,
        entities=[MessageEntity(type="bot_command", offset=0, length=len(text))],
        message_thread_id=thread_id,
    )


@pytest.mark.asyncio
async def test_devices_handler_sends_current_devices_to_current_thread() -> None:
    message = _message(thread_id=42)
    bot = MagicMock()
    catalog = MagicMock()
    catalog.get_devices = AsyncMock(return_value=RECORDS)
    cooldown = MagicMock()
    cooldown.try_acquire.return_value = 0

    with (
        patch.object(devices_module, "device_catalog", catalog),
        patch.object(devices_module, "devices_cooldown", cooldown),
        patch.object(devices_module, "send_devices_to_telegram", new=AsyncMock(return_value=1)) as send,
    ):
        await devices_module.devices_handler(message, bot)

    cooldown.try_acquire.assert_called_once_with(("user", 987654321))
    catalog.get_devices.assert_awaited_once_with()
    send.assert_awaited_once_with(RECORDS, bot, 123456789, message_thread_id=42)


@pytest.mark.asyncio
async def test_devices_handler_enforces_cooldown() -> None:
    message = MagicMock()
    message.chat.id = 123456789
    message.from_user.id = 987654321
    message.answer = AsyncMock()
    bot = MagicMock()
    catalog = MagicMock()
    catalog.get_devices = AsyncMock()
    cooldown = MagicMock()
    cooldown.try_acquire.return_value = 12.1

    with (
        patch.object(devices_module, "device_catalog", catalog),
        patch.object(devices_module, "devices_cooldown", cooldown),
    ):
        await devices_module.devices_handler(message, bot)

    message.answer.assert_awaited_once_with("Список недавно запрашивали. Повтори через 13 сек.")
    catalog.get_devices.assert_not_awaited()


@pytest.mark.asyncio
async def test_devices_handler_reports_download_or_parse_error() -> None:
    message = MagicMock()
    message.chat.id = 123456789
    message.from_user.id = 987654321
    message.message_thread_id = None
    message.answer = AsyncMock()
    bot = MagicMock()
    catalog = MagicMock()
    catalog.get_devices = AsyncMock(side_effect=ValueError("invalid DEVICES"))
    cooldown = MagicMock()
    cooldown.try_acquire.return_value = 0

    with (
        patch.object(devices_module, "device_catalog", catalog),
        patch.object(devices_module, "devices_cooldown", cooldown),
    ):
        await devices_module.devices_handler(message, bot)

    message.answer.assert_awaited_once_with(
        "Не удалось загрузить список устройств. Попробуй позже."
    )


@pytest.mark.asyncio
async def test_devices_command_is_not_consumed_by_feedback_waiting_state() -> None:
    """Integration test router order and filters with an active feedback FSM state."""
    message = _message()
    bot = Bot(token="123456789:TEST_TOKEN")
    state = AsyncMock()
    catalog = MagicMock()
    catalog.get_devices = AsyncMock(return_value=RECORDS)
    cooldown = MagicMock()
    cooldown.try_acquire.return_value = 0

    try:
        with (
            patch.object(devices_module, "device_catalog", catalog),
            patch.object(devices_module, "devices_cooldown", cooldown),
            patch.object(devices_module, "send_devices_to_telegram", new=AsyncMock(return_value=1)) as send,
        ):
            await router.propagate_event(
                update_type="message",
                event=message,
                bot=bot,
                state=state,
                raw_state=FeedbackForm.waiting_for_feedback.state,
            )
    finally:
        await bot.session.close()

    send.assert_awaited_once_with(RECORDS, bot, 123456789, message_thread_id=None)
    state.get_data.assert_not_awaited()


@pytest.mark.asyncio
async def test_unknown_command_is_not_consumed_as_feedback() -> None:
    message = _message("/unknown")
    bot = Bot(token="123456789:TEST_TOKEN")
    state = AsyncMock()

    try:
        await router.propagate_event(
            update_type="message",
            event=message,
            bot=bot,
            state=state,
            raw_state=FeedbackForm.waiting_for_feedback.state,
        )
    finally:
        await bot.session.close()

    state.get_data.assert_not_awaited()
