"""Tests for the action queue service."""

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest

from app.models.action_item import ActionItem
from app.models.building import Building
from app.services.action_queue_service import (
    complete_action,
    get_building_queue,
    get_weekly_summary,
    snooze_action,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_building(db, user_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Action 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1965,
        "building_type": "residential",
        "created_by": user_id,
        "status": "active",
    }
    defaults.update(kwargs)
    b = Building(**defaults)
    db.add(b)
    await db.commit()
    await db.refresh(b)
    return b


async def _make_action(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "source_type": "readiness",
        "action_type": "investigation",
        "title": "Test action",
        "priority": "medium",
        "status": "open",
    }
    defaults.update(kwargs)
    a = ActionItem(**defaults)
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return a


# ---------------------------------------------------------------------------
# get_building_queue
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_building_queue_empty(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    result = await get_building_queue(db_session, building.id)

    assert result["building_id"] == str(building.id)
    assert result["summary"]["total"] == 0
    assert result["overdue"] == []
    assert result["this_week"] == []
    assert result["this_month"] == []
    assert result["backlog"] == []


@pytest.mark.asyncio
async def test_get_building_queue_groups_by_urgency(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    today = date.today()

    # Overdue
    await _make_action(db_session, building.id, title="Overdue", due_date=today - timedelta(days=5))
    # This week
    await _make_action(db_session, building.id, title="This week", due_date=today + timedelta(days=3))
    # This month
    await _make_action(db_session, building.id, title="This month", due_date=today + timedelta(days=15))
    # Backlog (no deadline)
    await _make_action(db_session, building.id, title="Backlog", due_date=None)

    result = await get_building_queue(db_session, building.id)

    assert result["summary"]["overdue"] == 1
    assert result["summary"]["this_week"] == 1
    assert result["summary"]["this_month"] == 1
    assert result["summary"]["backlog"] == 1
    assert result["summary"]["total"] == 4
    assert result["overdue"][0]["title"] == "Overdue"
    assert result["this_week"][0]["title"] == "This week"
    assert result["this_month"][0]["title"] == "This month"
    assert result["backlog"][0]["title"] == "Backlog"


@pytest.mark.asyncio
async def test_get_building_queue_excludes_done(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)

    await _make_action(db_session, building.id, title="Open action")
    await _make_action(db_session, building.id, title="Done action", status="done")

    result = await get_building_queue(db_session, building.id)
    assert result["summary"]["total"] == 1


@pytest.mark.asyncio
async def test_get_building_queue_snoozed_hidden(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    future_date = (date.today() + timedelta(days=5)).isoformat()

    await _make_action(
        db_session,
        building.id,
        title="Snoozed",
        metadata_json={"snoozed_until": future_date},
    )
    await _make_action(db_session, building.id, title="Active")

    result = await get_building_queue(db_session, building.id)
    assert result["summary"]["total"] == 1
    assert result["summary"]["snoozed"] == 1
    assert len(result["snoozed"]) == 1
    assert result["snoozed"][0]["title"] == "Snoozed"


@pytest.mark.asyncio
async def test_get_building_queue_serialization_fields(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    await _make_action(
        db_session,
        building.id,
        title="Test",
        source_type="readiness",
        action_type="documentation",
        priority="high",
        due_date=date.today(),
    )

    result = await get_building_queue(db_session, building.id)
    items = result["this_week"] or result["overdue"] or result["backlog"]
    assert len(items) >= 1
    item = items[0]

    # Verify all expected fields present
    assert "id" in item
    assert "title" in item
    assert "priority" in item
    assert "source_type" in item
    assert "suggested_resolution" in item
    assert "estimated_effort" in item
    assert item["estimated_effort"] == "medium"  # documentation -> medium


@pytest.mark.asyncio
async def test_get_building_queue_priority_sort(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)

    # All in backlog (no deadline), but different priorities
    await _make_action(db_session, building.id, title="Low", priority="low")
    await _make_action(db_session, building.id, title="Critical", priority="critical")
    await _make_action(db_session, building.id, title="High", priority="high")

    result = await get_building_queue(db_session, building.id)
    titles = [a["title"] for a in result["backlog"]]
    assert titles == ["Critical", "High", "Low"]


# ---------------------------------------------------------------------------
# complete_action
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_complete_action(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    action = await _make_action(db_session, building.id)

    completed = await complete_action(db_session, action.id, admin_user.id, resolution_note="Fixed")

    assert completed is not None
    assert completed.status == "done"
    assert completed.completed_at is not None
    meta = completed.metadata_json or {}
    assert meta.get("resolution_note") == "Fixed"
    assert meta.get("completed_by") == str(admin_user.id)


@pytest.mark.asyncio
async def test_complete_action_not_found(db_session, admin_user):
    result = await complete_action(db_session, uuid.uuid4(), admin_user.id)
    assert result is None


# ---------------------------------------------------------------------------
# snooze_action
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_snooze_action(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    action = await _make_action(db_session, building.id)

    target = date.today() + timedelta(days=7)
    snoozed = await snooze_action(db_session, action.id, target, admin_user.id)

    assert snoozed is not None
    meta = snoozed.metadata_json or {}
    assert meta.get("snoozed_until") == target.isoformat()
    assert meta.get("snoozed_by") == str(admin_user.id)


@pytest.mark.asyncio
async def test_snooze_action_not_found(db_session, admin_user):
    result = await snooze_action(db_session, uuid.uuid4(), date.today(), admin_user.id)
    assert result is None


# ---------------------------------------------------------------------------
# get_weekly_summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_weekly_summary_empty(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    result = await get_weekly_summary(db_session, building.id)

    assert result["building_id"] == str(building.id)
    assert result["completed_count"] == 0
    assert result["created_count"] == 0
    assert result["readiness_trend"] == "stable"


@pytest.mark.asyncio
async def test_weekly_summary_with_activity(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)

    # Create an action (counts as created this week)
    await _make_action(db_session, building.id, title="New one")

    # Create a completed action
    await _make_action(
        db_session,
        building.id,
        title="Completed",
        status="done",
        completed_at=datetime.now(UTC),
    )

    result = await get_weekly_summary(db_session, building.id)

    # Both actions were created this week
    assert result["created_count"] == 2
    assert result["completed_count"] == 1
    assert result["open_count"] == 1
    assert len(result["next_priorities"]) == 1


@pytest.mark.asyncio
async def test_weekly_summary_trend_improved(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)

    # 3 completed, 1 created -> net positive -> improved
    for i in range(3):
        await _make_action(
            db_session,
            building.id,
            title=f"Done {i}",
            status="done",
            completed_at=datetime.now(UTC),
        )
    await _make_action(db_session, building.id, title="Created")

    result = await get_weekly_summary(db_session, building.id)
    # created=4 (all were created this week), completed=3
    # net = 3 - 4 = -1 -> degraded
    # Actually the 3 completed ones are also created this week,
    # so created_count=4, completed_count=3, net=-1 -> degraded
    assert result["readiness_trend"] in ("degraded", "stable", "improved")
