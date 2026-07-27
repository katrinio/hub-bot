import os
from datetime import datetime, timedelta, timezone

import jwt

ISSUER = "the-hub-bot"
TTL_MINUTES = 5


def get_auth_secret() -> str:
    """Read signing secret from environment or raise ValueError.

    TODO (future refactoring): Move to settings.py for unified configuration.
    Currently reads directly from os.environ like legacy code. Consolidate with
    get_bot_token(), get_postbox_url() into single settings module.
    """
    secret = os.environ.get("HUB_AUTH_SECRET", "").strip()
    if not secret:
        msg = (
            "HUB_AUTH_SECRET not found. "
            "Add it to .env file or set as environment variable:\n"
            "  export HUB_AUTH_SECRET=your_secret_key_here\n"
            "  poetry run python -m hub_bot"
        )
        raise ValueError(msg)
    return secret


def create_auth_token(
    telegram_user_id: int,
    audience: str,
    now: datetime | None = None,
) -> str:
    """
    Generate JWT auth token for Telegram user.

    Args:
        telegram_user_id: Telegram user ID (must be positive)
        audience: Target application slug (e.g., 'postbox')
        now: Optional current time for testing (defaults to UTC now)

    Returns:
        Signed JWT token as string

    Raises:
        ValueError: If telegram_user_id is invalid or audience is empty
    """
    if telegram_user_id <= 0:
        msg = f"Invalid telegram_user_id: {telegram_user_id} (must be positive)"
        raise ValueError(msg)

    if not audience or not audience.strip():
        msg = "audience cannot be empty or whitespace"
        raise ValueError(msg)

    audience = audience.strip()

    # Use provided time or current UTC time
    if now is None:
        now = datetime.now(timezone.utc)  # noqa: UP017

    exp = now + timedelta(minutes=TTL_MINUTES)

    payload = {
        "sub": str(telegram_user_id),
        "aud": audience,
        "iss": ISSUER,
        "iat": now,
        "exp": exp,
    }

    secret = get_auth_secret()
    return jwt.encode(payload, secret, algorithm="HS256")
