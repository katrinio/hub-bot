"""Telegram command for the current Asahi Linux device list."""

import logging
import math

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message

from hub_bot.devices.catalog import DeviceCatalog, RequestCooldown
from watcher import send_devices_to_telegram

logger = logging.getLogger(__name__)
router = Router(name=__name__)
device_catalog = DeviceCatalog()
devices_cooldown = RequestCooldown()


@router.message(Command("devices"))
async def devices_handler(message: Message, bot: Bot) -> None:
    """Download, parse, and send the current upstream DEVICES mapping."""
    cooldown_key = ("user", message.from_user.id) if message.from_user else ("chat", message.chat.id)
    retry_after = devices_cooldown.try_acquire(cooldown_key)
    if retry_after > 0:
        await message.answer(f"Список недавно запрашивали. Повтори через {math.ceil(retry_after)} сек.")
        return

    try:
        records = await device_catalog.get_devices()
        await send_devices_to_telegram(
            records,
            bot,
            message.chat.id,
            message_thread_id=message.message_thread_id,
        )
    except Exception as error:
        logger.error("Failed to send Asahi device list: %s", type(error).__name__, exc_info=True)
        await message.answer("Не удалось загрузить список устройств. Попробуй позже.")
