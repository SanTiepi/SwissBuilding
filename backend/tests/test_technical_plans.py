import uuid
from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from app.api.technical_plans import router as plans_router
from app.main import app
from app.models.user import User

# Register the router for tests (not yet in router.py)
app.include_router(plans_router, prefix="/api/v1")


def _make_headers(user):
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "exp": datetime.now(UTC) + timedelta(hours=8),
    }
    token = jwt.encode(payload, "test-secret-key-for-testing-only", algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def architect_user(db_session):
    user = User(
        id=uuid.uuid4(),
        email="architect@test.ch",
        password_hash="$2b$12$LJ3m4ys3uz0GH0lFnOVz3u",
        first_name="Marie",
        last_name="Test",
        role="architect",
        is_active=True,
        language="fr",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def contractor_user(db_session):
    user = User(
        id=uuid.uuid4(),
        email="contractor@test.ch",
        password_hash="$2b$12$LJ3m4ys3uz0GH0lFnOVz3u",
        first_name="Pierre",
        last_name="Test",
        role="contractor",
        is_active=True,
        language="fr",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def authority_user(db_session):
    user = User(
        id=uuid.uuid4(),
        email="authority@test.ch",
        password_hash="$2b$12$LJ3m4ys3uz0GH0lFnOVz3u",
        first_name="Luc",
        last_name="Test",
        role="authority",
        is_active=True,
        language="fr",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


PLAN_PAYLOAD = {
    "plan_type": "floor_plan",
    "title": "Ground floor plan",
    "file_path": "/plans/ground_floor.pdf",
    "file_name": "ground_floor.pdf",
    "description": "Ground floor layout with zones",
    "floor_number": 0,
    "mime_type": "application/pdf",
    "file_size_bytes": 245000,
}


class TestCreatePlan:
    async def test_create_plan_admin(self, client, admin_user, auth_headers, sample_building):
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/plans",
            json=PLAN_PAYLOAD,
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Ground floor plan"
        assert data["plan_type"] == "floor_plan"
        assert data["uploaded_by"] == str(admin_user.id)
        assert data["building_id"] == str(sample_building.id)

    async def test_create_plan_architect(self, client, architect_user, sample_building):
        headers = _make_headers(architect_user)
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/plans",
            json=PLAN_PAYLOAD,
            headers=headers,
        )
        assert response.status_code == 201
        assert response.json()["uploaded_by"] == str(architect_user.id)

    async def test_create_plan_diagnostician(self, client, diagnostician_user, diag_headers, sample_building):
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/plans",
            json=PLAN_PAYLOAD,
            headers=diag_headers,
        )
        assert response.status_code == 201

    async def test_contractor_cannot_create_plan(self, client, contractor_user, sample_building):
        headers = _make_headers(contractor_user)
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/plans",
            json=PLAN_PAYLOAD,
            headers=headers,
        )
        assert response.status_code == 403

    async def test_authority_cannot_create_plan(self, client, authority_user, sample_building):
        headers = _make_headers(authority_user)
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/plans",
            json=PLAN_PAYLOAD,
            headers=headers,
        )
        assert response.status_code == 403

    async def test_create_plan_building_not_found(self, client, admin_user, auth_headers):
        fake_id = uuid.uuid4()
        response = await client.post(
            f"/api/v1/buildings/{fake_id}/plans",
            json=PLAN_PAYLOAD,
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestListPlans:
    async def test_list_plans(self, client, admin_user, auth_headers, sample_building):
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/plans",
            json=PLAN_PAYLOAD,
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/plans",
            json={**PLAN_PAYLOAD, "title": "First floor plan", "floor_number": 1},
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/plans",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_list_filtered_by_type(self, client, admin_user, auth_headers, sample_building):
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/plans",
            json={**PLAN_PAYLOAD, "plan_type": "floor_plan"},
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/plans",
            json={**PLAN_PAYLOAD, "plan_type": "section", "title": "Cross section A"},
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/plans",
            params={"plan_type": "section"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["plan_type"] == "section"


class TestGetPlan:
    async def test_get_plan(self, client, admin_user, auth_headers, sample_building):
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/plans",
            json=PLAN_PAYLOAD,
            headers=auth_headers,
        )
        plan_id = create_resp.json()["id"]
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/plans/{plan_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["id"] == plan_id

    async def test_get_plan_not_found(self, client, admin_user, auth_headers, sample_building):
        fake_id = uuid.uuid4()
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/plans/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_get_plan_wrong_building(self, client, db_session, admin_user, auth_headers, sample_building):
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/plans",
            json=PLAN_PAYLOAD,
            headers=auth_headers,
        )
        plan_id = create_resp.json()["id"]

        from app.models.building import Building

        other_building = Building(
            id=uuid.uuid4(),
            address="Rue Autre 5",
            postal_code="1200",
            city="Geneve",
            canton="GE",
            construction_year=1990,
            building_type="commercial",
            created_by=admin_user.id,
            status="active",
        )
        db_session.add(other_building)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/buildings/{other_building.id}/plans/{plan_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestDeletePlan:
    async def test_delete_plan(self, client, admin_user, auth_headers, sample_building):
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/plans",
            json=PLAN_PAYLOAD,
            headers=auth_headers,
        )
        plan_id = create_resp.json()["id"]
        response = await client.delete(
            f"/api/v1/buildings/{sample_building.id}/plans/{plan_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

        get_resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/plans/{plan_id}",
            headers=auth_headers,
        )
        assert get_resp.status_code == 404
