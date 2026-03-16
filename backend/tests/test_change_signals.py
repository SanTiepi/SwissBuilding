import uuid

from app.api.change_signals import router as change_signals_router
from app.main import app

app.include_router(change_signals_router, prefix="/api/v1")

SIGNAL_PAYLOAD = {
    "signal_type": "regulation_change",
    "severity": "warning",
    "title": "New asbestos threshold effective 2026-01-01",
    "description": "ORRChim Annex 2.15 updated thresholds",
    "source": "regulation_update",
}


class TestCreateChangeSignal:
    async def test_create_signal_admin(self, client, admin_user, auth_headers, sample_building):
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/change-signals",
            json=SIGNAL_PAYLOAD,
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["signal_type"] == "regulation_change"
        assert data["severity"] == "warning"
        assert data["status"] == "active"
        assert data["building_id"] == str(sample_building.id)

    async def test_create_signal_building_not_found(self, client, admin_user, auth_headers):
        fake_id = uuid.uuid4()
        response = await client.post(
            f"/api/v1/buildings/{fake_id}/change-signals",
            json=SIGNAL_PAYLOAD,
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestListChangeSignals:
    async def test_list_signals(self, client, admin_user, auth_headers, sample_building):
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/change-signals",
            json=SIGNAL_PAYLOAD,
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/change-signals",
            json={**SIGNAL_PAYLOAD, "title": "Source data updated"},
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/change-signals",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    async def test_list_filtered_by_type(self, client, admin_user, auth_headers, sample_building):
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/change-signals",
            json={**SIGNAL_PAYLOAD, "signal_type": "regulation_change"},
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/change-signals",
            json={**SIGNAL_PAYLOAD, "signal_type": "source_update", "title": "Data refresh"},
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/change-signals",
            params={"signal_type": "source_update"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["signal_type"] == "source_update"

    async def test_list_filtered_by_severity(self, client, admin_user, auth_headers, sample_building):
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/change-signals",
            json={**SIGNAL_PAYLOAD, "severity": "info", "title": "Info signal"},
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/change-signals",
            json={**SIGNAL_PAYLOAD, "severity": "action_required", "title": "Urgent signal"},
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/change-signals",
            params={"severity": "action_required"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["total"] == 1


class TestGetChangeSignal:
    async def test_get_signal(self, client, admin_user, auth_headers, sample_building):
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/change-signals",
            json=SIGNAL_PAYLOAD,
            headers=auth_headers,
        )
        signal_id = create_resp.json()["id"]
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/change-signals/{signal_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["id"] == signal_id

    async def test_get_signal_not_found(self, client, admin_user, auth_headers, sample_building):
        fake_id = uuid.uuid4()
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/change-signals/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestUpdateChangeSignal:
    async def test_update_signal(self, client, admin_user, auth_headers, sample_building):
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/change-signals",
            json=SIGNAL_PAYLOAD,
            headers=auth_headers,
        )
        signal_id = create_resp.json()["id"]
        response = await client.put(
            f"/api/v1/buildings/{sample_building.id}/change-signals/{signal_id}",
            json={"status": "acknowledged"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "acknowledged"
        assert data["signal_type"] == "regulation_change"


class TestDeleteChangeSignal:
    async def test_delete_signal(self, client, admin_user, auth_headers, sample_building):
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/change-signals",
            json=SIGNAL_PAYLOAD,
            headers=auth_headers,
        )
        signal_id = create_resp.json()["id"]
        response = await client.delete(
            f"/api/v1/buildings/{sample_building.id}/change-signals/{signal_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204
        get_resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/change-signals/{signal_id}",
            headers=auth_headers,
        )
        assert get_resp.status_code == 404
