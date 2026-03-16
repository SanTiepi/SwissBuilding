import uuid

from app.models.diagnostic import Diagnostic
from app.models.post_works_state import PostWorksState
from app.models.sample import Sample


class TestComparePostWorksEndpoint:
    async def test_compare_returns_correct_structure(self, client, admin_user, auth_headers, sample_building):
        """Compare endpoint returns correct before/after structure."""
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/post-works/compare",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["building_id"] == str(sample_building.id)
        assert data["intervention_id"] is None
        assert "before" in data
        assert "after" in data
        assert "summary" in data
        assert "total_positive_samples" in data["before"]
        assert "by_pollutant" in data["before"]
        assert "risk_areas" in data["before"]
        assert "removed" in data["after"]
        assert "remaining" in data["after"]
        assert "encapsulated" in data["after"]
        assert "treated" in data["after"]
        assert "remediation_rate" in data["summary"]
        assert "verification_rate" in data["summary"]
        assert "residual_risk_count" in data["summary"]

    async def test_compare_with_intervention_id(self, client, admin_user, auth_headers, sample_building):
        """Compare endpoint accepts optional intervention_id filter."""
        intervention_id = uuid.uuid4()
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/post-works/compare",
            params={"intervention_id": str(intervention_id)},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["intervention_id"] == str(intervention_id)

    async def test_compare_empty_building(self, client, admin_user, auth_headers, sample_building):
        """Compare for building with no samples returns zeros."""
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/post-works/compare",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["before"]["total_positive_samples"] == 0
        assert data["summary"]["remediation_rate"] == 0.0
        assert data["summary"]["verification_rate"] == 0.0
        assert data["summary"]["residual_risk_count"] == 0

    async def test_compare_building_not_found(self, client, admin_user, auth_headers):
        """Compare for non-existent building returns 404."""
        fake_id = uuid.uuid4()
        response = await client.get(
            f"/api/v1/buildings/{fake_id}/post-works/compare",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_compare_with_data(self, client, admin_user, auth_headers, sample_building, db_session):
        """Compare endpoint reflects actual samples and post-works states."""
        # Create a diagnostic with positive samples
        diag = Diagnostic(
            id=uuid.uuid4(),
            building_id=sample_building.id,
            diagnostic_type="asbestos",
            status="completed",
            diagnostician_id=admin_user.id,
        )
        db_session.add(diag)
        await db_session.flush()

        sample = Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number="S-001",
            pollutant_type="asbestos",
            threshold_exceeded=True,
            location_room="Basement",
            risk_level="high",
        )
        db_session.add(sample)
        await db_session.flush()

        # Create a post-works state
        pws = PostWorksState(
            id=uuid.uuid4(),
            building_id=sample_building.id,
            state_type="removed",
            pollutant_type="asbestos",
            title="Removed asbestos from basement",
            verified=True,
            verified_by=admin_user.id,
            recorded_by=admin_user.id,
        )
        db_session.add(pws)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/post-works/compare",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["before"]["total_positive_samples"] >= 1
        assert data["before"]["by_pollutant"].get("asbestos", 0) >= 1
        assert data["after"]["removed"] >= 1
        assert data["summary"]["remediation_rate"] > 0
        assert data["summary"]["verification_rate"] > 0


class TestPostWorksSummaryEndpoint:
    async def test_summary_returns_structure(self, client, admin_user, auth_headers, sample_building):
        """Summary endpoint returns correct structure."""
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/post-works/summary",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["building_id"] == str(sample_building.id)
        assert "total_states" in data
        assert "by_state_type" in data
        assert "by_pollutant" in data
        assert "verification_progress" in data

    async def test_summary_building_not_found(self, client, admin_user, auth_headers):
        """Summary for non-existent building returns 404."""
        fake_id = uuid.uuid4()
        response = await client.get(
            f"/api/v1/buildings/{fake_id}/post-works/summary",
            headers=auth_headers,
        )
        assert response.status_code == 404
