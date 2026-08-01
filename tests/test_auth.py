import os
from collections.abc import AsyncIterator
from datetime import datetime, timezone

import jwt
import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from hub_bot.auth import ISSUER, TTL_MINUTES, create_auth_token, create_auth_token_for_user, get_auth_secret
from hub_bot.db.models import Base
from hub_bot.db.repository import UserRepository


@pytest.fixture
async def test_db() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield async_sessionmaker(engine, expire_on_commit=False)

    await engine.dispose()


@pytest.fixture
async def session(test_db: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    async with test_db() as session:
        yield session


def test_get_auth_secret_from_env() -> None:
    """Test that auth secret is read from environment."""
    test_secret = "test-secret-key-12345"
    os.environ["HUB_AUTH_SECRET"] = test_secret

    try:
        secret = get_auth_secret()
        assert secret == test_secret
    finally:
        os.environ.pop("HUB_AUTH_SECRET", None)


def test_get_auth_secret_missing() -> None:
    """Test that missing HUB_AUTH_SECRET raises ValueError with helpful message."""
    os.environ.pop("HUB_AUTH_SECRET", None)

    with pytest.raises(ValueError, match="HUB_AUTH_SECRET"):
        get_auth_secret()


def test_get_auth_secret_empty() -> None:
    """Test that empty HUB_AUTH_SECRET raises ValueError."""
    os.environ["HUB_AUTH_SECRET"] = ""

    try:
        with pytest.raises(ValueError, match="HUB_AUTH_SECRET"):
            get_auth_secret()
    finally:
        os.environ.pop("HUB_AUTH_SECRET", None)


def test_create_auth_token_returns_string() -> None:
    """Test that create_auth_token returns a string JWT."""
    os.environ["HUB_AUTH_SECRET"] = "test-secret"

    try:
        token = create_auth_token(123456789, "postbox")
        assert isinstance(token, str)
        assert len(token) > 0
    finally:
        os.environ.pop("HUB_AUTH_SECRET", None)


def test_create_auth_token_signature_valid() -> None:
    """Test that token signature is valid with correct secret."""
    secret = "test-secret-key"
    os.environ["HUB_AUTH_SECRET"] = secret

    try:
        token = create_auth_token(123456789, "postbox")
        decoded = jwt.decode(token, secret, algorithms=["HS256"], audience="postbox")
        assert decoded is not None
    finally:
        os.environ.pop("HUB_AUTH_SECRET", None)


def test_create_auth_token_invalid_signature() -> None:
    """Test that token cannot be verified with wrong secret."""
    secret = "correct-secret"
    wrong_secret = "wrong-secret"
    os.environ["HUB_AUTH_SECRET"] = secret

    try:
        token = create_auth_token(123456789, "postbox")
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(token, wrong_secret, algorithms=["HS256"])
    finally:
        os.environ.pop("HUB_AUTH_SECRET", None)


def test_create_auth_token_sub_claim() -> None:
    """Test that sub claim contains Telegram user ID as string."""
    os.environ["HUB_AUTH_SECRET"] = "test-secret"

    try:
        telegram_id = 987654321
        token = create_auth_token(telegram_id, "postbox")
        decoded = jwt.decode(token, "test-secret", algorithms=["HS256"], audience="postbox")
        assert decoded["sub"] == str(telegram_id)
    finally:
        os.environ.pop("HUB_AUTH_SECRET", None)


def test_create_auth_token_aud_claim() -> None:
    """Test that aud claim matches provided audience."""
    os.environ["HUB_AUTH_SECRET"] = "test-secret"

    try:
        token = create_auth_token(123456789, "postbox")
        decoded = jwt.decode(token, "test-secret", algorithms=["HS256"], audience="postbox")
        assert decoded["aud"] == "postbox"
    finally:
        os.environ.pop("HUB_AUTH_SECRET", None)


def test_create_auth_token_iss_claim() -> None:
    """Test that iss claim is set to the-hub-bot."""
    os.environ["HUB_AUTH_SECRET"] = "test-secret"

    try:
        token = create_auth_token(123456789, "postbox")
        decoded = jwt.decode(token, "test-secret", algorithms=["HS256"], audience="postbox")
        assert decoded["iss"] == ISSUER
    finally:
        os.environ.pop("HUB_AUTH_SECRET", None)


def test_create_auth_token_iat_and_exp() -> None:
    """Test that iat and exp claims are present."""
    os.environ["HUB_AUTH_SECRET"] = "test-secret"

    try:
        token = create_auth_token(123456789, "postbox")
        decoded = jwt.decode(token, "test-secret", algorithms=["HS256"], audience="postbox")
        assert "iat" in decoded
        assert "exp" in decoded
    finally:
        os.environ.pop("HUB_AUTH_SECRET", None)


def test_create_auth_token_ttl() -> None:
    """Test that exp - iat is approximately TTL_MINUTES."""
    os.environ["HUB_AUTH_SECRET"] = "test-secret"

    try:
        now = datetime.now(timezone.utc)  # noqa: UP017
        token = create_auth_token(123456789, "postbox", now=now)
        decoded = jwt.decode(
            token,
            "test-secret",
            algorithms=["HS256"],
            audience="postbox",
            # Use the same time for validation to avoid expiration issues
            options={"verify_exp": False},
        )

        iat = decoded["iat"]
        exp = decoded["exp"]
        ttl_seconds = exp - iat

        assert ttl_seconds == TTL_MINUTES * 60
    finally:
        os.environ.pop("HUB_AUTH_SECRET", None)


def test_create_auth_token_invalid_user_id_negative() -> None:
    """Test that negative telegram_user_id raises ValueError."""
    os.environ["HUB_AUTH_SECRET"] = "test-secret"

    try:
        with pytest.raises(ValueError, match="Invalid telegram_user_id"):
            create_auth_token(-123, "postbox")
    finally:
        os.environ.pop("HUB_AUTH_SECRET", None)


def test_create_auth_token_invalid_user_id_zero() -> None:
    """Test that zero telegram_user_id raises ValueError."""
    os.environ["HUB_AUTH_SECRET"] = "test-secret"

    try:
        with pytest.raises(ValueError, match="Invalid telegram_user_id"):
            create_auth_token(0, "postbox")
    finally:
        os.environ.pop("HUB_AUTH_SECRET", None)


def test_create_auth_token_empty_audience() -> None:
    """Test that empty audience raises ValueError."""
    os.environ["HUB_AUTH_SECRET"] = "test-secret"

    try:
        with pytest.raises(ValueError, match="audience cannot be empty"):
            create_auth_token(123456789, "")
    finally:
        os.environ.pop("HUB_AUTH_SECRET", None)


def test_create_auth_token_whitespace_audience() -> None:
    """Test that whitespace-only audience raises ValueError."""
    os.environ["HUB_AUTH_SECRET"] = "test-secret"

    try:
        with pytest.raises(ValueError, match="audience cannot be empty"):
            create_auth_token(123456789, "   ")
    finally:
        os.environ.pop("HUB_AUTH_SECRET", None)


def test_create_auth_token_custom_time() -> None:
    """Test that custom now parameter is used for iat/exp."""
    os.environ["HUB_AUTH_SECRET"] = "test-secret"

    try:
        custom_time = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)  # noqa: UP017
        token = create_auth_token(123456789, "postbox", now=custom_time)
        decoded = jwt.decode(
            token,
            "test-secret",
            algorithms=["HS256"],
            audience="postbox",
            # Use the custom time for validation
            options={"verify_exp": False},
        )

        assert decoded["iat"] == int(custom_time.timestamp())
    finally:
        os.environ.pop("HUB_AUTH_SECRET", None)


@pytest.mark.asyncio
async def test_create_auth_token_for_user_contains_telegram_profile_claims(session: AsyncSession) -> None:
    os.environ["HUB_AUTH_SECRET"] = "test-secret"

    try:
        await UserRepository.upsert(
            session,
            telegram_id=123456789,
            username="example",
            first_name="Katrin",
            last_name="Example",
            language_code="ru",
        )

        token = await create_auth_token_for_user(session, 123456789, "postbox")
        decoded = jwt.decode(token, "test-secret", algorithms=["HS256"], audience="postbox")

        assert decoded["telegram_id"] == 123456789
        assert decoded["first_name"] == "Katrin"
        assert decoded["last_name"] == "Example"
        assert decoded["username"] == "example"
        assert decoded["language_code"] == "ru"
    finally:
        os.environ.pop("HUB_AUTH_SECRET", None)


@pytest.mark.asyncio
async def test_create_auth_token_for_user_serializes_nullable_profile_claims(session: AsyncSession) -> None:
    os.environ["HUB_AUTH_SECRET"] = "test-secret"

    try:
        await UserRepository.upsert(
            session,
            telegram_id=123456789,
            username=None,
            first_name=None,
            last_name=None,
            language_code=None,
        )

        token = await create_auth_token_for_user(session, 123456789, "postbox")
        decoded = jwt.decode(token, "test-secret", algorithms=["HS256"], audience="postbox")

        assert decoded["telegram_id"] == 123456789
        assert decoded["first_name"] is None
        assert decoded["last_name"] is None
        assert decoded["username"] is None
        assert decoded["language_code"] is None
    finally:
        os.environ.pop("HUB_AUTH_SECRET", None)


@pytest.mark.asyncio
async def test_create_auth_token_for_user_preserves_required_claims(session: AsyncSession) -> None:
    os.environ["HUB_AUTH_SECRET"] = "test-secret"

    try:
        now = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)  # noqa: UP017
        await UserRepository.upsert(session, telegram_id=987654321, first_name="Test")

        token = await create_auth_token_for_user(session, 987654321, "postbox", now=now)
        decoded = jwt.decode(
            token,
            "test-secret",
            algorithms=["HS256"],
            audience="postbox",
            options={"verify_exp": False},
        )

        assert decoded["sub"] == "987654321"
        assert decoded["aud"] == "postbox"
        assert decoded["iss"] == ISSUER
        assert decoded["iat"] == int(now.timestamp())
        assert decoded["exp"] - decoded["iat"] == TTL_MINUTES * 60
    finally:
        os.environ.pop("HUB_AUTH_SECRET", None)


@pytest.mark.asyncio
async def test_create_auth_token_for_user_uses_requested_user_row(session: AsyncSession) -> None:
    os.environ["HUB_AUTH_SECRET"] = "test-secret"

    try:
        await UserRepository.upsert(session, telegram_id=111, username="first", first_name="First")
        await UserRepository.upsert(session, telegram_id=222, username="second", first_name="Second")

        token = await create_auth_token_for_user(session, 222, "postbox")
        decoded = jwt.decode(token, "test-secret", algorithms=["HS256"], audience="postbox")

        assert decoded["sub"] == "222"
        assert decoded["telegram_id"] == 222
        assert decoded["first_name"] == "Second"
        assert decoded["username"] == "second"
    finally:
        os.environ.pop("HUB_AUTH_SECRET", None)


@pytest.mark.asyncio
async def test_create_auth_token_for_user_requires_existing_hub_user(session: AsyncSession) -> None:
    os.environ["HUB_AUTH_SECRET"] = "test-secret"

    try:
        with pytest.raises(ValueError, match="Hub user not found"):
            await create_auth_token_for_user(session, 404, "postbox")
    finally:
        os.environ.pop("HUB_AUTH_SECRET", None)


@pytest.mark.asyncio
async def test_create_auth_token_for_user_db_read_error_does_not_issue_token(session: AsyncSession) -> None:
    os.environ["HUB_AUTH_SECRET"] = "test-secret"

    try:
        await session.execute(text("DROP TABLE users"))
        await session.commit()

        with pytest.raises(SQLAlchemyError):
            await create_auth_token_for_user(session, 123456789, "postbox")
    finally:
        os.environ.pop("HUB_AUTH_SECRET", None)
