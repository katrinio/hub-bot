import os

import pytest

from hub_bot.settings import get_bot_token


def test_get_bot_token_from_env() -> None:
    """Test that bot token is read from environment."""
    test_token = "123:ABC-xyz"
    os.environ["TELEGRAM_BOT_TOKEN"] = test_token

    try:
        token = get_bot_token()
        assert token == test_token
    finally:
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)


def test_get_bot_token_missing() -> None:
    """Test that missing TELEGRAM_BOT_TOKEN raises ValueError with helpful message."""
    os.environ.pop("TELEGRAM_BOT_TOKEN", None)

    with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
        get_bot_token()


def test_get_bot_token_empty_string() -> None:
    """Test that empty TELEGRAM_BOT_TOKEN raises ValueError."""
    os.environ["TELEGRAM_BOT_TOKEN"] = ""

    try:
        with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
            get_bot_token()
    finally:
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)


def test_get_bot_token_whitespace() -> None:
    """Test that whitespace-only TELEGRAM_BOT_TOKEN raises ValueError."""
    os.environ["TELEGRAM_BOT_TOKEN"] = "   "

    try:
        with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
            get_bot_token()
    finally:
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
