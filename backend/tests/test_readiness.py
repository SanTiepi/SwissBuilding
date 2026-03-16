import uuid

from app.api.readiness import router as readiness_router
from app.main import app

app.include_router(readiness_router, prefix="/api/v1")

ASSESSMENT_PAYLOAD = {
    "readiness_type": "safe_to_start",
    "status": "not_ready",
    "score": 0.45,
    "checks_json": [
        {"name": "asbestos_diagnostic", "passed": True},
        {"name": "pcb_diagnostic", "passed": False},
    ],
    "blockers_json": [{"type": "missing_diagnostic", "detail": "PCB diagnostic required"}],
    "notes": "Pending PCB diagnostic completion",
}


class TestCreateReadinessAssessment:
    async def test_create_assessment_admin(self, client, admin_user, auth_headers, sample_building):
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/readiness",
            json=ASSESSMENT_PAYLOAD,
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["readiness_type"] == "safe_to_start"
        assert data["status"] == "not_ready"
        assert data["score"] == 0.45
        assert data["assessed_by"] == str(admin_user.id)
        assert data["building_id"] == str(sample_building.id)
        assert len(data["checks_json"]) == 2
        assert len(data["blockers_json"]) == 1

    async def test_create_assessment_building_not_found(self, client, admin_user, auth_headers):
        fake_id = uuid.uuid4()
        response = await client.post(
            f"/api/v1/buildings/{fake_id}/readiness",
            json=ASSESSMENT_PAYLOAD,
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestListReadinessAssessments:
    async def test_list_assessments(self, client, admin_user, auth_headers, sample_building):
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/readiness",
            json=ASSESSMENT_PAYLOAD,
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/readiness",
            json={**ASSESSMENT_PAYLOAD, "readiness_type": "safe_to_renovate"},
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/readiness",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    async def test_list_filtered_by_type(self, client, admin_user, auth_headers, sample_building):
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/readiness",
            json={**ASSESSMENT_PAYLOAD, "readiness_type": "safe_to_start"},
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/readiness",
            json={**ASSESSMENT_PAYLOAD, "readiness_type": "safe_to_sell"},
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/readiness",
            params={"readiness_type": "safe_to_sell"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["readiness_type"] == "safe_to_sell"

    async def test_list_filtered_by_status(self, client, admin_user, auth_headers, sample_building):
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/readiness",
            json={**ASSESSMENT_PAYLOAD, "status": "ready", "score": 1.0},
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/readiness",
            json={**ASSESSMENT_PAYLOAD, "status": "not_ready"},
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/readiness",
            params={"status": "ready"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["total"] == 1


class TestGetReadinessAssessment:
    async def test_get_assessment(self, client, admin_user, auth_headers, sample_building):
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/readiness",
            json=ASSESSMENT_PAYLOAD,
            headers=auth_headers,
        )
        assessment_id = create_resp.json()["id"]
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/readiness/{assessment_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["id"] == assessment_id

    async def test_get_assessment_not_found(self, client, admin_user, auth_headers, sample_building):
        fake_id = uuid.uuid4()
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/readiness/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestUpdateReadinessAssessment:
    async def test_update_assessment(self, client, admin_user, auth_headers, sample_building):
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/readiness",
            json=ASSESSMENT_PAYLOAD,
            headers=auth_headers,
        )
        assessment_id = create_resp.json()["id"]
        response = await client.put(
            f"/api/v1/buildings/{sample_building.id}/readiness/{assessment_id}",
            json={"status": "ready", "score": 1.0, "blockers_json": []},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["score"] == 1.0
        assert data["blockers_json"] == []
        assert data["readiness_type"] == "safe_to_start"


class TestDeleteReadinessAssessment:
    async def test_delete_assessment(self, client, admin_user, auth_headers, sample_building):
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/readiness",
            json=ASSESSMENT_PAYLOAD,
            headers=auth_headers,
        )
        assessment_id = create_resp.json()["id"]
        response = await client.delete(
            f"/api/v1/buildings/{sample_building.id}/readiness/{assessment_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204
        get_resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/readiness/{assessment_id}",
            headers=auth_headers,
        )
        assert get_resp.status_code == 404


class TestPreworkTriggersEndpoint:
    async def test_get_prework_triggers(self, client, admin_user, auth_headers, sample_building):
        """Prework triggers endpoint should return a list."""
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/readiness",
            json=ASSESSMENT_PAYLOAD,
            headers=auth_headers,
        )
        assessment_id = create_resp.json()["id"]
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/readiness/{assessment_id}/prework-triggers",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_prework_triggers_in_read_response(self, client, admin_user, auth_headers, sample_building):
        """ReadinessAssessmentRead responses should include prework_triggers field."""
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/readiness",
            json=ASSESSMENT_PAYLOAD,
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        data = create_resp.json()
        # prework_triggers should be present (derived from checks_json)
        assert "prework_triggers" in data
        assert isinstance(data["prework_triggers"], list)

    async def test_prework_triggers_not_found(self, client, admin_user, auth_headers, sample_building):
        fake_id = uuid.uuid4()
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/readiness/{fake_id}/prework-triggers",
            headers=auth_headers,
        )
        assert response.status_code == 404
