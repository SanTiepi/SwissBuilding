"""Tests for the Activity Ledger Service — hash chain and CRUD."""

import uuid

import pytest

from app.models.building import Building
from app.services.activity_ledger_service import (
    get_building_ledger,
    record_activity,
    verify_chain_integrity,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_building(db_session, *, created_by=None):
    b = Building(
        id=uuid.uuid4(),
        address="Rue du Ledger 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=created_by,
        status="active",
    )
    db_session.add(b)
    return b


async def _record(db, building_id, actor_id, *, activity_type="diagnostic_submitted", n=1):
    """Helper to record activity(ies)."""
    entity_id = uuid.uuid4()
    result = None
    for i in range(n):
        result = await record_activity(
            db,
            building_id=building_id,
            actor_id=actor_id,
            actor_role="admin",
            actor_name="Test User",
            activity_type=activity_type,
            entity_type="diagnostic",
            entity_id=entity_id,
            title=f"Test activity {i}",
        )
    return result


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_activity_creates_entry_with_hash(db_session, admin_user):
    """A single recorded activity has a valid hash and no previous_hash."""
    building = _make_building(db_session, created_by=admin_user.id)
    await db_session.commit()

    activity = await record_activity(
        db_session,
        building_id=building.id,
        actor_id=admin_user.id,
        actor_role="admin",
        actor_name="Admin",
        activity_type="diagnostic_submitted",
        entity_type="diagnostic",
        entity_id=uuid.uuid4(),
        title="First diagnostic submitted",
        description="Full survey",
        reason="Annual check",
        metadata={"pollutant": "asbestos"},
    )
    await db_session.commit()

    assert activity.id is not None
    assert activity.activity_hash is not None
    assert len(activity.activity_hash) == 64
    assert activity.previous_hash is None
    assert activity.actor_role == "admin"
    assert activity.metadata_json == {"pollutant": "asbestos"}


@pytest.mark.asyncio
async def test_hash_chain_3_entries(db_session, admin_user):
    """Record 3 activities and verify the chain links correctly."""
    building = _make_building(db_session, created_by=admin_user.id)
    await db_session.commit()

    a1 = await record_activity(
        db_session,
        building_id=building.id,
        actor_id=admin_user.id,
        actor_role="admin",
        actor_name="Admin",
        activity_type="diagnostic_submitted",
        entity_type="diagnostic",
        entity_id=uuid.uuid4(),
        title="Activity 1",
    )
    await db_session.flush()

    a2 = await record_activity(
        db_session,
        building_id=building.id,
        actor_id=admin_user.id,
        actor_role="admin",
        actor_name="Admin",
        activity_type="document_uploaded",
        entity_type="document",
        entity_id=uuid.uuid4(),
        title="Activity 2",
    )
    await db_session.flush()

    a3 = await record_activity(
        db_session,
        building_id=building.id,
        actor_id=admin_user.id,
        actor_role="admin",
        actor_name="Admin",
        activity_type="action_completed",
        entity_type="action",
        entity_id=uuid.uuid4(),
        title="Activity 3",
    )
    await db_session.commit()

    # Chain linkage
    assert a1.previous_hash is None
    assert a2.previous_hash == a1.activity_hash
    assert a3.previous_hash == a2.activity_hash

    # Full chain verification
    result = await verify_chain_integrity(db_session, building.id)
    assert result["valid"] is True
    assert result["total_entries"] == 3
    assert result["first_break_at"] is None


@pytest.mark.asyncio
async def test_tamper_detection(db_session, admin_user):
    """Modifying a hash should make verify_chain_integrity detect the break."""
    building = _make_building(db_session, created_by=admin_user.id)
    await db_session.commit()

    await _record(db_session, building.id, admin_user.id, n=3)
    await db_session.commit()

    # Tamper with the second entry's hash
    items, _ = await get_building_ledger(db_session, building.id, size=50)
    # Items are newest-first; reverse to get chronological
    chronological = list(reversed(items))
    chronological[1].activity_hash = "tampered_hash_value_000000000000000000000000000000000000"
    await db_session.commit()

    result = await verify_chain_integrity(db_session, building.id)
    assert result["valid"] is False
    assert result["first_break_at"] is not None


@pytest.mark.asyncio
async def test_pagination(db_session, admin_user):
    """Pagination returns correct subsets and total count."""
    building = _make_building(db_session, created_by=admin_user.id)
    await db_session.commit()

    for i in range(5):
        await record_activity(
            db_session,
            building_id=building.id,
            actor_id=admin_user.id,
            actor_role="admin",
            actor_name="Admin",
            activity_type="note_added",
            entity_type="building",
            entity_id=building.id,
            title=f"Note {i}",
        )
        await db_session.flush()
    await db_session.commit()

    page1, total = await get_building_ledger(db_session, building.id, page=1, size=2)
    assert total == 5
    assert len(page1) == 2

    page3, _ = await get_building_ledger(db_session, building.id, page=3, size=2)
    assert len(page3) == 1


@pytest.mark.asyncio
async def test_filter_by_activity_type(db_session, admin_user):
    """Filtering by activity_type returns only matching entries."""
    building = _make_building(db_session, created_by=admin_user.id)
    await db_session.commit()

    await _record(db_session, building.id, admin_user.id, activity_type="diagnostic_submitted", n=2)
    await _record(db_session, building.id, admin_user.id, activity_type="document_uploaded", n=3)
    await db_session.commit()

    items, total = await get_building_ledger(db_session, building.id, activity_type="document_uploaded")
    assert total == 3
    assert all(a.activity_type == "document_uploaded" for a in items)


@pytest.mark.asyncio
async def test_ledger_order_newest_first(db_session, admin_user):
    """get_building_ledger returns newest entries first."""
    building = _make_building(db_session, created_by=admin_user.id)
    await db_session.commit()

    for i in range(3):
        await record_activity(
            db_session,
            building_id=building.id,
            actor_id=admin_user.id,
            actor_role="admin",
            actor_name="Admin",
            activity_type="note_added",
            entity_type="building",
            entity_id=building.id,
            title=f"Note {i}",
        )
        await db_session.flush()
    await db_session.commit()

    items, _ = await get_building_ledger(db_session, building.id)
    assert items[0].title == "Note 2"
    assert items[-1].title == "Note 0"


@pytest.mark.asyncio
async def test_empty_building_verify(db_session, admin_user):
    """Verifying an empty building returns valid with 0 entries."""
    building = _make_building(db_session, created_by=admin_user.id)
    await db_session.commit()

    result = await verify_chain_integrity(db_session, building.id)
    assert result == {"valid": True, "total_entries": 0, "first_break_at": None}
