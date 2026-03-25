import uuid
from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from app.api.interventions import router as interventions_router
from app.main import app
from app.models.user import User

# Register the router for tests (not yet in router.py)
app.include_router(interventions_router, prefix="/api/v1")


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


INTERVENTION_PAYLOAD = {
    "intervention_type": "removal",
    "title": "Asbestos removal floor 2",
    "description": "Complete removal of asbestos-containing materials",
    "status": "completed",
    "contractor_name": "DepoClean SA",
    "cost_chf": 15000.0,
}


class TestCreateIntervention:
    async def test_create_intervention_admin(self, client, admin_user, auth_headers, sample_building):
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/interventions",
            json=INTERVENTION_PAYLOAD,
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Asbestos removal floor 2"
        assert data["intervention_type"] == "removal"
        assert data["created_by"] == str(admin_user.id)
        assert data["building_id"] == str(sample_building.id)

    async def test_create_intervention_owner(self, client, owner_user, owner_headers, sample_building):
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/interventions",
            json=INTERVENTION_PAYLOAD,
            headers=owner_headers,
        )
        assert response.status_code == 201
        assert response.json()["created_by"] == str(owner_user.id)

    async def test_create_intervention_contractor(self, client, contractor_user, sample_building):
        headers = _make_headers(contractor_user)
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/interventions",
            json=INTERVENTION_PAYLOAD,
            headers=headers,
        )
        assert response.status_code == 201

    async def test_architect_cannot_create_intervention(self, client, architect_user, sample_building):
        headers = _make_headers(architect_user)
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/interventions",
            json=INTERVENTION_PAYLOAD,
            headers=headers,
        )
        assert response.status_code in (401, 403)

    async def test_create_intervention_building_not_found(self, client, admin_user, auth_headers):
        fake_id = uuid.uuid4()
        response = await client.post(
            f"/api/v1/buildings/{fake_id}/interventions",
            json=INTERVENTION_PAYLOAD,
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestListInterventions:
    async def test_list_interventions(self, client, admin_user, auth_headers, sample_building):
        # Create two interventions
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/interventions",
            json=INTERVENTION_PAYLOAD,
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/interventions",
            json={**INTERVENTION_PAYLOAD, "title": "Second intervention"},
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/interventions",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_list_filtered_by_type(self, client, admin_user, auth_headers, sample_building):
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/interventions",
            json={**INTERVENTION_PAYLOAD, "intervention_type": "removal"},
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/interventions",
            json={**INTERVENTION_PAYLOAD, "intervention_type": "encapsulation"},
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/interventions",
            params={"intervention_type": "removal"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["intervention_type"] == "removal"

    async def test_list_filtered_by_status(self, client, admin_user, auth_headers, sample_building):
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/interventions",
            json={**INTERVENTION_PAYLOAD, "status": "completed"},
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/interventions",
            json={**INTERVENTION_PAYLOAD, "status": "in_progress"},
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/interventions",
            params={"status": "in_progress"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "in_progress"

    async def test_list_pagination(self, client, admin_user, auth_headers, sample_building):
        for i in range(5):
            await client.post(
                f"/api/v1/buildings/{sample_building.id}/interventions",
                json={**INTERVENTION_PAYLOAD, "title": f"Intervention {i}"},
                headers=auth_headers,
            )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/interventions",
            params={"page": 1, "size": 2},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["size"] == 2
        assert data["pages"] == 3


class TestGetIntervention:
    async def test_get_intervention(self, client, admin_user, auth_headers, sample_building):
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/interventions",
            json=INTERVENTION_PAYLOAD,
            headers=auth_headers,
        )
        intervention_id = create_resp.json()["id"]
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/interventions/{intervention_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["id"] == intervention_id

    async def test_get_intervention_not_found(self, client, admin_user, auth_headers, sample_building):
        fake_id = uuid.uuid4()
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/interventions/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_get_intervention_wrong_building(self, client, db_session, admin_user, auth_headers, sample_building):
        # Create intervention on sample_building
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/interventions",
            json=INTERVENTION_PAYLOAD,
            headers=auth_headers,
        )
        intervention_id = create_resp.json()["id"]

        # Create a second building
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

        # Try to get intervention via wrong building
        response = await client.get(
            f"/api/v1/buildings/{other_building.id}/interventions/{intervention_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestUpdateIntervention:
    async def test_update_intervention(self, client, admin_user, auth_headers, sample_building):
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/interventions",
            json=INTERVENTION_PAYLOAD,
            headers=auth_headers,
        )
        intervention_id = create_resp.json()["id"]
        response = await client.put(
            f"/api/v1/buildings/{sample_building.id}/interventions/{intervention_id}",
            json={"title": "Updated title", "cost_chf": 20000.0},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated title"
        assert data["cost_chf"] == 20000.0
        # Unchanged fields preserved
        assert data["intervention_type"] == "removal"


class TestDeleteIntervention:
    async def test_delete_intervention(self, client, admin_user, auth_headers, sample_building):
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/interventions",
            json=INTERVENTION_PAYLOAD,
            headers=auth_headers,
        )
        intervention_id = create_resp.json()["id"]
        response = await client.delete(
            f"/api/v1/buildings/{sample_building.id}/interventions/{intervention_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

        # Confirm deleted
        get_resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/interventions/{intervention_id}",
            headers=auth_headers,
        )
        assert get_resp.status_code == 404
