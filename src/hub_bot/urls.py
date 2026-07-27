"""URL builders for Hub applications."""

from urllib.parse import urlencode


def build_postbox_auth_url(base_url: str, token: str) -> str:
    """Build Postbox authentication URL with signed JWT token.

    Args:
        base_url: Postbox base URL (e.g., 'https://postbox.finpipe.net')
        token: Signed JWT token from create_auth_token()

    Returns:
        Full URL: {base_url}/auth/hub?token={encoded_token}

    Raises:
        ValueError: If base_url or token is empty
    """
    if not base_url or not base_url.strip():
        msg = "base_url cannot be empty"
        raise ValueError(msg)

    if not token or not token.strip():
        msg = "token cannot be empty"
        raise ValueError(msg)

    # Remove trailing slash to prevent //auth/hub
    base_url = base_url.rstrip("/")

    # Properly encode token as query parameter
    query_params = {"token": token}
    return f"{base_url}/auth/hub?{urlencode(query_params)}"
