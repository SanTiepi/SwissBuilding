import uuid

from app.api.unknowns import router as unknowns_router
from app.main import app

app.include_router(unknowns_router, prefix="/api/v1")

ISSUE_PAYLOAD = {
    "unknown_type": "uninspected_zone",
    "severity": "high",
    "status": "open",
    "title": "Basement zone B2 never inspected for asbestos",
    "description": "No diagnostic record covers this zone",
    "entity_type": "zone",
    "blocks_readiness": True,
    "detected_by": "system",
}


class TestCreateUnknownIssue:
    async def test_create_issue_admin(self, client, admin_user, auth_headers, sample_building):
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/unknowns",
            json=ISSUE_PAYLOAD,
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["unknown_type"] == "uninspected_zone"
        assert data["severity"] == "high"
        assert data["building_id"] == str(sample_building.id)
        assert data["blocks_readiness"] is True

    async def test_create_issue_building_not_found(self, client, admin_user, auth_headers):
        fake_id = uuid.uuid4()
        response = await client.post(
            f"/api/v1/buildings/{fake_id}/unknowns",
            json=ISSUE_PAYLOAD,
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestListUnknownIssues:
    async def test_list_issues(self, client, admin_user, auth_headers, sample_building):
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/unknowns",
            json=ISSUE_PAYLOAD,
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/unknowns",
            json={**ISSUE_PAYLOAD, "unknown_type": "missing_plan", "title": "Missing floor plan"},
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/unknowns",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    async def test_list_filtered_by_type(self, client, admin_user, auth_headers, sample_building):
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/unknowns",
            json=ISSUE_PAYLOAD,
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/unknowns",
            json={**ISSUE_PAYLOAD, "unknown_type": "missing_plan", "title": "Missing plan"},
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/unknowns",
            params={"unknown_type": "missing_plan"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["unknown_type"] == "missing_plan"

    async def test_list_filtered_by_severity(self, client, admin_user, auth_headers, sample_building):
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/unknowns",
            json={**ISSUE_PAYLOAD, "severity": "critical", "title": "Critical unknown"},
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/unknowns",
            json={**ISSUE_PAYLOAD, "severity": "low", "title": "Low unknown"},
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/unknowns",
            params={"severity": "critical"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["total"] == 1


class TestGetUnknownIssue:
    async def test_get_issue(self, client, admin_user, auth_headers, sample_building):
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/unknowns",
            json=ISSUE_PAYLOAD,
            headers=auth_headers,
        )
        issue_id = create_resp.json()["id"]
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/unknowns/{issue_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["id"] == issue_id

    async def test_get_issue_not_found(self, client, admin_user, auth_headers, sample_building):
        fake_id = uuid.uuid4()
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/unknowns/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestUpdateUnknownIssue:
    async def test_update_issue(self, client, admin_user, auth_headers, sample_building):
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/unknowns",
            json=ISSUE_PAYLOAD,
            headers=auth_headers,
        )
        issue_id = create_resp.json()["id"]
        response = await client.put(
            f"/api/v1/buildings/{sample_building.id}/unknowns/{issue_id}",
            json={"status": "resolved", "resolution_notes": "Zone inspected on 2026-03-01"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resolved"
        assert data["resolution_notes"] == "Zone inspected on 2026-03-01"
        assert data["unknown_type"] == "uninspected_zone"


class TestDeleteUnknownIssue:
    async def test_delete_issue(self, client, admin_user, auth_headers, sample_building):
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/unknowns",
            json=ISSUE_PAYLOAD,
            headers=auth_headers,
        )
        issue_id = create_resp.json()["id"]
        response = await client.delete(
            f"/api/v1/buildings/{sample_building.id}/unknowns/{issue_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204
        get_resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/unknowns/{issue_id}",
            headers=auth_headers,
        )
        assert get_resp.status_code == 404
