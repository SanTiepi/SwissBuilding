"""Tests for DefectShield API endpoints — CRUD + state transitions.

Covers: POST create, GET fetch, PATCH status update, DELETE soft-delete.
Validates status codes, state transition enforcement, and alert notifications.
"""

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from jose import jwt

from app.models.building import Building
from app.models.organization import Organization
from app.models.user import User

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def org(db_session):
    o = Organization(
        id=uuid.uuid4(),
        name="Test Org DefectShield",
        type="diagnostic_lab",
    )
    db_session.add(o)
    await db_session.commit()
    await db_session.refresh(o)
    return o


@pytest.fixture
async def org_user(db_session, org):
    from tests.conftest import _HASH_ADMIN

    u = User(
        id=uuid.uuid4(),
        email="defect-api-tester@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Defect",
        last_name="Tester",
        role="admin",
        organization_id=org.id,
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest.fixture
async def building(db_session, org, org_user):
    b = Building(
        id=uuid.uuid4(),
        official_id="DEFECT-API-001",
        address="Rue du Defaut 1",
        city="Lausanne",
        canton="VD",
        postal_code="1000",
        building_type="residential",
        created_by=org_user.id,
        organization_id=org.id,
    )
    db_session.add(b)
    await db_session.commit()
    await db_session.refresh(b)
    return b


@pytest.fixture
def auth_header(org_user):
    payload = {
        "sub": str(org_user.id),
        "email": org_user.email,
        "role": org_user.role,
        "exp": datetime.now(UTC) + timedelta(hours=8),
    }
    token = jwt.encode(payload, "test-secret-key-for-testing-only", algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def create_payload(building):
    return {
        "building_id": str(building.id),
        "defect_type": "construction",
        "description": "Fissure facade nord",
        "discovery_date": date.today().isoformat(),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_timeline(client, auth_header, create_payload):
    """Helper: create a timeline and return the response JSON."""
    resp = await client.post("/api/v1/defects/timeline", json=create_payload, headers=auth_header)
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# POST /defects/timeline — create
# ---------------------------------------------------------------------------


class TestCreateEndpoint:
    async def test_create_returns_201(self, client, auth_header, create_payload):
        resp = await client.post("/api/v1/defects/timeline", json=create_payload, headers=auth_header)
        assert resp.status_code == 201
        body = resp.json()
        assert body["building_id"] == create_payload["building_id"]
        assert body["defect_type"] == "construction"
        assert body["status"] == "active"
        assert body["notification_deadline"] is not None

    async def test_create_with_purchase_date(self, client, auth_header, building):
        payload = {
            "building_id": str(building.id),
            "defect_type": "pollutant",
            "discovery_date": date.today().isoformat(),
            "purchase_date": (date.today() - timedelta(days=365)).isoformat(),
        }
        resp = await client.post("/api/v1/defects/timeline", json=payload, headers=auth_header)
        assert resp.status_code == 201
        body = resp.json()
        assert body["prescription_date"] is not None
        assert body["guarantee_type"] in ("standard", "new_build_rectification")

    async def test_create_building_not_found(self, client, auth_header):
        payload = {
            "building_id": str(uuid.uuid4()),
            "defect_type": "construction",
            "discovery_date": date.today().isoformat(),
        }
        resp = await client.post("/api/v1/defects/timeline", json=payload, headers=auth_header)
        assert resp.status_code == 404

    async def test_create_invalid_defect_type(self, client, auth_header, building):
        payload = {
            "building_id": str(building.id),
            "defect_type": "invalid_type",
            "discovery_date": date.today().isoformat(),
        }
        resp = await client.post("/api/v1/defects/timeline", json=payload, headers=auth_header)
        assert resp.status_code == 422  # Pydantic validation


# ---------------------------------------------------------------------------
# GET /defects/timelines/{timeline_id} — fetch single
# ---------------------------------------------------------------------------


class TestGetEndpoint:
    async def test_get_returns_200(self, client, auth_header, create_payload):
        created = await _create_timeline(client, auth_header, create_payload)
        timeline_id = created["id"]

        resp = await client.get(f"/api/v1/defects/timelines/{timeline_id}", headers=auth_header)
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == timeline_id
        assert body["status"] == "active"
        assert body["defect_type"] == "construction"

    async def test_get_not_found(self, client, auth_header):
        resp = await client.get(f"/api/v1/defects/timelines/{uuid.uuid4()}", headers=auth_header)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /defects/timelines/{timeline_id} — update status
# ---------------------------------------------------------------------------


class TestPatchEndpoint:
    async def test_transition_active_to_notified(self, client, auth_header, create_payload):
        created = await _create_timeline(client, auth_header, create_payload)
        timeline_id = created["id"]

        resp = await client.patch(
            f"/api/v1/defects/timelines/{timeline_id}",
            json={"status": "notified"},
            headers=auth_header,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "notified"

    async def test_transition_active_to_resolved(self, client, auth_header, create_payload):
        created = await _create_timeline(client, auth_header, create_payload)
        timeline_id = created["id"]

        resp = await client.patch(
            f"/api/v1/defects/timelines/{timeline_id}",
            json={"status": "resolved"},
            headers=auth_header,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "resolved"

    async def test_transition_notified_to_resolved(self, client, auth_header, create_payload):
        created = await _create_timeline(client, auth_header, create_payload)
        timeline_id = created["id"]

        # First: active → notified
        await client.patch(
            f"/api/v1/defects/timelines/{timeline_id}",
            json={"status": "notified"},
            headers=auth_header,
        )
        # Then: notified → resolved
        resp = await client.patch(
            f"/api/v1/defects/timelines/{timeline_id}",
            json={"status": "resolved"},
            headers=auth_header,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "resolved"

    async def test_invalid_transition_resolved_to_active(self, client, auth_header, create_payload):
        created = await _create_timeline(client, auth_header, create_payload)
        timeline_id = created["id"]

        # Resolve first
        await client.patch(
            f"/api/v1/defects/timelines/{timeline_id}",
            json={"status": "resolved"},
            headers=auth_header,
        )
        # Try to reactivate — should fail
        resp = await client.patch(
            f"/api/v1/defects/timelines/{timeline_id}",
            json={"status": "active"},
            headers=auth_header,
        )
        assert resp.status_code == 400
        assert "Invalid transition" in resp.json()["detail"]

    async def test_invalid_transition_notified_to_active(self, client, auth_header, create_payload):
        created = await _create_timeline(client, auth_header, create_payload)
        timeline_id = created["id"]

        await client.patch(
            f"/api/v1/defects/timelines/{timeline_id}",
            json={"status": "notified"},
            headers=auth_header,
        )
        resp = await client.patch(
            f"/api/v1/defects/timelines/{timeline_id}",
            json={"status": "active"},
            headers=auth_header,
        )
        assert resp.status_code == 400

    async def test_patch_not_found(self, client, auth_header):
        resp = await client.patch(
            f"/api/v1/defects/timelines/{uuid.uuid4()}",
            json={"status": "notified"},
            headers=auth_header,
        )
        assert resp.status_code == 404

    async def test_update_description_only(self, client, auth_header, create_payload):
        created = await _create_timeline(client, auth_header, create_payload)
        timeline_id = created["id"]

        resp = await client.patch(
            f"/api/v1/defects/timelines/{timeline_id}",
            json={"description": "Updated description"},
            headers=auth_header,
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "Updated description"
        assert resp.json()["status"] == "active"  # unchanged

    async def test_full_lifecycle_active_notified_resolved(self, client, auth_header, create_payload):
        """Full state machine walk: active → notified → resolved."""
        created = await _create_timeline(client, auth_header, create_payload)
        tid = created["id"]

        # active → notified
        r1 = await client.patch(f"/api/v1/defects/timelines/{tid}", json={"status": "notified"}, headers=auth_header)
        assert r1.status_code == 200
        assert r1.json()["status"] == "notified"

        # notified → resolved
        r2 = await client.patch(f"/api/v1/defects/timelines/{tid}", json={"status": "resolved"}, headers=auth_header)
        assert r2.status_code == 200
        assert r2.json()["status"] == "resolved"

        # resolved is terminal
        r3 = await client.patch(f"/api/v1/defects/timelines/{tid}", json={"status": "notified"}, headers=auth_header)
        assert r3.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /defects/timelines/{timeline_id} — soft delete
# ---------------------------------------------------------------------------


class TestDeleteEndpoint:
    async def test_delete_returns_200(self, client, auth_header, create_payload):
        created = await _create_timeline(client, auth_header, create_payload)
        timeline_id = created["id"]

        resp = await client.delete(f"/api/v1/defects/timelines/{timeline_id}", headers=auth_header)
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == timeline_id

        # Verify it's soft-deleted (still fetchable but status=deleted)
        get_resp = await client.get(f"/api/v1/defects/timelines/{timeline_id}", headers=auth_header)
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "deleted"

    async def test_delete_not_found(self, client, auth_header):
        resp = await client.delete(f"/api/v1/defects/timelines/{uuid.uuid4()}", headers=auth_header)
        assert resp.status_code == 404

    async def test_delete_already_deleted(self, client, auth_header, create_payload):
        created = await _create_timeline(client, auth_header, create_payload)
        timeline_id = created["id"]

        # First delete
        resp1 = await client.delete(f"/api/v1/defects/timelines/{timeline_id}", headers=auth_header)
        assert resp1.status_code == 200

        # Second delete — still succeeds (idempotent soft-delete)
        resp2 = await client.delete(f"/api/v1/defects/timelines/{timeline_id}", headers=auth_header)
        assert resp2.status_code == 200
