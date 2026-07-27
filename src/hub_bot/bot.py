import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from hub_bot.handlers import router

logger = logging.getLogger(__name__)


async def create_bot(token: str) -> Bot:
    """Create and configure Telegram bot instance."""
    bot = Bot(token=token)
    # Set bot commands
    await bot.set_my_commands(
        commands=[
            BotCommand(command="start", description="Start the bot"),
        ]
    )
    return bot


def create_dispatcher() -> Dispatcher:
    """Create Dispatcher with FSM storage and register routers."""
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(router)
    return dp
