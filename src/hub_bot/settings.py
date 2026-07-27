import os


def get_bot_token() -> str:
    """Read Telegram bot token from environment or raise ValueError."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        msg = (
            "TELEGRAM_BOT_TOKEN environment variable is not set. "
            "Set it before running the bot:\n"
            "  export TELEGRAM_BOT_TOKEN=your_bot_token_here\n"
            "  poetry run python -m hub_bot"
        )
        raise ValueError(msg)
    return token
