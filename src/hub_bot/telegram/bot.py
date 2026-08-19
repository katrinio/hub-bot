from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from hub_bot.telegram.handlers import router
from hub_bot.telegram.middleware import UserTrackingMiddleware


async def create_bot(token: str) -> Bot:
    """Create and configure the Telegram bot client."""
    bot = Bot(token=token)
    await bot.set_my_commands(
        commands=[
            BotCommand(command="start", description="Start the bot"),
            BotCommand(command="devices", description="Отслеживаемое устройство Asahi"),
            BotCommand(command="stats", description="Show statistics (admin only)"),
        ]
    )
    return bot


def create_dispatcher() -> Dispatcher:
    """Compose storage, middleware, and feature routers."""
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.update.middleware(UserTrackingMiddleware())
    dispatcher.include_router(router)
    return dispatcher
