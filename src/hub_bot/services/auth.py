from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from hub_bot.core.settings import get_auth_secret
from hub_bot.db.models import User
from hub_bot.db.repository import UserRepository

ISSUER = "the-hub-bot"
TTL_MINUTES = 5


def create_auth_token(
    telegram_user_id: int,
    audience: str,
    now: datetime | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Generate a short-lived JWT handoff token for an application."""
    if telegram_user_id <= 0:
        raise ValueError(f"Invalid telegram_user_id: {telegram_user_id} (must be positive)")
    if not audience or not audience.strip():
        raise ValueError("audience cannot be empty or whitespace")

    now = now or datetime.now(timezone.utc)  # noqa: UP017
    payload = {
        "sub": str(telegram_user_id),
        "aud": audience.strip(),
        "iss": ISSUER,
        "iat": now,
        "exp": now + timedelta(minutes=TTL_MINUTES),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, get_auth_secret(), algorithm="HS256")


def _telegram_profile_claims(user: User) -> dict[str, int | str | None]:
    return {
        "telegram_id": user.telegram_id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "language_code": user.language_code,
    }


async def create_auth_token_for_user(
    session: AsyncSession,
    telegram_user_id: int,
    audience: str,
    now: datetime | None = None,
) -> str:
    """Generate a handoff token using the latest saved Telegram profile."""
    user = await UserRepository.get_by_telegram_id(session, telegram_user_id)
    if user is None:
        raise ValueError(f"Hub user not found for telegram_user_id={telegram_user_id}")
    return create_auth_token(
        telegram_user_id=telegram_user_id,
        audience=audience,
        now=now,
        extra_claims=_telegram_profile_claims(user),
    )
