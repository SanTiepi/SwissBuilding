import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.api.pack_impact import router as pack_impact_router
from app.main import app
from app.models.evidence_pack import EvidencePack
from app.models.intervention import Intervention
from app.models.zone import Zone
from app.schemas.pack_impact import PackImpactType
from app.services.pack_impact_service import get_stale_packs, simulate_pack_impact

app.include_router(pack_impact_router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def sample_zone(db_session, sample_building):
    zone = Zone(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        name="Zone A - Ground Floor",
        zone_type="floor",
        floor_number=0,
    )
    db_session.add(zone)
    await db_session.commit()
    await db_session.refresh(zone)
    return zone


@pytest.fixture
async def sample_pack(db_session, sample_building):
    pack = EvidencePack(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        pack_type="authority_pack",
        title="Authority Pack v1",
        status="complete",
        created_at=datetime.now(UTC) - timedelta(days=30),
        updated_at=datetime.now(UTC) - timedelta(days=30),
    )
    db_session.add(pack)
    await db_session.commit()
    await db_session.refresh(pack)
    return pack


@pytest.fixture
async def planned_intervention(db_session, sample_building, sample_zone):
    intervention = Intervention(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        intervention_type="renovation",
        title="Full renovation ground floor",
        status="planned",
        zones_affected=[str(sample_zone.id)],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(intervention)
    await db_session.commit()
    await db_session.refresh(intervention)
    return intervention


@pytest.fixture
async def completed_intervention(db_session, sample_building, sample_zone):
    intervention = Intervention(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        intervention_type="asbestos_removal",
        title="Asbestos removal in zone A",
        status="completed",
        zones_affected=[str(sample_zone.id)],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(intervention)
    await db_session.commit()
    await db_session.refresh(intervention)
    return intervention


@pytest.fixture
async def inspection_intervention(db_session, sample_building):
    intervention = Intervention(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        intervention_type="inspection",
        title="Routine inspection",
        status="planned",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(intervention)
    await db_session.commit()
    await db_session.refresh(intervention)
    return intervention


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


class TestSimulatePackImpact:
    async def test_no_interventions_returns_empty_affected(self, db_session, sample_building, sample_pack):
        """Simulate with no planned interventions returns unaffected packs."""
        result = await simulate_pack_impact(db_session, sample_building.id)
        assert result is not None
        assert result.interventions_analyzed == 0
        assert result.packs_analyzed == 1
        # All packs should be unaffected when no interventions exist
        for pack in result.affected_packs:
            assert pack.impact_type == PackImpactType.unaffected

    async def test_intervention_affecting_zone_degrades_pack(
        self, db_session, sample_building, sample_pack, sample_zone, planned_intervention
    ):
        """Intervention affecting a zone should degrade or invalidate the pack."""
        result = await simulate_pack_impact(db_session, sample_building.id)
        assert result is not None
        assert result.interventions_analyzed == 1
        assert result.packs_analyzed == 1
        affected = result.affected_packs[0]
        # Renovation is an invalidating type
        assert affected.impact_type == PackImpactType.invalidated
        assert len(affected.affected_sections) > 0

    async def test_remediation_intervention_improves_pack(
        self, db_session, sample_building, sample_pack, inspection_intervention
    ):
        """Inspection-type intervention should improve pack."""
        result = await simulate_pack_impact(db_session, sample_building.id)
        assert result is not None
        affected = result.affected_packs[0]
        assert affected.impact_type == PackImpactType.improved

    async def test_no_packs_returns_zero_analyzed(self, db_session, sample_building, planned_intervention):
        """Building with no packs returns packs_analyzed=0."""
        result = await simulate_pack_impact(db_session, sample_building.id)
        assert result is not None
        assert result.packs_analyzed == 0
        assert len(result.affected_packs) == 0

    async def test_nonexistent_building_returns_none(self, db_session):
        """Nonexistent building returns None."""
        result = await simulate_pack_impact(db_session, uuid.uuid4())
        assert result is None

    async def test_risk_level_low_when_no_impact(self, db_session, sample_building, sample_pack):
        """Risk level is low when no interventions impact packs."""
        result = await simulate_pack_impact(db_session, sample_building.id)
        assert result is not None
        assert result.risk_level == "low"

    async def test_risk_level_medium_with_invalidated(
        self, db_session, sample_building, sample_pack, sample_zone, planned_intervention
    ):
        """Risk level is at least medium when a pack is invalidated."""
        result = await simulate_pack_impact(db_session, sample_building.id)
        assert result is not None
        assert result.risk_level in ("medium", "high", "critical")

    async def test_recommendations_generated_for_degraded(
        self, db_session, sample_building, sample_pack, sample_zone, planned_intervention
    ):
        """Recommendations are generated when packs are affected."""
        result = await simulate_pack_impact(db_session, sample_building.id)
        assert result is not None
        assert len(result.recommendations) > 0

    async def test_projected_trust_lower_for_invalidated(
        self, db_session, sample_building, sample_pack, sample_zone, planned_intervention
    ):
        """Projected trust score should be lower than current for invalidated packs."""
        result = await simulate_pack_impact(db_session, sample_building.id)
        assert result is not None
        affected = result.affected_packs[0]
        assert affected.current_trust_score is not None
        assert affected.projected_trust_score is not None
        assert affected.projected_trust_score < affected.current_trust_score

    async def test_simulate_with_specific_intervention_ids(
        self, db_session, sample_building, sample_pack, sample_zone, planned_intervention
    ):
        """Simulate with explicit intervention_ids works."""
        result = await simulate_pack_impact(db_session, sample_building.id, intervention_ids=[planned_intervention.id])
        assert result is not None
        assert result.interventions_analyzed == 1

    async def test_summary_counts_correct(
        self, db_session, sample_building, sample_pack, sample_zone, planned_intervention
    ):
        """Summary counts match actual affected packs."""
        result = await simulate_pack_impact(db_session, sample_building.id)
        assert result is not None
        s = result.summary
        total = s.invalidated_count + s.degraded_count + s.unaffected_count + s.improved_count
        assert total == result.packs_analyzed


class TestGetStalePacks:
    async def test_no_stale_packs(self, db_session, sample_building, sample_pack):
        """No stale packs when no completed interventions exist."""
        result = await get_stale_packs(db_session, sample_building.id)
        assert len(result) == 0

    async def test_stale_pack_after_intervention(
        self, db_session, sample_building, sample_pack, sample_zone, completed_intervention
    ):
        """Pack is stale when a completed intervention is newer than pack."""
        result = await get_stale_packs(db_session, sample_building.id)
        assert len(result) == 1
        assert result[0].pack_id == sample_pack.id
        assert result[0].impact_type == PackImpactType.degraded

    async def test_no_packs_returns_empty(self, db_session, sample_building):
        """No packs at all returns empty list."""
        result = await get_stale_packs(db_session, sample_building.id)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


class TestPackImpactAPI:
    async def test_get_pack_impact_200(self, client, admin_user, auth_headers, sample_building):
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/pack-impact",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["building_id"] == str(sample_building.id)
        assert "summary" in data
        assert "risk_level" in data

    async def test_post_simulate_200(self, client, admin_user, auth_headers, sample_building):
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/pack-impact/simulate",
            json={"intervention_ids": []},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["interventions_analyzed"] == 0

    async def test_get_pack_impact_404_nonexistent(self, client, admin_user, auth_headers):
        fake_id = uuid.uuid4()
        response = await client.get(
            f"/api/v1/buildings/{fake_id}/pack-impact",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_get_stale_packs_200(self, client, admin_user, auth_headers, sample_building):
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/stale-packs",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
