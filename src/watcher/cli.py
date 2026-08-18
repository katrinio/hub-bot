"""Command-line entry point for the standalone Asahi device watcher."""

import argparse
import asyncio
import os

from aiogram import Bot
from dotenv import load_dotenv

from watcher.parser import DEFAULT_SOURCE_URL, fetch_devices
from watcher.telegram import format_devices, send_devices_to_telegram


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
    records = await fetch_devices(url, timeout)

    bot = Bot(token=token)
    try:
        message_count = await send_devices_to_telegram(records, bot, admin_id)
    finally:
        await bot.session.close()
    return len(records), message_count


def main() -> None:
    load_dotenv()
    argument_parser = argparse.ArgumentParser(description="Отправить список устройств Asahi Linux в Telegram.")
    argument_parser.add_argument("--url", default=DEFAULT_SOURCE_URL, help="URL исходного src/main.py")
    argument_parser.add_argument("--timeout", type=float, default=30.0, help="таймаут загрузки в секундах")
    argument_parser.add_argument("--dry-run", action="store_true", help="вывести результат без отправки в Telegram")
    args = argument_parser.parse_args()

    if args.dry_run:
        records = asyncio.run(fetch_devices(args.url, args.timeout))
        print(format_devices(records))
        return

    device_count, message_count = asyncio.run(run(args.url, args.timeout))
    print(f"Отправлено устройств: {device_count}; сообщений: {message_count}.")
