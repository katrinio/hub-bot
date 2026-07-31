"""User repository for database operations."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from hub_bot.db.models import User


class UserRepository:
    """Repository for User model operations."""

    @staticmethod
    async def upsert(
        session: AsyncSession,
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        language_code: str | None = None,
    ) -> User:
        """Create or update user, always updating last_seen_at.

        Args:
            session: AsyncSession for database operations
            telegram_id: Unique Telegram user ID
            username: Optional Telegram username (without @)
            first_name: Optional first name
            last_name: Optional last name
            language_code: Optional language code (e.g., 'en', 'ru')

        Returns:
            User instance (newly created or updated)

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            # Try to find existing user
            stmt = select(User).where(User.telegram_id == telegram_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if user:
                # Update existing user
                user.username = username
                user.first_name = first_name
                user.last_name = last_name
                user.language_code = language_code
                user.last_seen_at = datetime.now(UTC)
            else:
                # Create new user
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    language_code=language_code,
                    created_at=datetime.now(UTC),
                    last_seen_at=datetime.now(UTC),
                )
                session.add(user)

            await session.commit()
            return user
        except SQLAlchemyError:
            await session.rollback()
            raise

    @staticmethod
    async def get_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
        """Get user by Telegram ID.

        Args:
            session: AsyncSession
            telegram_id: Unique Telegram user ID

        Returns:
            User instance or None if not found
        """
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def count_total(session: AsyncSession) -> int:
        """Get total count of users."""
        stmt = select(func.count(User.id))
        result = await session.execute(stmt)
        return result.scalar() or 0

    @staticmethod
    async def count_new_today(session: AsyncSession, now: datetime) -> int:
        """Get count of users created today (start of day in app timezone).

        Args:
            session: AsyncSession
            now: Current datetime in app timezone (already converted)

        Returns:
            Count of users created since start of today (midnight UTC equivalent)
        """
        # Start of today: midnight in app timezone, converted to UTC
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Convert back to UTC for database query
        # (now is already in app tz, so we calculate UTC equivalent)
        utc_start = start_of_day.astimezone(UTC)

        stmt = select(func.count(User.id)).where(User.created_at >= utc_start)
        result = await session.execute(stmt)
        return result.scalar() or 0

    @staticmethod
    async def count_new_7_days(session: AsyncSession) -> int:
        """Get count of users created in last 7 days."""
        cutoff = datetime.now(UTC) - timedelta(days=7)
        stmt = select(func.count(User.id)).where(User.created_at >= cutoff)
        result = await session.execute(stmt)
        return result.scalar() or 0

    @staticmethod
    async def count_active_7_days(session: AsyncSession) -> int:
        """Get count of unique users active (last_seen_at) in last 7 days."""
        cutoff = datetime.now(UTC) - timedelta(days=7)
        stmt = select(func.count(User.id)).where(User.last_seen_at >= cutoff)
        result = await session.execute(stmt)
        return result.scalar() or 0
