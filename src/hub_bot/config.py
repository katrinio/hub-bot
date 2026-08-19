import os

from dotenv import load_dotenv

load_dotenv()


def get_bot_token() -> str:
    """Read Telegram bot token from environment."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        msg = (
            "TELEGRAM_BOT_TOKEN not found. Add it to .env file or set as environment variable:\n"
            "  export TELEGRAM_BOT_TOKEN=your_bot_token_here\n"
            "  poetry run python -m hub_bot"
        )
        raise ValueError(msg)
    return token


def get_auth_secret() -> str:
    """Read the secret used to sign application handoff tokens."""
    secret = os.environ.get("HUB_AUTH_SECRET", "").strip()
    if not secret:
        msg = (
            "HUB_AUTH_SECRET not found. Add it to .env file or set as environment variable:\n"
            "  export HUB_AUTH_SECRET=your_secret_key_here\n"
            "  poetry run python -m hub_bot"
        )
        raise ValueError(msg)
    return secret


def get_postbox_url() -> str | None:
    """Read and normalize the Postbox URL, if configured."""
    url = os.environ.get("POSTBOX_URL", "").strip()
    return url.rstrip("/") if url else None


def get_admin_telegram_id() -> int | None:
    """Return the configured administrator ID, or None when unavailable."""
    admin_id = os.environ.get("ADMIN_TELEGRAM_ID", "").strip()
    if not admin_id:
        return None
    try:
        return int(admin_id)
    except ValueError:
        return None


def get_database_url() -> str:
    """Read the SQLAlchemy database URL."""
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        msg = (
            "DATABASE_URL not found. Add it to .env file:\n"
            "  export DATABASE_URL='sqlite+aiosqlite:///./data/hub.db'\n"
            "  poetry run python -m hub_bot"
        )
        raise ValueError(msg)
    return url


def get_app_timezone() -> str:
    """Return the timezone used for calendar-based statistics."""
    return os.environ.get("APP_TIMEZONE", "Europe/Belgrade").strip() or "Europe/Belgrade"


def validate_admin_telegram_id() -> None:
    """Validate an optional administrator ID during startup."""
    admin_id = os.environ.get("ADMIN_TELEGRAM_ID", "").strip()
    if not admin_id:
        return
    try:
        int(admin_id)
    except ValueError:
        raise ValueError(f"Invalid ADMIN_TELEGRAM_ID: must be a number. Got: {admin_id!r}") from None
