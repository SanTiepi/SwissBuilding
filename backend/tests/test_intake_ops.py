"""BatiConnect — Intake Request tests (service-layer + route-level)."""

import uuid

import pytest

from app.api.intake import router as intake_router
from app.main import app
from app.services.intake_service import (
    convert_request,
    get_request,
    list_requests,
    qualify_request,
    reject_request,
    submit_request,
)

# Register intake router for HTTP tests (not yet in router.py hub file)
app.include_router(intake_router, prefix="/api/v1")


# ---- Helpers ----


def _intake_data(**overrides) -> dict:
    base = {
        "requester_name": "Alice Test",
        "requester_email": "alice@example.ch",
        "building_address": "Rue du Lac 10, 1000 Lausanne",
        "request_type": "asbestos_diagnostic",
        "urgency": "standard",
        "source": "website",
    }
    base.update(overrides)
    return base


# ---- Service-layer tests ----


@pytest.mark.asyncio
async def test_submit_request_service(db_session):
    intake = await submit_request(db_session, _intake_data())
    assert intake.id is not None
    assert intake.status == "new"
    assert intake.requester_name == "Alice Test"
    assert intake.requester_email == "alice@example.ch"


@pytest.mark.asyncio
async def test_list_requests_service(db_session):
    for i in range(3):
        await submit_request(db_session, _intake_data(requester_email=f"list{i}@example.ch"))
    items, total = await list_requests(db_session)
    assert total == 3
    assert len(items) == 3


@pytest.mark.asyncio
async def test_list_requests_filter_status(db_session, admin_user):
    r1 = await submit_request(db_session, _intake_data(requester_email="f1@example.ch"))
    await submit_request(db_session, _intake_data(requester_email="f2@example.ch"))
    await qualify_request(db_session, r1, admin_user.id, notes="ok")

    items, total = await list_requests(db_session, status="qualified")
    assert total == 1
    assert items[0].status == "qualified"


@pytest.mark.asyncio
async def test_get_request_service(db_session):
    intake = await submit_request(db_session, _intake_data())
    found = await get_request(db_session, intake.id)
    assert found is not None
    assert found.id == intake.id


@pytest.mark.asyncio
async def test_get_request_not_found(db_session):
    found = await get_request(db_session, uuid.uuid4())
    assert found is None


@pytest.mark.asyncio
async def test_qualify_request_service(db_session, admin_user):
    intake = await submit_request(db_session, _intake_data())
    qualified = await qualify_request(db_session, intake, admin_user.id, notes="Looks good")
    assert qualified.status == "qualified"
    assert qualified.qualified_by_user_id == admin_user.id
    assert qualified.qualified_at is not None
    assert qualified.notes == "Looks good"


@pytest.mark.asyncio
async def test_reject_request_service(db_session, admin_user):
    intake = await submit_request(db_session, _intake_data())
    rejected = await reject_request(db_session, intake, admin_user.id, reason="Spam")
    assert rejected.status == "rejected"
    assert rejected.notes == "Spam"


@pytest.mark.asyncio
async def test_convert_request_service(db_session, admin_user):
    intake = await submit_request(
        db_session,
        _intake_data(
            building_city="Lausanne",
            building_postal_code="1000",
            requester_phone="+41 79 000 00 00",
            requester_company="Test SA",
        ),
    )
    converted = await convert_request(db_session, intake, admin_user.id)
    assert converted.status == "converted"
    assert converted.converted_contact_id is not None
    assert converted.converted_building_id is not None


@pytest.mark.asyncio
async def test_convert_request_creates_contact_and_building(db_session, admin_user):
    from app.models.building import Building
    from app.models.contact import Contact

    intake = await submit_request(
        db_session,
        _intake_data(building_city="Geneva", building_postal_code="1201", building_egid="12345"),
    )
    converted = await convert_request(db_session, intake, admin_user.id)

    # Check contact was created
    from sqlalchemy import select

    contact = (
        await db_session.execute(select(Contact).where(Contact.id == converted.converted_contact_id))
    ).scalar_one()
    assert contact.name == "Alice Test"
    assert contact.email == "alice@example.ch"
    assert contact.source_ref == f"intake:{intake.id}"

    # Check building was created
    building = (
        await db_session.execute(select(Building).where(Building.id == converted.converted_building_id))
    ).scalar_one()
    assert building.address == "Rue du Lac 10, 1000 Lausanne"
    assert building.city == "Geneva"
    assert building.egid == 12345


# ---- Route-level tests ----


@pytest.mark.asyncio
async def test_api_public_submit_intake(client):
    """Public endpoint — no auth headers needed."""
    payload = _intake_data(description="Urgent asbestos check")
    resp = await client.post("/api/v1/public/intake", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "new"
    assert body["requester_name"] == "Alice Test"
    assert body["request_type"] == "asbestos_diagnostic"
    assert body["id"] is not None


@pytest.mark.asyncio
async def test_api_list_intake_requests(client, auth_headers, db_session):
    # Seed 2 intakes
    await submit_request(db_session, _intake_data(requester_email="api1@example.ch"))
    await submit_request(db_session, _intake_data(requester_email="api2@example.ch"))
    await db_session.commit()

    resp = await client.get("/api/v1/intake-requests", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


@pytest.mark.asyncio
async def test_api_get_intake_request(client, auth_headers, db_session):
    intake = await submit_request(db_session, _intake_data())
    await db_session.commit()

    resp = await client.get(f"/api/v1/intake-requests/{intake.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["requester_name"] == "Alice Test"


@pytest.mark.asyncio
async def test_api_qualify_intake(client, auth_headers, db_session):
    intake = await submit_request(db_session, _intake_data())
    await db_session.commit()

    resp = await client.post(
        f"/api/v1/intake-requests/{intake.id}/qualify",
        json={"notes": "Verified caller"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "qualified"
    assert resp.json()["notes"] == "Verified caller"


@pytest.mark.asyncio
async def test_api_convert_intake(client, auth_headers, db_session):
    intake = await submit_request(db_session, _intake_data(building_city="Bern", building_postal_code="3000"))
    await db_session.commit()

    resp = await client.post(
        f"/api/v1/intake-requests/{intake.id}/convert",
        json={},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "converted"
    assert body["converted_contact_id"] is not None
    assert body["converted_building_id"] is not None


@pytest.mark.asyncio
async def test_api_reject_intake(client, auth_headers, db_session):
    intake = await submit_request(db_session, _intake_data())
    await db_session.commit()

    resp = await client.post(
        f"/api/v1/intake-requests/{intake.id}/reject",
        json={"reason": "Duplicate request"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"
    assert resp.json()["notes"] == "Duplicate request"


@pytest.mark.asyncio
async def test_api_qualify_already_converted_fails(client, auth_headers, db_session, admin_user):
    intake = await submit_request(db_session, _intake_data(building_city="Zurich", building_postal_code="8000"))
    await convert_request(db_session, intake, admin_user.id)
    await db_session.commit()

    resp = await client.post(
        f"/api/v1/intake-requests/{intake.id}/qualify",
        json={},
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_api_intake_not_found(client, auth_headers):
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/intake-requests/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_intake_unauthorized(client):
    """Admin endpoints require auth."""
    resp = await client.get("/api/v1/intake-requests")
    assert resp.status_code in (401, 403)
