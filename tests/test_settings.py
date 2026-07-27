import os

import pytest

from hub_bot.settings import get_bot_token, get_postbox_url


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


def test_get_postbox_url_from_env() -> None:
    """Test that Postbox URL is read from environment."""
    test_url = "https://postbox.finpipe.net"
    os.environ["POSTBOX_URL"] = test_url

    try:
        url = get_postbox_url()
        assert url == test_url
    finally:
        os.environ.pop("POSTBOX_URL", None)


def test_get_postbox_url_missing() -> None:
    """Test that missing POSTBOX_URL returns None (graceful degradation)."""
    os.environ.pop("POSTBOX_URL", None)

    url = get_postbox_url()
    assert url is None


def test_get_postbox_url_empty() -> None:
    """Test that empty POSTBOX_URL returns None."""
    os.environ["POSTBOX_URL"] = ""

    try:
        url = get_postbox_url()
        assert url is None
    finally:
        os.environ.pop("POSTBOX_URL", None)


def test_get_postbox_url_whitespace() -> None:
    """Test that whitespace-only POSTBOX_URL returns None."""
    os.environ["POSTBOX_URL"] = "   "

    try:
        url = get_postbox_url()
        assert url is None
    finally:
        os.environ.pop("POSTBOX_URL", None)


def test_get_postbox_url_trailing_slash() -> None:
    """Test that trailing slash is removed from Postbox URL."""
    os.environ["POSTBOX_URL"] = "https://postbox.finpipe.net/"

    try:
        url = get_postbox_url()
        assert url == "https://postbox.finpipe.net"
        assert not url.endswith("/")
    finally:
        os.environ.pop("POSTBOX_URL", None)


def test_get_postbox_url_multiple_trailing_slashes() -> None:
    """Test that multiple trailing slashes are removed."""
    os.environ["POSTBOX_URL"] = "https://postbox.finpipe.net///"

    try:
        url = get_postbox_url()
        assert url == "https://postbox.finpipe.net"
        assert not url.endswith("/")
    finally:
        os.environ.pop("POSTBOX_URL", None)
