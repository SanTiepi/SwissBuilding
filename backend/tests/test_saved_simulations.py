import uuid

from app.api.saved_simulations import router as simulations_router
from app.main import app

app.include_router(simulations_router, prefix="/api/v1")

SIMULATION_PAYLOAD = {
    "title": "Renovation scenario A",
    "description": "Full asbestos removal before renovation",
    "simulation_type": "renovation",
    "parameters_json": {"zones": ["floor_1", "floor_2"], "pollutants": ["asbestos"]},
    "results_json": {"phases": [{"name": "removal", "weeks": 4}]},
    "total_cost_chf": 125000.0,
    "total_duration_weeks": 8,
    "risk_level_before": "high",
    "risk_level_after": "low",
}


class TestCreateSimulation:
    async def test_create_simulation_admin(self, client, admin_user, auth_headers, sample_building):
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/simulations",
            json=SIMULATION_PAYLOAD,
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Renovation scenario A"
        assert data["simulation_type"] == "renovation"
        assert data["total_cost_chf"] == 125000.0
        assert data["created_by"] == str(admin_user.id)
        assert data["building_id"] == str(sample_building.id)

    async def test_create_simulation_building_not_found(self, client, admin_user, auth_headers):
        fake_id = uuid.uuid4()
        response = await client.post(
            f"/api/v1/buildings/{fake_id}/simulations",
            json=SIMULATION_PAYLOAD,
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestListSimulations:
    async def test_list_simulations(self, client, admin_user, auth_headers, sample_building):
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/simulations",
            json=SIMULATION_PAYLOAD,
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/simulations",
            json={**SIMULATION_PAYLOAD, "title": "Scenario B"},
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/simulations",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_list_filtered_by_type(self, client, admin_user, auth_headers, sample_building):
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/simulations",
            json={**SIMULATION_PAYLOAD, "simulation_type": "renovation"},
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/simulations",
            json={**SIMULATION_PAYLOAD, "simulation_type": "cost_estimate"},
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/simulations",
            params={"simulation_type": "cost_estimate"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["simulation_type"] == "cost_estimate"

    async def test_list_pagination(self, client, admin_user, auth_headers, sample_building):
        for i in range(5):
            await client.post(
                f"/api/v1/buildings/{sample_building.id}/simulations",
                json={**SIMULATION_PAYLOAD, "title": f"Sim {i}"},
                headers=auth_headers,
            )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/simulations",
            params={"page": 1, "size": 2},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["pages"] == 3


class TestGetSimulation:
    async def test_get_simulation(self, client, admin_user, auth_headers, sample_building):
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/simulations",
            json=SIMULATION_PAYLOAD,
            headers=auth_headers,
        )
        sim_id = create_resp.json()["id"]
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/simulations/{sim_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["id"] == sim_id

    async def test_get_simulation_not_found(self, client, admin_user, auth_headers, sample_building):
        fake_id = uuid.uuid4()
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/simulations/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestUpdateSimulation:
    async def test_update_simulation(self, client, admin_user, auth_headers, sample_building):
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/simulations",
            json=SIMULATION_PAYLOAD,
            headers=auth_headers,
        )
        sim_id = create_resp.json()["id"]
        response = await client.put(
            f"/api/v1/buildings/{sample_building.id}/simulations/{sim_id}",
            json={"title": "Updated scenario", "total_cost_chf": 200000.0},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated scenario"
        assert data["total_cost_chf"] == 200000.0
        assert data["simulation_type"] == "renovation"


class TestDeleteSimulation:
    async def test_delete_simulation(self, client, admin_user, auth_headers, sample_building):
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/simulations",
            json=SIMULATION_PAYLOAD,
            headers=auth_headers,
        )
        sim_id = create_resp.json()["id"]
        response = await client.delete(
            f"/api/v1/buildings/{sample_building.id}/simulations/{sim_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204
        get_resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/simulations/{sim_id}",
            headers=auth_headers,
        )
        assert get_resp.status_code == 404
