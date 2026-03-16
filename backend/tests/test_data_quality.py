import uuid

from app.api.data_quality import router as data_quality_router
from app.main import app

app.include_router(data_quality_router, prefix="/api/v1")

ISSUE_PAYLOAD = {
    "issue_type": "missing_field",
    "severity": "high",
    "description": "Construction year is missing",
    "field_name": "construction_year",
    "entity_type": "building",
    "detected_by": "system",
}


class TestCreateDataQualityIssue:
    async def test_create_issue_admin(self, client, admin_user, auth_headers, sample_building):
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/data-quality-issues",
            json=ISSUE_PAYLOAD,
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["issue_type"] == "missing_field"
        assert data["severity"] == "high"
        assert data["status"] == "open"
        assert data["building_id"] == str(sample_building.id)

    async def test_create_issue_building_not_found(self, client, admin_user, auth_headers):
        fake_id = uuid.uuid4()
        response = await client.post(
            f"/api/v1/buildings/{fake_id}/data-quality-issues",
            json=ISSUE_PAYLOAD,
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestListDataQualityIssues:
    async def test_list_issues(self, client, admin_user, auth_headers, sample_building):
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/data-quality-issues",
            json=ISSUE_PAYLOAD,
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/data-quality-issues",
            json={**ISSUE_PAYLOAD, "description": "Address format error"},
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/data-quality-issues",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    async def test_list_filtered_by_severity(self, client, admin_user, auth_headers, sample_building):
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/data-quality-issues",
            json={**ISSUE_PAYLOAD, "severity": "high"},
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/data-quality-issues",
            json={**ISSUE_PAYLOAD, "severity": "low", "description": "Minor issue"},
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/data-quality-issues",
            params={"severity": "low"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["severity"] == "low"

    async def test_list_filtered_by_status(self, client, admin_user, auth_headers, sample_building):
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/data-quality-issues",
            json=ISSUE_PAYLOAD,
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/data-quality-issues",
            params={"status": "open"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["total"] == 1


class TestGetDataQualityIssue:
    async def test_get_issue(self, client, admin_user, auth_headers, sample_building):
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/data-quality-issues",
            json=ISSUE_PAYLOAD,
            headers=auth_headers,
        )
        issue_id = create_resp.json()["id"]
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/data-quality-issues/{issue_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["id"] == issue_id

    async def test_get_issue_not_found(self, client, admin_user, auth_headers, sample_building):
        fake_id = uuid.uuid4()
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/data-quality-issues/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestUpdateDataQualityIssue:
    async def test_update_issue(self, client, admin_user, auth_headers, sample_building):
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/data-quality-issues",
            json=ISSUE_PAYLOAD,
            headers=auth_headers,
        )
        issue_id = create_resp.json()["id"]
        response = await client.put(
            f"/api/v1/buildings/{sample_building.id}/data-quality-issues/{issue_id}",
            json={"status": "resolved", "resolution_notes": "Field was added"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resolved"
        assert data["resolution_notes"] == "Field was added"


class TestDeleteDataQualityIssue:
    async def test_delete_issue(self, client, admin_user, auth_headers, sample_building):
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/data-quality-issues",
            json=ISSUE_PAYLOAD,
            headers=auth_headers,
        )
        issue_id = create_resp.json()["id"]
        response = await client.delete(
            f"/api/v1/buildings/{sample_building.id}/data-quality-issues/{issue_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204
        get_resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/data-quality-issues/{issue_id}",
            headers=auth_headers,
        )
        assert get_resp.status_code == 404
