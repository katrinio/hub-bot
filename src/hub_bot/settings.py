import os

from dotenv import load_dotenv

# Load .env file
load_dotenv()


def get_bot_token() -> str:
    """Read Telegram bot token from environment (.env or export)."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        msg = (
            "TELEGRAM_BOT_TOKEN not found. "
            "Add it to .env file or set as environment variable:\n"
            "  export TELEGRAM_BOT_TOKEN=your_bot_token_here\n"
            "  poetry run python -m hub_bot"
        )
        raise ValueError(msg)
    return token


def get_postbox_url() -> str | None:
    """Read Postbox URL from environment or return None if not configured.

    Returns None if POSTBOX_URL is not set, allowing graceful degradation.
    Caller should handle None (e.g., show error to user without traceback).
    """
    url = os.environ.get("POSTBOX_URL", "").strip()
    if not url:
        return None
    # Normalize: remove trailing slash to prevent //auth/hub in URL
    return url.rstrip("/")


def get_admin_telegram_id() -> int | None:
    """Read admin Telegram ID from environment (for feedback and stats).

    Returns None if ADMIN_TELEGRAM_ID is not set, allowing graceful degradation.
    Caller should handle None (e.g., show error to user without capability).
    """
    admin_id = os.environ.get("ADMIN_TELEGRAM_ID", "").strip()
    if not admin_id:
        return None
    try:
        return int(admin_id)
    except ValueError:
        return None


def get_database_url() -> str:
    """Read database URL from environment.

    Returns:
        SQLAlchemy database URL (e.g., sqlite+aiosqlite:///./data/hub.db)

    Raises:
        ValueError: If DATABASE_URL is not set or invalid
    """
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        msg = (
            "DATABASE_URL not found. "
            "Add it to .env file:\n"
            "  export DATABASE_URL='sqlite+aiosqlite:///./data/hub.db'\n"
            "  poetry run python -m hub_bot"
        )
        raise ValueError(msg)
    return url


def get_app_timezone() -> str:
    """Read application timezone from environment.

    Used to calculate 'today' for statistics (e.g., new users today).
    Database stores all times in UTC.

    Returns:
        Timezone name (e.g., 'Europe/Belgrade', 'UTC')
        Defaults to 'Europe/Belgrade' if not set.
    """
    tz = os.environ.get("APP_TIMEZONE", "Europe/Belgrade").strip()
    if not tz:
        return "Europe/Belgrade"
    return tz


def validate_admin_telegram_id() -> None:
    """Validate ADMIN_TELEGRAM_ID configuration on startup.

    Raises:
        ValueError: If the value is set but not a valid integer
    """
    admin_id = os.environ.get("ADMIN_TELEGRAM_ID", "").strip()
    if not admin_id:
        # Not set is OK (stats command will be unavailable)
        return

    try:
        int(admin_id)
    except ValueError:
        msg = f"Invalid ADMIN_TELEGRAM_ID: must be a number. Got: {admin_id!r}"
        raise ValueError(msg)
