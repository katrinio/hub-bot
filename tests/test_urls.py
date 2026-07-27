"""Tests for URL builders."""

import pytest

from hub_bot.urls import build_postbox_auth_url


def test_build_postbox_auth_url_valid() -> None:
    """Test that valid base_url and token produce correct auth URL."""
    base_url = "https://postbox.finpipe.net"
    token = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzdWIiOiIxMjM0NTY3ODkifQ."
        "dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
    )

    url = build_postbox_auth_url(base_url, token)

    assert url.startswith("https://postbox.finpipe.net/auth/hub?")
    assert "token=" in url
    assert token in url


def test_build_postbox_auth_url_removes_trailing_slash() -> None:
    """Test that trailing slash in base_url is removed."""
    base_url = "https://postbox.finpipe.net/"
    token = "fake-token"

    url = build_postbox_auth_url(base_url, token)

    assert url.startswith("https://postbox.finpipe.net/auth/hub?")
    assert "//" not in url.replace("://", "")  # Ensure no double slashes except in protocol


def test_build_postbox_auth_url_encodes_token() -> None:
    """Test that token with special characters is properly URL-encoded."""
    base_url = "https://postbox.finpipe.net"
    token = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzdWIiOiIxMjM0NTY3ODkifQ."
        "dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
    )

    url = build_postbox_auth_url(base_url, token)

    # Token should be in the URL (possibly URL-encoded)
    assert token in url or token.replace(".", "%2E") in url


def test_build_postbox_auth_url_empty_base_url() -> None:
    """Test that empty base_url raises ValueError."""
    with pytest.raises(ValueError, match="base_url cannot be empty"):
        build_postbox_auth_url("", "token")


def test_build_postbox_auth_url_whitespace_base_url() -> None:
    """Test that whitespace-only base_url raises ValueError."""
    with pytest.raises(ValueError, match="base_url cannot be empty"):
        build_postbox_auth_url("   ", "token")


def test_build_postbox_auth_url_empty_token() -> None:
    """Test that empty token raises ValueError."""
    with pytest.raises(ValueError, match="token cannot be empty"):
        build_postbox_auth_url("https://postbox.finpipe.net", "")


def test_build_postbox_auth_url_whitespace_token() -> None:
    """Test that whitespace-only token raises ValueError."""
    with pytest.raises(ValueError, match="token cannot be empty"):
        build_postbox_auth_url("https://postbox.finpipe.net", "   ")


def test_build_postbox_auth_url_query_parameter_format() -> None:
    """Test that URL follows correct query parameter format."""
    base_url = "https://postbox.finpipe.net"
    token = "test-token-123"

    url = build_postbox_auth_url(base_url, token)

    assert url == f"https://postbox.finpipe.net/auth/hub?token={token}"
