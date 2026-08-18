"""Telegram command for the current Asahi Linux device list."""

import logging

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message

from watcher.parse_devices import fetch_devices, send_devices_to_telegram

logger = logging.getLogger(__name__)
router = Router(name=__name__)


@router.message(Command("devices"))
async def devices_handler(message: Message, bot: Bot) -> None:
    """Download, parse, and send the current upstream DEVICES mapping."""
    try:
        records = await fetch_devices()
        await send_devices_to_telegram(records, bot, message.chat.id)
    except Exception as error:
        logger.error("Failed to send Asahi device list: %s", type(error).__name__, exc_info=True)
        await message.answer("Не удалось загрузить список устройств. Попробуй позже.")
