"""Tests for feedback database operations."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from hub_bot.db.models import Base, Feedback, User
from hub_bot.db.repository import FeedbackRepository, UserRepository


@pytest.fixture
async def async_session() -> AsyncSession:
    """Create in-memory SQLite session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_feedback_create_for_existing_user(async_session: AsyncSession) -> None:
    """Test that feedback is created for an existing user."""
    # Create user first
    user = await UserRepository.upsert(
        async_session,
        telegram_id=123456789,
        username="testuser",
        first_name="Test",
    )

    # Create feedback
    feedback = await FeedbackRepository.create(
        async_session,
        telegram_id=user.telegram_id,
        app_id="postbox",
        message="This is test feedback",
    )

    assert feedback.id is not None
    assert feedback.telegram_id == 123456789
    assert feedback.app_id == "postbox"
    assert feedback.message == "This is test feedback"
    assert feedback.status == "new"


@pytest.mark.asyncio
async def test_feedback_saves_correct_fields(async_session: AsyncSession) -> None:
    """Test that all fields are saved correctly."""
    await UserRepository.upsert(async_session, telegram_id=111, username="user1")

    feedback = await FeedbackRepository.create(
        async_session,
        telegram_id=111,
        app_id="postbox",
        message="Test message",
    )

    # Verify all fields
    assert feedback.telegram_id == 111
    assert feedback.app_id == "postbox"
    assert feedback.message == "Test message"
    assert feedback.status == "new"
    assert isinstance(feedback.created_at, datetime)
    assert feedback.created_at.tzinfo is not None  # UTC timezone aware


@pytest.mark.asyncio
async def test_feedback_strips_whitespace(async_session: AsyncSession) -> None:
    """Test that message whitespace is stripped."""
    await UserRepository.upsert(async_session, telegram_id=222)

    feedback = await FeedbackRepository.create(
        async_session,
        telegram_id=222,
        app_id="postbox",
        message="  test message with spaces  ",
    )

    assert feedback.message == "test message with spaces"


@pytest.mark.asyncio
async def test_feedback_invalid_app_id_raises_error(async_session: AsyncSession) -> None:
    """Test that invalid app_id raises ValueError."""
    await UserRepository.upsert(async_session, telegram_id=333)

    with pytest.raises(ValueError, match="Invalid app_id"):
        await FeedbackRepository.create(
            async_session,
            telegram_id=333,
            app_id="nonexistent_app",
            message="message",
        )


@pytest.mark.asyncio
async def test_feedback_one_submit_creates_one_record(async_session: AsyncSession) -> None:
    """Test that one submit creates exactly one feedback record."""
    await UserRepository.upsert(async_session, telegram_id=444)

    await FeedbackRepository.create(
        async_session,
        telegram_id=444,
        app_id="postbox",
        message="single message",
    )

    # Query to verify only one record
    stmt = select(Feedback).where(Feedback.telegram_id == 444)
    result = await async_session.execute(stmt)
    records = result.scalars().all()

    assert len(records) == 1


@pytest.mark.asyncio
async def test_feedback_fk_constraint_nonexistent_user(async_session: AsyncSession) -> None:
    """Test that FK constraint prevents feedback for nonexistent user."""
    # Enable FK constraints (SQLite specific)
    conn = await async_session.connection()
    await conn.exec_driver_sql("PRAGMA foreign_keys=ON")

    with pytest.raises(IntegrityError):
        await FeedbackRepository.create(
            async_session,
            telegram_id=999999999,  # Nonexistent user
            app_id="postbox",
            message="this should fail",
        )

    # Verify no record was created
    stmt = select(Feedback).where(Feedback.telegram_id == 999999999)
    result = await async_session.execute(stmt)
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_feedback_status_defaults_to_new(async_session: AsyncSession) -> None:
    """Test that status defaults to 'new'."""
    await UserRepository.upsert(async_session, telegram_id=555)

    feedback = await FeedbackRepository.create(
        async_session,
        telegram_id=555,
        app_id="postbox",
        message="test",
    )

    assert feedback.status == "new"


@pytest.mark.asyncio
async def test_feedback_created_at_is_utc(async_session: AsyncSession) -> None:
    """Test that created_at is UTC timezone aware."""
    await UserRepository.upsert(async_session, telegram_id=666)

    before = datetime.now(UTC)
    feedback = await FeedbackRepository.create(
        async_session,
        telegram_id=666,
        app_id="postbox",
        message="test",
    )
    after = datetime.now(UTC)

    assert feedback.created_at.tzinfo is not None
    assert before <= feedback.created_at <= after


@pytest.mark.asyncio
async def test_feedback_multiple_messages_same_app(async_session: AsyncSession) -> None:
    """Test that multiple feedback messages can be created for same app."""
    await UserRepository.upsert(async_session, telegram_id=777)

    feedback1 = await FeedbackRepository.create(
        async_session,
        telegram_id=777,
        app_id="postbox",
        message="first feedback",
    )
    feedback2 = await FeedbackRepository.create(
        async_session,
        telegram_id=777,
        app_id="postbox",
        message="second feedback",
    )

    assert feedback1.app_id == "postbox"
    assert feedback2.app_id == "postbox"
    assert feedback1.id != feedback2.id
    assert feedback1.message == "first feedback"
    assert feedback2.message == "second feedback"


@pytest.mark.asyncio
async def test_feedback_multiple_users(async_session: AsyncSession) -> None:
    """Test that feedback is correctly attributed to different users."""
    await UserRepository.upsert(async_session, telegram_id=888, username="user1")
    await UserRepository.upsert(async_session, telegram_id=889, username="user2")

    feedback1 = await FeedbackRepository.create(
        async_session,
        telegram_id=888,
        app_id="postbox",
        message="user1 feedback",
    )
    feedback2 = await FeedbackRepository.create(
        async_session,
        telegram_id=889,
        app_id="postbox",
        message="user2 feedback",
    )

    assert feedback1.telegram_id == 888
    assert feedback2.telegram_id == 889
