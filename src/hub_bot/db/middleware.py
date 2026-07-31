"""Middleware for automatic user tracking."""

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
    """Middleware to track user interactions with the bot.

    Saves or updates user on every message and callback_query.
    Errors don't break the bot; they're logged and rolled back.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Process update and track user if present.

        Args:
            handler: Next middleware or handler
            event: Telegram event (Update)
            data: Middleware data

        Returns:
            Handler result
        """
        if isinstance(event, Update):
            await self._track_user(event)

        return await handler(event, data)

    @staticmethod
    async def _track_user(update: Update) -> bool:
        """Track user from update if applicable.

        Handles updates that contain from_user (message, callback_query, etc.).
        Skips updates without from_user or from bot accounts gracefully.

        Args:
            update: Telegram update

        Returns:
            True if user was tracked, False if tracking was skipped
        """
        # Determine source and extract from_user
        from_user = None
        if update.message and update.message.from_user:
            from_user = update.message.from_user
        elif update.callback_query and update.callback_query.from_user:
            from_user = update.callback_query.from_user
        # Other update types (channel_post, etc.) may not have from_user

        if not from_user:
            # No user to track, skip silently
            logger.debug("Skipping tracking: update has no from_user")
            return False

        if from_user.is_bot:
            # Don't track bot accounts
            logger.debug("Skipping tracking: user is a bot (id=%s)", from_user.id)
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
        except SQLAlchemyError as e:
            logger.error(
                "Failed to track user %s: %s",
                from_user.id,
                type(e).__name__,
                exc_info=True,
            )
            return False
        except Exception as e:
            logger.error(
                "Unexpected error tracking user %s: %s",
                from_user.id,
                type(e).__name__,
                exc_info=True,
            )
            return False
