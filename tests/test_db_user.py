"""Tests for user database operations."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from hub_bot.db.models import Base, User
from hub_bot.db.repository import UserRepository


@pytest.fixture
async def test_db() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Create a temporary test database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    yield TestSessionLocal

    await engine.dispose()


@pytest.fixture
async def session(test_db: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    """Provide a test database session."""
    async with test_db() as session:
        yield session


@pytest.mark.asyncio
async def test_upsert_creates_new_user(session: AsyncSession) -> None:
    """Test that upsert creates a new user."""
    user = await UserRepository.upsert(
        session,
        telegram_id=123456789,
        username="testuser",
        first_name="Test",
        last_name="User",
        language_code="en",
    )

    assert user.telegram_id == 123456789
    assert user.username == "testuser"
    assert user.first_name == "Test"
    assert user.last_name == "User"
    assert user.language_code == "en"
    assert user.created_at is not None
    assert user.last_seen_at is not None


@pytest.mark.asyncio
async def test_upsert_does_not_duplicate(session: AsyncSession) -> None:
    """Test that repeated upsert doesn't create duplicate users."""
    telegram_id = 123456789

    # First upsert
    user1 = await UserRepository.upsert(session, telegram_id=telegram_id)
    count1 = await UserRepository.count_total(session)

    # Second upsert (same telegram_id)
    user2 = await UserRepository.upsert(session, telegram_id=telegram_id)
    count2 = await UserRepository.count_total(session)

    assert count1 == 1
    assert count2 == 1  # No new user created
    assert user1.id == user2.id  # Same user returned


@pytest.mark.asyncio
async def test_upsert_updates_last_seen_at(session: AsyncSession) -> None:
    """Test that upsert updates last_seen_at on repeat interaction."""
    telegram_id = 123456789

    # First upsert
    user1 = await UserRepository.upsert(session, telegram_id=telegram_id)
    first_seen = user1.last_seen_at

    # Wait a bit and upsert again
    await session.refresh(user1)  # Reload to ensure fresh data
    user2 = await UserRepository.upsert(session, telegram_id=telegram_id)
    second_seen = user2.last_seen_at

    # second_seen should be >= first_seen
    assert second_seen >= first_seen


@pytest.mark.asyncio
async def test_upsert_syncs_username(session: AsyncSession) -> None:
    """Test that upsert syncs username change."""
    telegram_id = 123456789

    # First upsert with username
    user1 = await UserRepository.upsert(session, telegram_id=telegram_id, username="oldname")
    assert user1.username == "oldname"

    # Upsert with new username
    user2 = await UserRepository.upsert(session, telegram_id=telegram_id, username="newname")
    assert user2.username == "newname"


@pytest.mark.asyncio
async def test_upsert_handles_no_username(session: AsyncSession) -> None:
    """Test that upsert handles user with no username."""
    user = await UserRepository.upsert(
        session,
        telegram_id=123456789,
        username=None,
        first_name="NoUsername",
    )

    assert user.username is None
    assert user.first_name == "NoUsername"


@pytest.mark.asyncio
async def test_count_total(session: AsyncSession) -> None:
    """Test counting total users."""
    # Add 3 users
    for i in range(3):
        await UserRepository.upsert(session, telegram_id=100000 + i)

    count = await UserRepository.count_total(session)
    assert count == 3


@pytest.mark.asyncio
async def test_count_new_7_days(session: AsyncSession) -> None:
    """Test counting new users in last 7 days."""
    now = datetime.now(UTC)

    # Add user created now (should be counted)
    await UserRepository.upsert(session, telegram_id=123)

    # Simulate old user (8 days ago - should not be counted)
    old_user = User(
        telegram_id=456,
        created_at=now - timedelta(days=8),
        last_seen_at=now - timedelta(days=8),
    )
    session.add(old_user)
    await session.commit()

    count = await UserRepository.count_new_7_days(session)
    assert count == 1  # Only the new user


@pytest.mark.asyncio
async def test_count_active_7_days(session: AsyncSession) -> None:
    """Test counting active users in last 7 days."""
    now = datetime.now(UTC)

    # Add active user (last_seen_at now)
    await UserRepository.upsert(session, telegram_id=123)

    # Add old inactive user (last_seen 8 days ago)
    old_user = User(
        telegram_id=456,
        created_at=now - timedelta(days=30),
        last_seen_at=now - timedelta(days=8),
    )
    session.add(old_user)
    await session.commit()

    count = await UserRepository.count_active_7_days(session)
    assert count == 1  # Only the active user


@pytest.mark.asyncio
async def test_count_new_today_with_timezone(session: AsyncSession) -> None:
    """Test counting new users 'today' with timezone awareness."""
    import pytz

    # Get timezone
    tz = pytz.timezone("Europe/Belgrade")
    now_tz = datetime.now(tz)

    # Add user created now
    await UserRepository.upsert(session, telegram_id=123)

    count = await UserRepository.count_new_today(session, now_tz)
    assert count == 1


@pytest.mark.asyncio
async def test_get_by_telegram_id(session: AsyncSession) -> None:
    """Test retrieving user by telegram_id."""
    telegram_id = 123456789
    await UserRepository.upsert(session, telegram_id=telegram_id, username="testuser")

    user = await UserRepository.get_by_telegram_id(session, telegram_id)
    assert user is not None
    assert user.telegram_id == telegram_id
    assert user.username == "testuser"


@pytest.mark.asyncio
async def test_get_by_telegram_id_not_found(session: AsyncSession) -> None:
    """Test that get_by_telegram_id returns None for non-existent user."""
    user = await UserRepository.get_by_telegram_id(session, 999999999)
    assert user is None


@pytest.mark.asyncio
async def test_upsert_preserves_created_at(session: AsyncSession) -> None:
    """Test that created_at is not updated on upsert."""
    telegram_id = 123456789

    # First upsert
    user1 = await UserRepository.upsert(session, telegram_id=telegram_id)
    created_at_first = user1.created_at

    # Second upsert
    user2 = await UserRepository.upsert(session, telegram_id=telegram_id)
    created_at_second = user2.created_at

    # created_at should be identical
    assert created_at_first == created_at_second
