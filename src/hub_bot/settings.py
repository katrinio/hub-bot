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
