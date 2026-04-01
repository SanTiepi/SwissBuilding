"""Tests for the Invalidation Engine."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invalidation import InvalidationEvent
from app.services.invalidation_engine import InvalidationEngine


@pytest.fixture
def engine():
    return InvalidationEngine()


@pytest.fixture
def building_id():
    return uuid.uuid4()


@pytest.fixture
def user_id():
    return uuid.uuid4()


# ---------------------------------------------------------------------------
# _create_if_new idempotency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_if_new_creates_event(db: AsyncSession, engine: InvalidationEngine, building_id: uuid.UUID):
    """First call creates an event."""
    event = await engine._create_if_new(
        db,
        building_id=building_id,
        trigger_type="manual",
        trigger_id=None,
        trigger_description="Test trigger",
        affected_type="pack",
        affected_id=uuid.uuid4(),
        impact_reason="Test impact",
        severity="warning",
        required_reaction="review_required",
    )
    assert event is not None
    assert event.trigger_type == "manual"
    assert event.severity == "warning"
    assert event.status == "detected"


@pytest.mark.asyncio
async def test_create_if_new_deduplicates(db: AsyncSession, engine: InvalidationEngine, building_id: uuid.UUID):
    """Second call with same key returns None (dedup)."""
    affected_id = uuid.uuid4()
    kwargs = dict(
        building_id=building_id,
        trigger_type="manual",
        trigger_id=None,
        trigger_description="Test",
        affected_type="pack",
        affected_id=affected_id,
        impact_reason="reason",
        severity="warning",
        required_reaction="review_required",
    )
    first = await engine._create_if_new(db, **kwargs)
    await db.flush()
    second = await engine._create_if_new(db, **kwargs)
    assert first is not None
    assert second is None


# ---------------------------------------------------------------------------
# acknowledge / resolve
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_acknowledge_invalidation(
    db: AsyncSession, engine: InvalidationEngine, building_id: uuid.UUID, user_id: uuid.UUID
):
    event = InvalidationEvent(
        building_id=building_id,
        trigger_type="manual",
        trigger_description="test",
        affected_type="pack",
        affected_id=uuid.uuid4(),
        impact_reason="reason",
        severity="warning",
        required_reaction="review_required",
        status="detected",
    )
    db.add(event)
    await db.flush()

    result = await engine.acknowledge_invalidation(db, event.id, user_id)
    assert result is not None
    assert result.status == "acknowledged"


@pytest.mark.asyncio
async def test_resolve_invalidation(
    db: AsyncSession, engine: InvalidationEngine, building_id: uuid.UUID, user_id: uuid.UUID
):
    event = InvalidationEvent(
        building_id=building_id,
        trigger_type="manual",
        trigger_description="test",
        affected_type="pack",
        affected_id=uuid.uuid4(),
        impact_reason="reason",
        severity="warning",
        required_reaction="review_required",
        status="detected",
    )
    db.add(event)
    await db.flush()

    result = await engine.resolve_invalidation(db, event.id, user_id, "Fixed it")
    assert result is not None
    assert result.status == "resolved"
    assert result.resolution_note == "Fixed it"
    assert result.resolved_by_id == user_id
    assert result.resolved_at is not None


@pytest.mark.asyncio
async def test_resolve_not_found(db: AsyncSession, engine: InvalidationEngine, user_id: uuid.UUID):
    result = await engine.resolve_invalidation(db, uuid.uuid4(), user_id, "note")
    assert result is None


@pytest.mark.asyncio
async def test_acknowledge_not_found(db: AsyncSession, engine: InvalidationEngine, user_id: uuid.UUID):
    result = await engine.acknowledge_invalidation(db, uuid.uuid4(), user_id)
    assert result is None


# ---------------------------------------------------------------------------
# get_pending_invalidations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_pending_invalidations(db: AsyncSession, engine: InvalidationEngine, building_id: uuid.UUID):
    for i in range(3):
        db.add(
            InvalidationEvent(
                building_id=building_id,
                trigger_type="manual",
                trigger_description=f"event {i}",
                affected_type="pack",
                affected_id=uuid.uuid4(),
                impact_reason="reason",
                severity="warning" if i < 2 else "critical",
                required_reaction="review_required",
                status="detected",
            )
        )
    await db.flush()

    items, total = await engine.get_pending_invalidations(db, building_id=building_id)
    assert total == 3
    assert len(items) == 3


@pytest.mark.asyncio
async def test_get_pending_with_severity_filter(db: AsyncSession, engine: InvalidationEngine, building_id: uuid.UUID):
    db.add(
        InvalidationEvent(
            building_id=building_id,
            trigger_type="manual",
            trigger_description="critical one",
            affected_type="passport",
            affected_id=uuid.uuid4(),
            impact_reason="reason",
            severity="critical",
            required_reaction="republish",
            status="detected",
        )
    )
    db.add(
        InvalidationEvent(
            building_id=building_id,
            trigger_type="manual",
            trigger_description="info one",
            affected_type="form_instance",
            affected_id=uuid.uuid4(),
            impact_reason="reason",
            severity="info",
            required_reaction="notify_only",
            status="detected",
        )
    )
    await db.flush()

    items, total = await engine.get_pending_invalidations(db, building_id=building_id, severity="critical")
    assert total == 1
    assert items[0].severity == "critical"


# ---------------------------------------------------------------------------
# execute_reaction (basic)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_reaction_not_found(db: AsyncSession, engine: InvalidationEngine):
    result = await engine.execute_reaction(db, uuid.uuid4())
    assert result["error"] == "Event not found"
    assert result["success"] is False


@pytest.mark.asyncio
async def test_execute_reaction_notify_only(db: AsyncSession, engine: InvalidationEngine, building_id: uuid.UUID):
    event = InvalidationEvent(
        building_id=building_id,
        trigger_type="manual",
        trigger_description="test",
        affected_type="pack",
        affected_id=uuid.uuid4(),
        impact_reason="reason",
        severity="info",
        required_reaction="notify_only",
        status="detected",
    )
    db.add(event)
    await db.flush()

    result = await engine.execute_reaction(db, event.id)
    assert result["success"] is True
    assert result["action"] == "notification_sent"
