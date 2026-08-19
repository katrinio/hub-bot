"""Command-line entry point for the standalone Asahi device watcher."""

import argparse
import asyncio
import os
from pathlib import Path

from aiogram import Bot
from dotenv import load_dotenv

from watcher.monitoring import DEFAULT_STATE_PATH, load_device_snapshot, save_device_snapshot
from watcher.parser import DEFAULT_SOURCE_URL
from watcher.telegram import format_devices, send_device_change_to_telegram, send_devices_to_telegram
from watcher.tracking import fetch_tracked_device


def _required_environment_variable(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"Не задана обязательная переменная окружения {name}")
    return value


def _admin_telegram_id() -> int:
    value = _required_environment_variable("ADMIN_TELEGRAM_ID")
    try:
        admin_id = int(value)
    except ValueError:
        raise ValueError("ADMIN_TELEGRAM_ID должен быть числом") from None
    if admin_id <= 0:
        raise ValueError("ADMIN_TELEGRAM_ID должен быть положительным числом")
    return admin_id


async def run(url: str, timeout: float) -> tuple[int, int]:
    """Download, parse, and send the current device list."""
    token = _required_environment_variable("TELEGRAM_BOT_TOKEN")
    admin_id = _admin_telegram_id()
    records = await fetch_tracked_device(url, timeout)

    bot = Bot(token=token)
    try:
        message_count = await send_devices_to_telegram(records, bot, admin_id)
    finally:
        await bot.session.close()
    return len(records), message_count


async def check_for_changes(url: str, timeout: float, state_path: Path) -> str:
    """Notify the administrator only when the monitored device changes."""
    current = (await fetch_tracked_device(url, timeout))[0]
    previous = load_device_snapshot(state_path)
    if previous is None:
        save_device_snapshot(state_path, current)
        return f"Baseline сохранён: {current.device_id}. Сообщение не отправлено."
    if previous == current:
        return f"Изменений нет: {current.device_id}. Сообщение не отправлено."

    token = _required_environment_variable("TELEGRAM_BOT_TOKEN")
    admin_id = _admin_telegram_id()
    bot = Bot(token=token)
    try:
        await send_device_change_to_telegram(previous, current, bot, admin_id)
    finally:
        await bot.session.close()
    save_device_snapshot(state_path, current)
    return f"Изменение обнаружено: {current.device_id}. Сообщение отправлено."


def main() -> None:
    load_dotenv()
    argument_parser = argparse.ArgumentParser(description="Отправить список устройств Asahi Linux в Telegram.")
    argument_parser.add_argument("--url", default=DEFAULT_SOURCE_URL, help="URL исходного src/main.py")
    argument_parser.add_argument("--timeout", type=float, default=30.0, help="таймаут загрузки в секундах")
    mode = argument_parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="вывести результат без отправки в Telegram")
    mode.add_argument("--check", action="store_true", help="отправить сообщение только при изменении устройства")
    argument_parser.add_argument(
        "--state-path",
        type=Path,
        default=Path(os.environ.get("WATCHER_STATE_PATH", DEFAULT_STATE_PATH)),
        help="путь к snapshot для --check",
    )
    args = argument_parser.parse_args()

    if args.dry_run:
        records = asyncio.run(fetch_tracked_device(args.url, args.timeout))
        print(format_devices(records))
        return

    if args.check:
        print(asyncio.run(check_for_changes(args.url, args.timeout, args.state_path)))
        return

    device_count, message_count = asyncio.run(run(args.url, args.timeout))
    print(f"Отправлено устройств: {device_count}; сообщений: {message_count}.")
