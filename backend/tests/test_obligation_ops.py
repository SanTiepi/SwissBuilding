"""BatiConnect — Obligation Ops tests (service-layer + route-level)."""

import uuid
from datetime import date, timedelta

import pytest

from app.api.obligations import router as obligations_router
from app.main import app
from app.services.obligation_service import (
    _calculate_status,
    cancel_obligation,
    complete_obligation,
    create_obligation,
    get_due_soon,
    get_overdue,
    list_obligations,
    refresh_statuses,
    update_obligation,
)

# Register obligations router for HTTP tests (not yet in router.py hub file)
app.include_router(obligations_router, prefix="/api/v1")


# ---- Unit: _calculate_status ----


def test_calculate_status_upcoming():
    future = date.today() + timedelta(days=60)
    assert _calculate_status(future, None, 30) == "upcoming"


def test_calculate_status_due_soon():
    soon = date.today() + timedelta(days=10)
    assert _calculate_status(soon, None, 30) == "due_soon"


def test_calculate_status_overdue():
    past = date.today() - timedelta(days=5)
    assert _calculate_status(past, None, 30) == "overdue"


def test_calculate_status_completed():
    from datetime import datetime

    assert _calculate_status(date.today(), datetime.utcnow(), 30) == "completed"


# ---- Service-layer tests ----


@pytest.mark.asyncio
async def test_create_obligation(db_session, sample_building):
    data = {
        "title": "Annual amiante inspection",
        "obligation_type": "regulatory_inspection",
        "due_date": date.today() + timedelta(days=90),
        "priority": "high",
    }
    obl = await create_obligation(db_session, sample_building.id, data)
    assert obl.id is not None
    assert obl.status == "upcoming"
    assert obl.obligation_type == "regulatory_inspection"


@pytest.mark.asyncio
async def test_create_obligation_due_soon(db_session, sample_building):
    data = {
        "title": "Renew insurance",
        "obligation_type": "insurance_renewal",
        "due_date": date.today() + timedelta(days=10),
        "priority": "medium",
    }
    obl = await create_obligation(db_session, sample_building.id, data)
    assert obl.status == "due_soon"


@pytest.mark.asyncio
async def test_list_obligations_filtered(db_session, sample_building):
    for i, (otype, prio) in enumerate(
        [("maintenance", "low"), ("regulatory_inspection", "high"), ("maintenance", "medium")]
    ):
        await create_obligation(
            db_session,
            sample_building.id,
            {
                "title": f"Obligation {i}",
                "obligation_type": otype,
                "due_date": date.today() + timedelta(days=30 + i),
                "priority": prio,
            },
        )
    all_obls = await list_obligations(db_session, sample_building.id)
    assert len(all_obls) == 3

    maint_only = await list_obligations(db_session, sample_building.id, obligation_type="maintenance")
    assert len(maint_only) == 2


@pytest.mark.asyncio
async def test_get_due_soon(db_session, sample_building):
    # One due in 10 days, one in 60 days
    await create_obligation(
        db_session,
        sample_building.id,
        {
            "title": "Soon",
            "obligation_type": "custom",
            "due_date": date.today() + timedelta(days=10),
            "priority": "medium",
        },
    )
    await create_obligation(
        db_session,
        sample_building.id,
        {
            "title": "Later",
            "obligation_type": "custom",
            "due_date": date.today() + timedelta(days=60),
            "priority": "low",
        },
    )
    soon = await get_due_soon(db_session, sample_building.id, days=30)
    assert len(soon) == 1
    assert soon[0].title == "Soon"


@pytest.mark.asyncio
async def test_get_overdue(db_session, sample_building):
    obl = await create_obligation(
        db_session,
        sample_building.id,
        {
            "title": "Past due",
            "obligation_type": "maintenance",
            "due_date": date.today() - timedelta(days=5),
            "priority": "high",
        },
    )
    assert obl.status == "overdue"
    overdue = await get_overdue(db_session, sample_building.id)
    assert len(overdue) == 1


@pytest.mark.asyncio
async def test_complete_obligation_onetime(db_session, sample_building, admin_user):
    obl = await create_obligation(
        db_session,
        sample_building.id,
        {
            "title": "One-time task",
            "obligation_type": "custom",
            "due_date": date.today() + timedelta(days=5),
            "priority": "medium",
        },
    )
    completed, next_obl = await complete_obligation(db_session, obl, admin_user.id, notes="Done")
    assert completed.status == "completed"
    assert completed.completed_at is not None
    assert completed.completed_by_user_id == admin_user.id
    assert next_obl is None


@pytest.mark.asyncio
async def test_complete_obligation_recurring(db_session, sample_building, admin_user):
    obl = await create_obligation(
        db_session,
        sample_building.id,
        {
            "title": "Quarterly check",
            "obligation_type": "maintenance",
            "due_date": date.today() + timedelta(days=5),
            "recurrence": "quarterly",
            "priority": "medium",
        },
    )
    completed, next_obl = await complete_obligation(db_session, obl, admin_user.id)
    assert completed.status == "completed"
    assert next_obl is not None
    assert next_obl.title == "Quarterly check"
    assert next_obl.due_date == obl.due_date + timedelta(days=91)
    assert next_obl.recurrence == "quarterly"
    assert next_obl.status in ("upcoming", "due_soon")


@pytest.mark.asyncio
async def test_cancel_obligation(db_session, sample_building):
    obl = await create_obligation(
        db_session,
        sample_building.id,
        {
            "title": "Cancel me",
            "obligation_type": "custom",
            "due_date": date.today() + timedelta(days=30),
            "priority": "low",
        },
    )
    cancelled = await cancel_obligation(db_session, obl)
    assert cancelled.status == "cancelled"


@pytest.mark.asyncio
async def test_update_obligation(db_session, sample_building):
    obl = await create_obligation(
        db_session,
        sample_building.id,
        {
            "title": "Update me",
            "obligation_type": "custom",
            "due_date": date.today() + timedelta(days=60),
            "priority": "low",
        },
    )
    updated = await update_obligation(db_session, obl, {"priority": "critical", "title": "Updated"})
    assert updated.priority == "critical"
    assert updated.title == "Updated"


@pytest.mark.asyncio
async def test_refresh_statuses(db_session, sample_building):
    # Create an obligation with a past due_date but force status to upcoming
    await create_obligation(
        db_session,
        sample_building.id,
        {
            "title": "Stale status",
            "obligation_type": "custom",
            "due_date": date.today() - timedelta(days=1),
            "priority": "medium",
        },
    )
    # It should already be overdue, but let's test refresh
    count = await refresh_statuses(db_session, sample_building.id)
    # No change expected since create already sets correct status
    assert count == 0


# ---- Route-level tests ----


@pytest.mark.asyncio
async def test_api_list_obligations(client, auth_headers, db_session, sample_building):
    await create_obligation(
        db_session,
        sample_building.id,
        {
            "title": "API list test",
            "obligation_type": "maintenance",
            "due_date": date.today() + timedelta(days=30),
            "priority": "medium",
        },
    )
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/obligations", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["title"] == "API list test"


@pytest.mark.asyncio
async def test_api_create_obligation(client, auth_headers, sample_building):
    payload = {
        "title": "New obligation",
        "obligation_type": "insurance_renewal",
        "due_date": str(date.today() + timedelta(days=45)),
        "priority": "high",
        "recurrence": "annual",
    }
    resp = await client.post(f"/api/v1/buildings/{sample_building.id}/obligations", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "New obligation"
    assert body["status"] == "upcoming"
    assert body["recurrence"] == "annual"


@pytest.mark.asyncio
async def test_api_update_obligation(client, auth_headers, db_session, sample_building):
    obl = await create_obligation(
        db_session,
        sample_building.id,
        {
            "title": "To update",
            "obligation_type": "custom",
            "due_date": date.today() + timedelta(days=60),
            "priority": "low",
        },
    )
    await db_session.commit()

    resp = await client.put(f"/api/v1/obligations/{obl.id}", json={"priority": "high"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["priority"] == "high"


@pytest.mark.asyncio
async def test_api_complete_obligation(client, auth_headers, db_session, sample_building):
    obl = await create_obligation(
        db_session,
        sample_building.id,
        {
            "title": "To complete",
            "obligation_type": "maintenance",
            "due_date": date.today() + timedelta(days=5),
            "priority": "medium",
        },
    )
    await db_session.commit()

    resp = await client.post(f"/api/v1/obligations/{obl.id}/complete", json={"notes": "All done"}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    assert body["completed_at"] is not None


@pytest.mark.asyncio
async def test_api_delete_obligation(client, auth_headers, db_session, sample_building):
    obl = await create_obligation(
        db_session,
        sample_building.id,
        {
            "title": "To cancel",
            "obligation_type": "custom",
            "due_date": date.today() + timedelta(days=30),
            "priority": "low",
        },
    )
    await db_session.commit()

    resp = await client.delete(f"/api/v1/obligations/{obl.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_api_obligation_not_found(client, auth_headers):
    resp = await client.put(f"/api/v1/obligations/{uuid.uuid4()}", json={"title": "x"}, headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_obligation_building_not_found(client, auth_headers):
    resp = await client.get(f"/api/v1/buildings/{uuid.uuid4()}/obligations", headers=auth_headers)
    assert resp.status_code == 404
