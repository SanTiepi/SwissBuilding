"""Tests for sample optimization service and API."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.zone import Zone
from app.services.sample_optimization_service import (
    LAB_TURNAROUND_DAYS,
    SAMPLE_MAX_AGE_YEARS,
    _applicable_pollutants,
    _is_sample_outdated,
    estimate_sampling_cost,
    evaluate_sampling_adequacy,
    get_portfolio_sampling_status,
    optimize_sampling_plan,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def building_1965(db_session, admin_user):
    """Pre-1990 building (asbestos, pcb, lead, hap, radon all applicable)."""
    b = Building(
        id=uuid.uuid4(),
        address="Rue Optimisation 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.commit()
    await db_session.refresh(b)
    return b


@pytest.fixture
async def building_2000(db_session, admin_user):
    """Post-1990 building (only lead, hap, radon applicable)."""
    b = Building(
        id=uuid.uuid4(),
        address="Rue Moderne 10",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=2000,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.commit()
    await db_session.refresh(b)
    return b


@pytest.fixture
async def zones_for_building(db_session, building_1965, admin_user):
    """Create 3 zones for building_1965."""
    zone_data = [
        ("basement", "Sous-sol", -1),
        ("room", "Bureau 101", 1),
        ("staircase", "Cage escalier", 0),
    ]
    zones = []
    for ztype, name, floor in zone_data:
        z = Zone(
            id=uuid.uuid4(),
            building_id=building_1965.id,
            zone_type=ztype,
            name=name,
            floor_number=floor,
            created_by=admin_user.id,
        )
        db_session.add(z)
        zones.append(z)
    await db_session.commit()
    for z in zones:
        await db_session.refresh(z)
    return zones


@pytest.fixture
async def diagnostic_with_samples(db_session, building_1965, admin_user):
    """Create a diagnostic with a few recent samples."""
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_1965.id,
        diagnostic_type="asbestos",
        status="completed",
        diagnostician_id=admin_user.id,
    )
    db_session.add(diag)
    await db_session.flush()

    samples = []
    for i, pollutant in enumerate(["asbestos", "pcb"]):
        s = Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number=f"S-{i + 1}",
            location_floor="-1",
            pollutant_type=pollutant,
            created_at=datetime.now(UTC),
        )
        db_session.add(s)
        samples.append(s)
    await db_session.commit()
    return diag, samples


@pytest.fixture
async def old_diagnostic(db_session, building_1965, admin_user):
    """Create a diagnostic with outdated samples (>3 years)."""
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_1965.id,
        diagnostic_type="asbestos",
        status="completed",
        diagnostician_id=admin_user.id,
    )
    db_session.add(diag)
    await db_session.flush()

    old_date = datetime.now(UTC) - timedelta(days=SAMPLE_MAX_AGE_YEARS * 365 + 30)
    s = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S-OLD-1",
        location_floor="1",
        pollutant_type="asbestos",
        created_at=old_date,
    )
    db_session.add(s)
    await db_session.commit()
    return diag, [s]


@pytest.fixture
async def org_with_buildings(db_session, admin_user, building_1965):
    """Create an org with admin_user as member, linked to building_1965."""
    org = Organization(
        id=uuid.uuid4(),
        name="Test Org",
        type="property_management",
    )
    db_session.add(org)
    await db_session.flush()

    admin_user.organization_id = org.id
    await db_session.commit()
    await db_session.refresh(org)
    return org


# ---------------------------------------------------------------------------
# Unit tests: helpers
# ---------------------------------------------------------------------------


class TestApplicablePollutants:
    def test_pre_1970_all_pollutants(self):
        result = _applicable_pollutants(1965)
        assert "asbestos" in result
        assert "pcb" in result
        assert "lead" in result
        assert "hap" in result
        assert "radon" in result

    def test_post_1990_no_asbestos(self):
        result = _applicable_pollutants(2000)
        assert "asbestos" not in result
        assert "pcb" not in result

    def test_none_year_all_pollutants(self):
        result = _applicable_pollutants(None)
        assert len(result) == 5

    def test_1980_has_asbestos_no_pcb(self):
        result = _applicable_pollutants(1980)
        assert "asbestos" in result
        assert "pcb" not in result


class TestIsSampleOutdated:
    def test_recent_sample_not_outdated(self):
        s = Sample(
            id=uuid.uuid4(),
            diagnostic_id=uuid.uuid4(),
            sample_number="X",
            created_at=datetime.now(UTC),
        )
        assert _is_sample_outdated(s) is False

    def test_old_sample_outdated(self):
        s = Sample(
            id=uuid.uuid4(),
            diagnostic_id=uuid.uuid4(),
            sample_number="X",
            created_at=datetime.now(UTC) - timedelta(days=SAMPLE_MAX_AGE_YEARS * 365 + 1),
        )
        assert _is_sample_outdated(s) is True

    def test_none_created_at_outdated(self):
        s = Sample(
            id=uuid.uuid4(),
            diagnostic_id=uuid.uuid4(),
            sample_number="X",
            created_at=None,
        )
        assert _is_sample_outdated(s) is True


# ---------------------------------------------------------------------------
# Service tests: optimize_sampling_plan
# ---------------------------------------------------------------------------


class TestOptimizeSamplingPlan:
    @pytest.mark.asyncio
    async def test_nonexistent_building(self, db_session):
        result = await optimize_sampling_plan(db_session, uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_building_no_zones_no_samples(self, db_session, building_1965):
        result = await optimize_sampling_plan(db_session, building_1965.id)
        assert result is not None
        assert result.building_id == building_1965.id
        assert result.total_zones == 0
        assert result.recommended_samples == []

    @pytest.mark.asyncio
    async def test_zones_without_samples(self, db_session, building_1965, zones_for_building):
        result = await optimize_sampling_plan(db_session, building_1965.id)
        assert result is not None
        assert result.zones_needing_samples == 3
        assert len(result.recommended_samples) > 0
        # All 5 pollutants applicable for 1965 building, 3 zones => up to 15 recommendations
        pollutant_types = {r.pollutant_type for r in result.recommended_samples}
        assert "asbestos" in pollutant_types

    @pytest.mark.asyncio
    async def test_partial_sampling_reduces_recommendations(
        self, db_session, building_1965, zones_for_building, diagnostic_with_samples
    ):
        result = await optimize_sampling_plan(db_session, building_1965.id)
        assert result is not None
        # basement (floor -1) has asbestos and pcb samples, so fewer recs for that zone
        basement_recs = [r for r in result.recommended_samples if r.zone_name == "Sous-sol"]
        basement_pollutants = {r.pollutant_type for r in basement_recs}
        # asbestos and pcb are already sampled for floor -1
        assert "asbestos" not in basement_pollutants
        assert "pcb" not in basement_pollutants

    @pytest.mark.asyncio
    async def test_cost_calculated(self, db_session, building_1965, zones_for_building):
        result = await optimize_sampling_plan(db_session, building_1965.id)
        assert result.total_estimated_cost_chf > 0

    @pytest.mark.asyncio
    async def test_high_risk_zones_prioritized(self, db_session, building_1965, zones_for_building):
        result = await optimize_sampling_plan(db_session, building_1965.id)
        # basement and staircase are high-risk for 1965 building
        high_priority = [r for r in result.recommended_samples if r.priority == "high"]
        assert len(high_priority) > 0


# ---------------------------------------------------------------------------
# Service tests: estimate_sampling_cost
# ---------------------------------------------------------------------------


class TestEstimateSamplingCost:
    @pytest.mark.asyncio
    async def test_nonexistent_building(self, db_session):
        result = await estimate_sampling_cost(db_session, uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_cost_breakdown(self, db_session, building_1965, zones_for_building):
        result = await estimate_sampling_cost(db_session, building_1965.id)
        assert result is not None
        assert result.total_samples > 0
        assert result.total_cost_chf > 0
        assert result.lab_turnaround_days == LAB_TURNAROUND_DAYS
        assert len(result.pollutant_breakdown) > 0
        # Verify cost consistency
        computed = sum(pb.total_chf for pb in result.pollutant_breakdown)
        assert abs(computed - result.total_cost_chf) < 0.01

    @pytest.mark.asyncio
    async def test_no_zones_zero_cost(self, db_session, building_1965):
        result = await estimate_sampling_cost(db_session, building_1965.id)
        assert result is not None
        assert result.total_cost_chf == 0.0


# ---------------------------------------------------------------------------
# Service tests: evaluate_sampling_adequacy
# ---------------------------------------------------------------------------


class TestEvaluateSamplingAdequacy:
    @pytest.mark.asyncio
    async def test_nonexistent_building(self, db_session):
        result = await evaluate_sampling_adequacy(db_session, uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_no_samples_not_adequate(self, db_session, building_1965, zones_for_building):
        result = await evaluate_sampling_adequacy(db_session, building_1965.id)
        assert result is not None
        assert result.is_adequate is False
        assert result.confidence_level < 1.0
        assert result.recommended_additional_samples > 0

    @pytest.mark.asyncio
    async def test_pollutant_adequacy_listed(self, db_session, building_1965, zones_for_building):
        result = await evaluate_sampling_adequacy(db_session, building_1965.id)
        pollutant_names = {pa.pollutant_type for pa in result.pollutant_adequacy}
        assert "asbestos" in pollutant_names

    @pytest.mark.asyncio
    async def test_outdated_samples_not_counted(self, db_session, building_1965, zones_for_building, old_diagnostic):
        result = await evaluate_sampling_adequacy(db_session, building_1965.id)
        # Old sample should not contribute to adequacy
        assert result.is_adequate is False

    @pytest.mark.asyncio
    async def test_no_zones_zero_coverage(self, db_session, building_1965):
        result = await evaluate_sampling_adequacy(db_session, building_1965.id)
        assert result is not None
        assert result.overall_coverage_pct == 0.0


# ---------------------------------------------------------------------------
# Service tests: get_portfolio_sampling_status
# ---------------------------------------------------------------------------


class TestPortfolioSamplingStatus:
    @pytest.mark.asyncio
    async def test_nonexistent_org_empty(self, db_session):
        result = await get_portfolio_sampling_status(db_session, uuid.uuid4())
        assert result is not None
        assert result.total_buildings == 0

    @pytest.mark.asyncio
    async def test_org_with_building(self, db_session, org_with_buildings, building_1965, zones_for_building):
        result = await get_portfolio_sampling_status(db_session, org_with_buildings.id)
        assert result is not None
        assert result.total_buildings == 1
        assert result.buildings_needing_resampling == 1
        assert len(result.priority_queue) == 1
        assert result.priority_queue[0].building_id == building_1965.id


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------


class TestSampleOptimizationAPI:
    @pytest.mark.asyncio
    async def test_optimization_endpoint(self, client, auth_headers, building_1965, zones_for_building):
        resp = await client.get(
            f"/api/v1/buildings/{building_1965.id}/sampling-optimization",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["building_id"] == str(building_1965.id)
        assert "recommended_samples" in data

    @pytest.mark.asyncio
    async def test_optimization_404(self, client, auth_headers):
        resp = await client.get(
            f"/api/v1/buildings/{uuid.uuid4()}/sampling-optimization",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_cost_endpoint(self, client, auth_headers, building_1965, zones_for_building):
        resp = await client.get(
            f"/api/v1/buildings/{building_1965.id}/sampling-cost",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_cost_chf" in data
        assert "pollutant_breakdown" in data

    @pytest.mark.asyncio
    async def test_adequacy_endpoint(self, client, auth_headers, building_1965, zones_for_building):
        resp = await client.get(
            f"/api/v1/buildings/{building_1965.id}/sampling-adequacy",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "is_adequate" in data
        assert "confidence_level" in data

    @pytest.mark.asyncio
    async def test_portfolio_endpoint(self, client, auth_headers, org_with_buildings, zones_for_building):
        resp = await client.get(
            f"/api/v1/organizations/{org_with_buildings.id}/sampling-status",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_buildings"] == 1

    @pytest.mark.asyncio
    async def test_unauthenticated_rejected(self, client, building_1965):
        resp = await client.get(
            f"/api/v1/buildings/{building_1965.id}/sampling-optimization",
        )
        assert resp.status_code == 401
