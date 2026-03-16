import uuid

from app.api.post_works import router as post_works_router
from app.main import app

app.include_router(post_works_router, prefix="/api/v1")

STATE_PAYLOAD = {
    "state_type": "removed",
    "pollutant_type": "asbestos",
    "title": "Asbestos pipe insulation removed from basement",
    "description": "Complete removal of chrysotile insulation on heating pipes",
    "verified": False,
    "notes": "Awaiting air clearance test results",
}


class TestCreatePostWorksState:
    async def test_create_state_admin(self, client, admin_user, auth_headers, sample_building):
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/post-works",
            json=STATE_PAYLOAD,
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["state_type"] == "removed"
        assert data["pollutant_type"] == "asbestos"
        assert data["building_id"] == str(sample_building.id)
        assert data["recorded_by"] == str(admin_user.id)
        assert data["verified"] is False

    async def test_create_state_building_not_found(self, client, admin_user, auth_headers):
        fake_id = uuid.uuid4()
        response = await client.post(
            f"/api/v1/buildings/{fake_id}/post-works",
            json=STATE_PAYLOAD,
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestListPostWorksStates:
    async def test_list_states(self, client, admin_user, auth_headers, sample_building):
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/post-works",
            json=STATE_PAYLOAD,
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/post-works",
            json={**STATE_PAYLOAD, "state_type": "remaining", "title": "PCB remaining in joints"},
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/post-works",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    async def test_list_filtered_by_state_type(self, client, admin_user, auth_headers, sample_building):
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/post-works",
            json=STATE_PAYLOAD,
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/post-works",
            json={**STATE_PAYLOAD, "state_type": "encapsulated", "title": "Encapsulated lead paint"},
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/post-works",
            params={"state_type": "encapsulated"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["state_type"] == "encapsulated"

    async def test_list_filtered_by_pollutant(self, client, admin_user, auth_headers, sample_building):
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/post-works",
            json={**STATE_PAYLOAD, "pollutant_type": "pcb", "title": "PCB removed"},
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/post-works",
            json=STATE_PAYLOAD,
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/post-works",
            params={"pollutant_type": "pcb"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["total"] == 1


class TestGetPostWorksState:
    async def test_get_state(self, client, admin_user, auth_headers, sample_building):
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/post-works",
            json=STATE_PAYLOAD,
            headers=auth_headers,
        )
        state_id = create_resp.json()["id"]
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/post-works/{state_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["id"] == state_id

    async def test_get_state_not_found(self, client, admin_user, auth_headers, sample_building):
        fake_id = uuid.uuid4()
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/post-works/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestUpdatePostWorksState:
    async def test_update_state(self, client, admin_user, auth_headers, sample_building):
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/post-works",
            json=STATE_PAYLOAD,
            headers=auth_headers,
        )
        state_id = create_resp.json()["id"]
        response = await client.put(
            f"/api/v1/buildings/{sample_building.id}/post-works/{state_id}",
            json={"verified": True, "notes": "Air clearance test passed"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["verified"] is True
        assert data["notes"] == "Air clearance test passed"
        assert data["state_type"] == "removed"


class TestDeletePostWorksState:
    async def test_delete_state(self, client, admin_user, auth_headers, sample_building):
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/post-works",
            json=STATE_PAYLOAD,
            headers=auth_headers,
        )
        state_id = create_resp.json()["id"]
        response = await client.delete(
            f"/api/v1/buildings/{sample_building.id}/post-works/{state_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204
        get_resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/post-works/{state_id}",
            headers=auth_headers,
        )
        assert get_resp.status_code == 404
