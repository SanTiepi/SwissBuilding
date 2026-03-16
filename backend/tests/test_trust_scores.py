import uuid

from app.api.trust_scores import router as trust_scores_router
from app.main import app

app.include_router(trust_scores_router, prefix="/api/v1")

SCORE_PAYLOAD = {
    "overall_score": 0.72,
    "percent_proven": 0.5,
    "percent_inferred": 0.2,
    "percent_declared": 0.2,
    "percent_obsolete": 0.05,
    "percent_contradictory": 0.05,
    "total_data_points": 100,
    "proven_count": 50,
    "inferred_count": 20,
    "declared_count": 20,
    "obsolete_count": 5,
    "contradictory_count": 5,
    "trend": "improving",
    "previous_score": 0.65,
    "assessed_by": "system",
    "notes": "Initial trust assessment",
}


class TestCreateTrustScore:
    async def test_create_score_admin(self, client, admin_user, auth_headers, sample_building):
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/trust-scores",
            json=SCORE_PAYLOAD,
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["overall_score"] == 0.72
        assert data["trend"] == "improving"
        assert data["building_id"] == str(sample_building.id)
        assert data["total_data_points"] == 100

    async def test_create_score_building_not_found(self, client, admin_user, auth_headers):
        fake_id = uuid.uuid4()
        response = await client.post(
            f"/api/v1/buildings/{fake_id}/trust-scores",
            json=SCORE_PAYLOAD,
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestListTrustScores:
    async def test_list_scores(self, client, admin_user, auth_headers, sample_building):
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/trust-scores",
            json=SCORE_PAYLOAD,
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/trust-scores",
            json={**SCORE_PAYLOAD, "overall_score": 0.85, "trend": "stable"},
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/trust-scores",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    async def test_list_filtered_by_trend(self, client, admin_user, auth_headers, sample_building):
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/trust-scores",
            json={**SCORE_PAYLOAD, "trend": "improving"},
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/trust-scores",
            json={**SCORE_PAYLOAD, "trend": "declining"},
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/trust-scores",
            params={"trend": "declining"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["trend"] == "declining"


class TestGetTrustScore:
    async def test_get_score(self, client, admin_user, auth_headers, sample_building):
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/trust-scores",
            json=SCORE_PAYLOAD,
            headers=auth_headers,
        )
        score_id = create_resp.json()["id"]
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/trust-scores/{score_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["id"] == score_id

    async def test_get_score_not_found(self, client, admin_user, auth_headers, sample_building):
        fake_id = uuid.uuid4()
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/trust-scores/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestUpdateTrustScore:
    async def test_update_score(self, client, admin_user, auth_headers, sample_building):
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/trust-scores",
            json=SCORE_PAYLOAD,
            headers=auth_headers,
        )
        score_id = create_resp.json()["id"]
        response = await client.put(
            f"/api/v1/buildings/{sample_building.id}/trust-scores/{score_id}",
            json={"overall_score": 0.90, "trend": "stable"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["overall_score"] == 0.90
        assert data["trend"] == "stable"
        assert data["percent_proven"] == 0.5


class TestDeleteTrustScore:
    async def test_delete_score(self, client, admin_user, auth_headers, sample_building):
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/trust-scores",
            json=SCORE_PAYLOAD,
            headers=auth_headers,
        )
        score_id = create_resp.json()["id"]
        response = await client.delete(
            f"/api/v1/buildings/{sample_building.id}/trust-scores/{score_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204
        get_resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/trust-scores/{score_id}",
            headers=auth_headers,
        )
        assert get_resp.status_code == 404
