import logging
from datetime import datetime

import pytz
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from hub_bot.core.settings import get_admin_telegram_id, get_app_timezone
from hub_bot.db.connection import get_session
from hub_bot.db.repository import UserRepository

logger = logging.getLogger(__name__)
router = Router(name=__name__)


@router.message(Command("stats"))
async def stats_handler(message: Message) -> None:
    """Show usage statistics to the configured administrator."""
    admin_id = get_admin_telegram_id()
    if not admin_id or not message.from_user or message.from_user.id != admin_id:
        await message.answer("Команда недоступна.")
        return

    try:
        async with get_session() as session:
            total = await UserRepository.count_total(session)
            new_7_days = await UserRepository.count_new_7_days(session)
            active_7_days = await UserRepository.count_active_7_days(session)
            now = datetime.now(pytz.timezone(get_app_timezone()))
            new_today = await UserRepository.count_new_today(session, now)

        await message.answer(
            "Статистика The Hub\n\n"
            f"Всего пользователей: {total}\n"
            f"Новых сегодня: {new_today}\n"
            f"Новых за 7 дней: {new_7_days}\n"
            f"Активных за 7 дней: {active_7_days}"
        )
    except Exception as error:
        logger.error("Error generating stats: %s", type(error).__name__, exc_info=True)
        await message.answer("Ошибка при получении статистики. Попробуйте позже.")
