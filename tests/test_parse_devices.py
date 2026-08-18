"""Tests for the Asahi device parser and Telegram delivery."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from watcher import parse_devices as parser

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


def test_format_devices_uses_russian_ui_and_preserves_source_data() -> None:
    message = parser.format_devices(parser.parse_devices(SOURCE))

    assert message.startswith("Устройства Asahi Linux\nНайдено: 2")
    assert "device_id: j274ap" in message
    assert "model: Mac mini (M1, 2020)" in message
    assert "min_ver: 11.0 | expert_only: False" in message
    assert "min_ver: 14.8.3 | expert_only: True" in message


@pytest.mark.parametrize("limit", [0, -1])
def test_split_message_rejects_non_positive_limit(limit: int) -> None:
    with pytest.raises(ValueError, match="message limit must be positive"):
        parser.split_message("text", limit)


def test_split_message_respects_limit_for_lines_and_long_content() -> None:
    text = "first line\n" + "x" * 25 + "\nlast line"

    chunks = parser.split_message(text, limit=10)

    assert len(chunks) > 1
    assert all(0 < len(chunk) <= 10 for chunk in chunks)
    assert chunks[0] == "first line"
    assert chunks[-1] == "last line"


@pytest.mark.asyncio
async def test_send_devices_splits_and_sends_every_message() -> None:
    bot = MagicMock()
    bot.send_message = AsyncMock()

    with patch.object(parser, "format_devices", return_value="x" * (parser.TELEGRAM_MESSAGE_LIMIT + 1)):
        message_count = await parser.send_devices_to_telegram([], bot, "chat-id")

    assert message_count == 2
    assert bot.send_message.await_count == 2
    first_call, second_call = bot.send_message.await_args_list
    assert first_call.kwargs == {"chat_id": "chat-id", "text": "x" * parser.TELEGRAM_MESSAGE_LIMIT}
    assert second_call.kwargs == {"chat_id": "chat-id", "text": "x"}


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
