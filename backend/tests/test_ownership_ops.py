"""BatiConnect — Ownership Ops tests (service-layer + route-level)."""

import uuid
from datetime import date

import pytest

from app.api.ownership import router as ownership_router
from app.main import app
from app.services.ownership_service import (
    create_ownership_record,
    get_ownership_summary,
    list_ownership_records,
    update_ownership_record,
)

# Register ownership router for HTTP tests
app.include_router(ownership_router, prefix="/api/v1")


# ---- Service-layer tests ----


@pytest.mark.asyncio
async def test_create_ownership_service(db_session, sample_building, admin_user):
    data = {
        "owner_type": "contact",
        "owner_id": uuid.uuid4(),
        "ownership_type": "full",
        "share_pct": 100.0,
        "acquisition_type": "purchase",
        "acquisition_date": date(2020, 6, 1),
        "status": "active",
    }
    record = await create_ownership_record(db_session, sample_building.id, data, created_by=admin_user.id)
    assert record.id is not None
    assert record.share_pct == 100.0
    assert record.ownership_type == "full"


@pytest.mark.asyncio
async def test_list_ownership_service(db_session, sample_building):
    for _i in range(3):
        await create_ownership_record(
            db_session,
            sample_building.id,
            {
                "owner_type": "contact",
                "owner_id": uuid.uuid4(),
                "ownership_type": "co_ownership",
                "share_pct": 33.33,
                "status": "active",
            },
        )
    _items, total = await list_ownership_records(db_session, sample_building.id)
    assert total == 3


@pytest.mark.asyncio
async def test_update_ownership_service(db_session, sample_building):
    record = await create_ownership_record(
        db_session,
        sample_building.id,
        {
            "owner_type": "contact",
            "owner_id": uuid.uuid4(),
            "ownership_type": "full",
            "share_pct": 100.0,
            "status": "active",
        },
    )
    updated = await update_ownership_record(db_session, record, {"status": "transferred", "share_pct": 0.0})
    assert updated.status == "transferred"
    assert updated.share_pct == 0.0


@pytest.mark.asyncio
async def test_get_ownership_summary_service(db_session, sample_building):
    owner1 = uuid.uuid4()
    owner2 = uuid.uuid4()
    for owner_id, share, st in [(owner1, 50.0, "active"), (owner2, 50.0, "active"), (uuid.uuid4(), 100.0, "archived")]:
        await create_ownership_record(
            db_session,
            sample_building.id,
            {
                "owner_type": "contact",
                "owner_id": owner_id,
                "ownership_type": "co_ownership",
                "share_pct": share,
                "status": st,
            },
        )
    summary = await get_ownership_summary(db_session, sample_building.id)
    assert summary["total_records"] == 3
    assert summary["active_records"] == 2
    assert summary["total_share_pct"] == 100.0
    assert summary["owner_count"] == 2
    assert summary["co_ownership"] is True


# ---- Route-level tests ----


@pytest.mark.asyncio
async def test_api_list_ownership(client, auth_headers, db_session, sample_building, admin_user):
    for _i in range(2):
        await create_ownership_record(
            db_session,
            sample_building.id,
            {
                "owner_type": "contact",
                "owner_id": uuid.uuid4(),
                "ownership_type": "full",
                "share_pct": 50.0,
                "status": "active",
            },
            created_by=admin_user.id,
        )
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/ownership", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert body["page"] == 1
    assert body["pages"] == 1
    assert len(body["items"]) == 2
    assert "size" in body


@pytest.mark.asyncio
async def test_api_list_ownership_pagination(client, auth_headers, db_session, sample_building, admin_user):
    for _i in range(5):
        await create_ownership_record(
            db_session,
            sample_building.id,
            {
                "owner_type": "contact",
                "owner_id": uuid.uuid4(),
                "ownership_type": "co_ownership",
                "share_pct": 20.0,
                "status": "active",
            },
            created_by=admin_user.id,
        )
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/ownership?page=1&size=2", headers=auth_headers)
    body = resp.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2
    assert body["pages"] == 3


@pytest.mark.asyncio
async def test_api_list_ownership_filter_status(client, auth_headers, db_session, sample_building, admin_user):
    await create_ownership_record(
        db_session,
        sample_building.id,
        {
            "owner_type": "contact",
            "owner_id": uuid.uuid4(),
            "ownership_type": "full",
            "share_pct": 100.0,
            "status": "active",
        },
        created_by=admin_user.id,
    )
    await create_ownership_record(
        db_session,
        sample_building.id,
        {
            "owner_type": "contact",
            "owner_id": uuid.uuid4(),
            "ownership_type": "full",
            "share_pct": 100.0,
            "status": "transferred",
        },
        created_by=admin_user.id,
    )
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/ownership?status=active", headers=auth_headers)
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["status"] == "active"


@pytest.mark.asyncio
async def test_api_create_ownership(client, auth_headers, sample_building):
    payload = {
        "owner_type": "contact",
        "owner_id": str(uuid.uuid4()),
        "ownership_type": "full",
        "share_pct": 100.0,
        "acquisition_type": "purchase",
        "acquisition_date": "2020-06-01",
        "status": "active",
    }
    resp = await client.post(f"/api/v1/buildings/{sample_building.id}/ownership", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["ownership_type"] == "full"
    assert body["share_pct"] == 100.0
    assert body["id"] is not None
    assert "owner_display_name" in body


@pytest.mark.asyncio
async def test_api_get_ownership(client, auth_headers, db_session, sample_building, admin_user):
    record = await create_ownership_record(
        db_session,
        sample_building.id,
        {
            "owner_type": "contact",
            "owner_id": uuid.uuid4(),
            "ownership_type": "usufruct",
            "share_pct": 100.0,
            "status": "active",
        },
        created_by=admin_user.id,
    )
    await db_session.commit()

    resp = await client.get(f"/api/v1/ownership/{record.id}", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["ownership_type"] == "usufruct"


@pytest.mark.asyncio
async def test_api_update_ownership(client, auth_headers, db_session, sample_building, admin_user):
    record = await create_ownership_record(
        db_session,
        sample_building.id,
        {
            "owner_type": "contact",
            "owner_id": uuid.uuid4(),
            "ownership_type": "full",
            "share_pct": 100.0,
            "status": "active",
        },
        created_by=admin_user.id,
    )
    await db_session.commit()

    resp = await client.put(
        f"/api/v1/ownership/{record.id}",
        json={"status": "transferred", "share_pct": 0.0},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "transferred"
    assert body["share_pct"] == 0.0


@pytest.mark.asyncio
async def test_api_ownership_summary(client, auth_headers, db_session, sample_building, admin_user):
    owner1 = uuid.uuid4()
    owner2 = uuid.uuid4()
    for owner_id, share, st in [(owner1, 60.0, "active"), (owner2, 40.0, "active"), (uuid.uuid4(), 100.0, "archived")]:
        await create_ownership_record(
            db_session,
            sample_building.id,
            {
                "owner_type": "contact",
                "owner_id": owner_id,
                "ownership_type": "co_ownership",
                "share_pct": share,
                "status": st,
            },
            created_by=admin_user.id,
        )
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/ownership-summary", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_records"] == 3
    assert body["active_records"] == 2
    assert body["total_share_pct"] == 100.0
    assert body["owner_count"] == 2
    assert body["co_ownership"] is True


@pytest.mark.asyncio
async def test_api_ownership_building_not_found(client, auth_headers):
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/buildings/{fake_id}/ownership", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_ownership_not_found(client, auth_headers):
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/ownership/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_ownership_rbac_diagnostician_read_only(
    client, diag_headers, db_session, sample_building, admin_user
):
    record = await create_ownership_record(
        db_session,
        sample_building.id,
        {
            "owner_type": "contact",
            "owner_id": uuid.uuid4(),
            "ownership_type": "full",
            "share_pct": 100.0,
            "status": "active",
        },
        created_by=admin_user.id,
    )
    await db_session.commit()

    # Can list
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/ownership", headers=diag_headers)
    assert resp.status_code == 200

    # Can read
    resp = await client.get(f"/api/v1/ownership/{record.id}", headers=diag_headers)
    assert resp.status_code == 200

    # Cannot create
    resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/ownership",
        json={
            "owner_type": "contact",
            "owner_id": str(uuid.uuid4()),
            "ownership_type": "full",
            "share_pct": 100.0,
        },
        headers=diag_headers,
    )
    assert resp.status_code == 403

    # Cannot update
    resp = await client.put(f"/api/v1/ownership/{record.id}", json={"status": "transferred"}, headers=diag_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_api_ownership_unauthorized(client):
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/buildings/{fake_id}/ownership")
    assert resp.status_code in (401, 403)
