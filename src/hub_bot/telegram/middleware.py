"""Middleware for automatic Telegram user tracking."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from sqlalchemy.exc import SQLAlchemyError

from hub_bot.db.connection import get_session
from hub_bot.db.repository import UserRepository

logger = logging.getLogger(__name__)


class UserTrackingMiddleware(BaseMiddleware):
    """Save the latest Telegram profile seen in each incoming update."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Update):
            await self._track_user(event)
        return await handler(event, data)

    @staticmethod
    async def _track_user(update: Update) -> bool:
        from_user = None
        if update.message and update.message.from_user:
            from_user = update.message.from_user
        elif update.callback_query and update.callback_query.from_user:
            from_user = update.callback_query.from_user

        if not from_user or from_user.is_bot:
            return False

        try:
            async with get_session() as session:
                await UserRepository.upsert(
                    session,
                    telegram_id=from_user.id,
                    username=from_user.username,
                    first_name=from_user.first_name,
                    last_name=from_user.last_name,
                    language_code=from_user.language_code,
                )
            return True
        except SQLAlchemyError as error:
            logger.error("Failed to track user %s: %s", from_user.id, type(error).__name__, exc_info=True)
            return False
        except Exception as error:
            logger.error("Unexpected error tracking user %s: %s", from_user.id, type(error).__name__, exc_info=True)
            return False
