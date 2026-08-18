"""Tests for the Asahi device parser and Telegram delivery."""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter, TelegramServerError
from aiogram.methods import SendMessage

from hub_bot.watcher import parse_devices as parser

SOURCE = '''
DEVICES = {
    "j274ap": Device("11.0", False),  # Mac mini (M1, 2020)
    "j433ap": Device(min_ver="14.8.3", expert_only=True),  # iMac (24-inch, M3, 2023)
}
'''


def test_parse_devices_extracts_literals_and_inline_models() -> None:
    records = parser.parse_devices(SOURCE)

    assert records == [
        parser.DeviceRecord("j274ap", "Mac mini (M1, 2020)", "11.0", False),
        parser.DeviceRecord("j433ap", "iMac (24-inch, M3, 2023)", "14.8.3", True),
    ]


def test_parse_devices_does_not_execute_downloaded_source() -> None:
    source = f'raise RuntimeError("source was executed")\n{SOURCE}'

    records = parser.parse_devices(source)

    assert len(records) == 2


def test_parse_devices_rejects_non_literal_values() -> None:
    source = '''
DEVICES = {
    "j274ap": Device(get_version(), False),  # Mac mini (M1, 2020)
}
'''

    with pytest.raises(ValueError, match="min_ver must be a literal"):
        parser.parse_devices(source)


def test_parse_devices_requires_inline_model_comment() -> None:
    source = '''
DEVICES = {
    "j274ap": Device("11.0", False),
}
'''

    with pytest.raises(ValueError, match="has no inline Mac model comment"):
        parser.parse_devices(source)


def test_parse_devices_rejects_empty_mapping() -> None:
    with pytest.raises(ValueError, match="DEVICES must not be empty"):
        parser.parse_devices("DEVICES = {}")


def test_parse_devices_rejects_duplicate_device_ids() -> None:
    source = '''
DEVICES = {
    "j274ap": Device("11.0", False),  # Mac mini (M1, 2020)
    "j274ap": Device("12.0", True),  # Duplicate Mac
}
'''

    with pytest.raises(ValueError, match="duplicate DEVICES device_id: 'j274ap'"):
        parser.parse_devices(source)


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        ('DEVICES["later"] = Device("15.0", True)', "DEVICES is mutated"),
        ('DEVICES.update({"later": Device("15.0", True)})', "DEVICES.update"),
        ('del DEVICES["j274ap"]', "DEVICES is mutated"),
        ("DEVICES.clear()", "DEVICES.clear"),
    ],
)
def test_parse_devices_rejects_later_mutations(mutation: str, error: str) -> None:
    with pytest.raises(ValueError, match=error):
        parser.parse_devices(f"{SOURCE}\n{mutation}\n")


def test_parse_devices_allows_known_asahi_development_vm_branch() -> None:
    source = f'''
import os
{SOURCE}
if os.environ.get("ALLOW_VM", None):
    DEVICES["vma2macosap"] = Device("12.0", False)
'''

    records = parser.parse_devices(source)

    assert [record.device_id for record in records] == ["j274ap", "j433ap"]


def test_format_devices_uses_russian_ui_and_preserves_source_data() -> None:
    message = parser.format_devices(parser.parse_devices(SOURCE))

    assert message.startswith("Устройства Asahi Linux\nНайдено: 2")
    assert "device_id: j274ap" in message
    assert "model: Mac mini (M1, 2020)" in message
    assert "min_ver: 11.0 | expert_only: False" in message
    assert "min_ver: 14.8.3 | expert_only: True" in message


def test_build_device_messages_splits_only_between_records_and_numbers_parts() -> None:
    records = [
        parser.DeviceRecord(f"device-{index}", f"Mac model {index}", "14.0", False)
        for index in range(4)
    ]

    messages = parser.build_device_messages(records, limit=145)

    assert len(messages) > 1
    assert all(len(message) <= 145 for message in messages)
    for index, message in enumerate(messages, 1):
        assert f"Часть {index}/{len(messages)}" in message
    for record in records:
        containing_messages = [message for message in messages if record.device_id in message]
        assert len(containing_messages) == 1
        assert f"model: {record.mac_model}" in containing_messages[0]
        assert f"min_ver: {record.min_ver} | expert_only: False" in containing_messages[0]


@pytest.mark.parametrize("limit", [0, -1])
def test_build_device_messages_rejects_non_positive_limit(limit: int) -> None:
    with pytest.raises(ValueError, match="message limit must be positive"):
        parser.build_device_messages(parser.parse_devices(SOURCE), limit)


def test_build_device_messages_rejects_record_larger_than_one_message() -> None:
    record = parser.DeviceRecord("oversized", "x" * 200, "14.0", False)

    with pytest.raises(ValueError, match="device record 'oversized' exceeds"):
        parser.build_device_messages([record], limit=150)


@pytest.mark.asyncio
async def test_send_devices_splits_and_sends_every_message() -> None:
    bot = MagicMock()
    bot.send_message = AsyncMock()
    records = parser.parse_devices(SOURCE)

    with patch.object(parser, "build_device_messages", return_value=["part one", "part two"]):
        message_count = await parser.send_devices_to_telegram(records, bot, "chat-id", message_thread_id=42)

    assert message_count == 2
    assert bot.send_message.await_count == 2
    first_call, second_call = bot.send_message.await_args_list
    assert first_call.kwargs == {"chat_id": "chat-id", "text": "part one", "message_thread_id": 42}
    assert second_call.kwargs == {"chat_id": "chat-id", "text": "part two", "message_thread_id": 42}


@pytest.mark.parametrize("error_type", [TelegramNetworkError, TelegramServerError])
@pytest.mark.asyncio
async def test_send_devices_retries_transient_error(
    error_type: type[TelegramNetworkError] | type[TelegramServerError],
) -> None:
    bot = MagicMock()
    error = error_type(method=SendMessage(chat_id=1, text="message"), message="Telegram unavailable")
    bot.send_message = AsyncMock(side_effect=[error, MagicMock()])

    with patch.object(parser.asyncio, "sleep", new=AsyncMock()) as sleep:
        count = await parser.send_devices_to_telegram(parser.parse_devices(SOURCE), bot, 1)

    assert count == 1
    assert bot.send_message.await_count == 2
    sleep.assert_awaited_once_with(1.0)


@pytest.mark.asyncio
async def test_send_devices_honors_bounded_retry_after() -> None:
    bot = MagicMock()
    error = TelegramRetryAfter(
        method=SendMessage(chat_id=1, text="message"),
        message="too many requests",
        retry_after=120,
    )
    bot.send_message = AsyncMock(side_effect=[error, MagicMock()])

    with patch.object(parser.asyncio, "sleep", new=AsyncMock()) as sleep:
        await parser.send_devices_to_telegram(parser.parse_devices(SOURCE), bot, 1)

    sleep.assert_awaited_once_with(parser.TELEGRAM_MAX_RETRY_DELAY)


@pytest.mark.asyncio
async def test_send_devices_stops_after_bounded_retries() -> None:
    bot = MagicMock()
    error = TelegramNetworkError(method=SendMessage(chat_id=1, text="message"), message="network unavailable")
    bot.send_message = AsyncMock(side_effect=error)

    with (
        patch.object(parser.asyncio, "sleep", new=AsyncMock()) as sleep,
        pytest.raises(TelegramNetworkError),
    ):
        await parser.send_devices_to_telegram(parser.parse_devices(SOURCE), bot, 1, max_retries=2)

    assert bot.send_message.await_count == 3
    assert sleep.await_count == 2


@pytest.mark.asyncio
async def test_run_downloads_parses_sends_and_closes_bot(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-id")
    bot = MagicMock()
    bot.session.close = AsyncMock()

    with (
        patch.object(parser, "download_source", return_value=SOURCE) as download,
        patch.object(parser, "get_bot_token", return_value="123:token"),
        patch.object(parser, "Bot", return_value=bot) as bot_class,
        patch.object(parser, "send_devices_to_telegram", new=AsyncMock(return_value=2)) as send,
    ):
        result = await parser.run("https://example.test/main.py", 5.0)

    assert result == (2, 2)
    download.assert_called_once_with("https://example.test/main.py", 5.0)
    bot_class.assert_called_once_with(token="123:token")
    send.assert_awaited_once_with(parser.parse_devices(SOURCE), bot, "chat-id")
    bot.session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_closes_bot_when_sending_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-id")
    bot = MagicMock()
    bot.session.close = AsyncMock()

    with (
        patch.object(parser, "download_source", return_value=SOURCE),
        patch.object(parser, "get_bot_token", return_value="123:token"),
        patch.object(parser, "Bot", return_value=bot),
        patch.object(
            parser,
            "send_devices_to_telegram",
            new=AsyncMock(side_effect=RuntimeError("Telegram unavailable")),
        ),
        pytest.raises(RuntimeError, match="Telegram unavailable"),
    ):
        await parser.run("https://example.test/main.py", 5.0)

    bot.session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_requires_chat_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    with (
        patch.object(parser, "download_source", return_value=SOURCE),
        patch.object(parser, "get_bot_token", return_value="123:token"),
        pytest.raises(ValueError, match="TELEGRAM_CHAT_ID"),
    ):
        await parser.run("https://example.test/main.py", 5.0)


def test_main_dry_run_prints_devices_without_telegram(capsys: pytest.CaptureFixture[str]) -> None:
    records = parser.parse_devices(SOURCE)

    with (
        patch.object(sys, "argv", ["parse_devices.py", "--dry-run"]),
        patch.object(parser, "fetch_devices", new=AsyncMock(return_value=records)) as fetch,
        patch.object(parser, "run", new=AsyncMock()) as run,
    ):
        parser.main()

    assert capsys.readouterr().out.strip() == parser.format_devices(records)
    fetch.assert_awaited_once_with(parser.DEFAULT_SOURCE_URL, 30.0)
    run.assert_not_awaited()
