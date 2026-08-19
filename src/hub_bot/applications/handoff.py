from urllib.parse import urlencode

from hub_bot.applications.tokens import create_auth_token_for_user
from hub_bot.db.connection import get_session


def build_postbox_auth_url(base_url: str, token: str) -> str:
    """Build a Postbox authentication URL with a signed handoff token."""
    if not base_url or not base_url.strip():
        raise ValueError("base_url cannot be empty")
    if not token or not token.strip():
        raise ValueError("token cannot be empty")
    return f"{base_url.rstrip('/')}/auth/hub?{urlencode({'token': token})}"


async def build_auth_url_for_user(telegram_user_id: int, audience: str, base_url: str) -> str:
    """Create a fresh token and return the application handoff URL."""
    async with get_session() as session:
        token = await create_auth_token_for_user(session, telegram_user_id=telegram_user_id, audience=audience)
    return build_postbox_auth_url(base_url, token)
