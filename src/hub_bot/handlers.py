from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("start"))
async def start_handler(message: Message) -> None:
    """Handle /start command."""
    response = (
        "The Hub\n\n"
        "Единая точка входа в мои приложения.\n\n"
        "Пока здесь тихо, но скоро появятся первые сервисы."
    )
    await message.answer(response)
