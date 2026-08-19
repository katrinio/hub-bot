"""Tests for persistent watcher snapshots and change-only notifications."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from watcher import cli
from watcher.monitoring import changed_fields, load_device_snapshot, save_device_snapshot
from watcher.parser import DeviceRecord
from watcher.telegram import format_device_change

PREVIOUS = DeviceRecord(
    device_id="j516sap",
    mac_model="MacBook Pro (16-inch, M3 Pro, 2023)",
    min_ver="14.8.3",
    expert_only=True,
)
CURRENT = DeviceRecord(
    device_id="j516sap",
    mac_model="MacBook Pro (16-inch, M3 Pro, 2023)",
    min_ver="14.8.3",
    expert_only=False,
)


def test_snapshot_round_trip(tmp_path: Path) -> None:
    state_path = tmp_path / "watcher" / "device.json"

    assert load_device_snapshot(state_path) is None
    save_device_snapshot(state_path, PREVIOUS)

    assert load_device_snapshot(state_path) == PREVIOUS


def test_snapshot_rejects_invalid_json(tmp_path: Path) -> None:
    state_path = tmp_path / "device.json"
    state_path.write_text("not-json", encoding="utf-8")

    with pytest.raises(ValueError, match="cannot read watcher state"):
        load_device_snapshot(state_path)


def test_snapshot_rejects_invalid_field_types(tmp_path: Path) -> None:
    state_path = tmp_path / "device.json"
    state_path.write_text(
        json.dumps(
            {
                "device_id": "j516sap",
                "mac_model": "MacBook Pro",
                "min_ver": "14.8.3",
                "expert_only": "False",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="invalid expert_only"):
        load_device_snapshot(state_path)


def test_change_message_highlights_expert_only_transition() -> None:
    assert changed_fields(PREVIOUS, CURRENT) == {"expert_only": (True, False)}
    assert format_device_change(PREVIOUS, CURRENT) == (
        "Изменение устройства Asahi Linux\n"
        "device_id: j516sap\n"
        "model: MacBook Pro (16-inch, M3 Pro, 2023)\n\n"
        "expert_only: True → False"
    )


@pytest.mark.asyncio
async def test_first_check_saves_baseline_without_sending(tmp_path: Path) -> None:
    state_path = tmp_path / "device.json"

    with (
        patch.object(cli, "fetch_tracked_device", new=AsyncMock(return_value=[PREVIOUS])),
        patch.object(cli, "Bot") as bot_class,
    ):
        result = await cli.check_for_changes("https://example.test/main.py", 5.0, state_path)

    assert result == "Baseline сохранён: j516sap. Сообщение не отправлено."
    assert load_device_snapshot(state_path) == PREVIOUS
    bot_class.assert_not_called()


@pytest.mark.asyncio
async def test_unchanged_check_does_not_send(tmp_path: Path) -> None:
    state_path = tmp_path / "device.json"
    save_device_snapshot(state_path, PREVIOUS)

    with (
        patch.object(cli, "fetch_tracked_device", new=AsyncMock(return_value=[PREVIOUS])),
        patch.object(cli, "Bot") as bot_class,
    ):
        result = await cli.check_for_changes("https://example.test/main.py", 5.0, state_path)

    assert result == "Изменений нет: j516sap. Сообщение не отправлено."
    bot_class.assert_not_called()


@pytest.mark.asyncio
async def test_changed_check_sends_then_updates_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:token")
    monkeypatch.setenv("ADMIN_TELEGRAM_ID", "123456789")
    state_path = tmp_path / "device.json"
    save_device_snapshot(state_path, PREVIOUS)
    bot = MagicMock()
    bot.session.close = AsyncMock()

    with (
        patch.object(cli, "fetch_tracked_device", new=AsyncMock(return_value=[CURRENT])),
        patch.object(cli, "Bot", return_value=bot),
        patch.object(cli, "send_device_change_to_telegram", new=AsyncMock()) as send,
    ):
        result = await cli.check_for_changes("https://example.test/main.py", 5.0, state_path)

    assert result == "Изменение обнаружено: j516sap. Сообщение отправлено."
    send.assert_awaited_once_with(PREVIOUS, CURRENT, bot, 123456789)
    bot.session.close.assert_awaited_once()
    assert load_device_snapshot(state_path) == CURRENT


@pytest.mark.asyncio
async def test_failed_notification_keeps_previous_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:token")
    monkeypatch.setenv("ADMIN_TELEGRAM_ID", "123456789")
    state_path = tmp_path / "device.json"
    save_device_snapshot(state_path, PREVIOUS)
    bot = MagicMock()
    bot.session.close = AsyncMock()

    with (
        patch.object(cli, "fetch_tracked_device", new=AsyncMock(return_value=[CURRENT])),
        patch.object(cli, "Bot", return_value=bot),
        patch.object(
            cli,
            "send_device_change_to_telegram",
            new=AsyncMock(side_effect=RuntimeError("Telegram unavailable")),
        ),
        pytest.raises(RuntimeError, match="Telegram unavailable"),
    ):
        await cli.check_for_changes("https://example.test/main.py", 5.0, state_path)

    bot.session.close.assert_awaited_once()
    assert load_device_snapshot(state_path) == PREVIOUS
