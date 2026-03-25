"""Tests for the Ventilation Assessment service and API."""

import uuid

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.services.ventilation_assessment_service import (
    RADON_LIMIT_BQ_M3,
    RADON_REFERENCE_BQ_M3,
    _radon_priority,
    _sample_location,
    _select_radon_mitigation,
    assess_ventilation_needs,
    evaluate_radon_ventilation,
    get_air_quality_monitoring_plan,
    get_portfolio_ventilation_status,
)

# ---------------------------------------------------------------------------
# Pure logic unit tests
# ---------------------------------------------------------------------------


class TestRadonPriority:
    def test_critical_above_limit(self):
        assert _radon_priority(1500.0) == "critical"

    def test_critical_at_limit(self):
        assert _radon_priority(1000.0) == "critical"

    def test_high_above_600(self):
        assert _radon_priority(700.0) == "high"

    def test_medium_above_reference(self):
        assert _radon_priority(400.0) == "medium"

    def test_low_below_reference(self):
        assert _radon_priority(100.0) == "low"


class TestSelectRadonMitigation:
    def test_above_limit_gets_sub_slab(self):
        assert _select_radon_mitigation(1200.0) == "sub_slab_depressurization"

    def test_above_600_gets_combined(self):
        assert _select_radon_mitigation(700.0) == "combined"

    def test_above_reference_gets_forced(self):
        assert _select_radon_mitigation(400.0) == "forced_ventilation"


class TestSampleLocation:
    def test_full_location(self):
        s = type("S", (), {"location_floor": "RdC", "location_room": "Salon", "location_detail": "Mur nord"})()
        assert _sample_location(s) == "RdC / Salon / Mur nord"

    def test_partial_location(self):
        s = type("S", (), {"location_floor": "1er", "location_room": None, "location_detail": "Plafond"})()
        assert _sample_location(s) == "1er / Plafond"

    def test_empty_location(self):
        s = type("S", (), {"location_floor": None, "location_room": None, "location_detail": None})()
        assert _sample_location(s) == "Unknown location"


class TestConstants:
    def test_radon_reference(self):
        assert RADON_REFERENCE_BQ_M3 == 300.0

    def test_radon_limit(self):
        assert RADON_LIMIT_BQ_M3 == 1000.0


# ---------------------------------------------------------------------------
# Async DB tests
# ---------------------------------------------------------------------------


@pytest.fixture
async def _org(db_session):
    org = Organization(
        id=uuid.uuid4(),
        name="TestOrg",
        type="property_management",
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def _owner(db_session, _org):
    from tests.conftest import _HASH_OWNER

    user = User(
        id=uuid.uuid4(),
        email="vent-owner@test.ch",
        password_hash=_HASH_OWNER,
        first_name="Owner",
        last_name="Vent",
        role="owner",
        is_active=True,
        language="fr",
        organization_id=_org.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def _building(db_session, _owner):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Ventilation 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=_owner.id,
        owner_id=_owner.id,
        status="active",
    )
    db_session.add(b)
    await db_session.commit()
    await db_session.refresh(b)
    return b


@pytest.fixture
async def _diagnostic(db_session, _building, admin_user):
    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=_building.id,
        diagnostic_type="full",
        status="completed",
        diagnostician_id=admin_user.id,
    )
    db_session.add(d)
    await db_session.commit()
    await db_session.refresh(d)
    return d


@pytest.fixture
async def _radon_sample_high(db_session, _diagnostic):
    s = Sample(
        id=uuid.uuid4(),
        diagnostic_id=_diagnostic.id,
        sample_number="R-001",
        location_floor="Sous-sol",
        location_room="Cave",
        pollutant_type="radon",
        concentration=1200.0,
        unit="Bq/m3",
        threshold_exceeded=True,
        risk_level="critical",
    )
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)
    return s


@pytest.fixture
async def _radon_sample_medium(db_session, _diagnostic):
    s = Sample(
        id=uuid.uuid4(),
        diagnostic_id=_diagnostic.id,
        sample_number="R-002",
        location_floor="RdC",
        location_room="Salon",
        pollutant_type="radon",
        concentration=450.0,
        unit="Bq/m3",
        threshold_exceeded=True,
        risk_level="high",
    )
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)
    return s


@pytest.fixture
async def _asbestos_sample(db_session, _diagnostic):
    s = Sample(
        id=uuid.uuid4(),
        diagnostic_id=_diagnostic.id,
        sample_number="A-001",
        location_floor="1er",
        location_room="Corridor",
        pollutant_type="asbestos",
        concentration=None,
        threshold_exceeded=True,
        risk_level="high",
        material_category="flocage",
    )
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)
    return s


@pytest.fixture
async def _pcb_sample(db_session, _diagnostic):
    s = Sample(
        id=uuid.uuid4(),
        diagnostic_id=_diagnostic.id,
        sample_number="P-001",
        location_floor="2ème",
        location_room="Bureau",
        pollutant_type="pcb",
        concentration=120.0,
        unit="mg/kg",
        threshold_exceeded=True,
        risk_level="high",
    )
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)
    return s


# ---------------------------------------------------------------------------
# FN1: assess_ventilation_needs
# ---------------------------------------------------------------------------


class TestAssessVentilationNeeds:
    @pytest.mark.asyncio
    async def test_empty_building(self, db_session, _building):
        result = await assess_ventilation_needs(db_session, _building.id)
        assert result.building_id == _building.id
        assert result.requirements == []
        assert result.zones_needing_upgrade == 0

    @pytest.mark.asyncio
    async def test_nonexistent_building(self, db_session):
        result = await assess_ventilation_needs(db_session, uuid.uuid4())
        assert result.requirements == []
        assert result.total_zones_assessed == 0

    @pytest.mark.asyncio
    async def test_radon_high_requires_forced(self, db_session, _building, _diagnostic, _radon_sample_high):
        result = await assess_ventilation_needs(db_session, _building.id)
        assert len(result.requirements) == 1
        req = result.requirements[0]
        assert req.pollutant_type == "radon"
        assert req.ventilation_type == "forced"
        assert req.air_changes_per_hour == 1.0
        assert req.monitoring_frequency == "weekly"

    @pytest.mark.asyncio
    async def test_radon_medium_requires_forced(self, db_session, _building, _diagnostic, _radon_sample_medium):
        result = await assess_ventilation_needs(db_session, _building.id)
        assert len(result.requirements) == 1
        req = result.requirements[0]
        assert req.ventilation_type == "forced"
        assert req.air_changes_per_hour == 0.5
        assert req.monitoring_frequency == "monthly"

    @pytest.mark.asyncio
    async def test_asbestos_requires_negative_pressure(self, db_session, _building, _diagnostic, _asbestos_sample):
        result = await assess_ventilation_needs(db_session, _building.id)
        assert len(result.requirements) == 1
        req = result.requirements[0]
        assert req.pollutant_type == "asbestos"
        assert req.ventilation_type == "negative_pressure"
        assert req.filtration == "HEPA"
        assert req.monitoring_frequency == "continuous"

    @pytest.mark.asyncio
    async def test_pcb_requires_forced_with_carbon(self, db_session, _building, _diagnostic, _pcb_sample):
        result = await assess_ventilation_needs(db_session, _building.id)
        assert len(result.requirements) == 1
        req = result.requirements[0]
        assert req.pollutant_type == "pcb"
        assert req.ventilation_type == "forced"
        assert req.filtration == "activated_carbon"

    @pytest.mark.asyncio
    async def test_multiple_pollutants(
        self, db_session, _building, _diagnostic, _radon_sample_high, _asbestos_sample, _pcb_sample
    ):
        result = await assess_ventilation_needs(db_session, _building.id)
        assert len(result.requirements) == 3
        types = {r.pollutant_type for r in result.requirements}
        assert types == {"radon", "asbestos", "pcb"}


# ---------------------------------------------------------------------------
# FN2: evaluate_radon_ventilation
# ---------------------------------------------------------------------------


class TestEvaluateRadonVentilation:
    @pytest.mark.asyncio
    async def test_no_radon(self, db_session, _building, _diagnostic):
        result = await evaluate_radon_ventilation(db_session, _building.id)
        assert result.total_zones_measured == 0
        assert result.zones_above_reference == 0
        assert result.recommendations == []

    @pytest.mark.asyncio
    async def test_nonexistent_building(self, db_session):
        result = await evaluate_radon_ventilation(db_session, uuid.uuid4())
        assert result.total_zones_measured == 0

    @pytest.mark.asyncio
    async def test_high_radon_sub_slab(self, db_session, _building, _diagnostic, _radon_sample_high):
        result = await evaluate_radon_ventilation(db_session, _building.id)
        assert result.zones_above_limit == 1
        assert result.zones_above_reference == 1
        assert len(result.recommendations) == 1
        rec = result.recommendations[0]
        assert rec.mitigation_method == "sub_slab_depressurization"
        assert rec.priority == "critical"
        assert rec.expected_reduction_pct == 80.0
        assert rec.estimated_cost_chf == 8000.0

    @pytest.mark.asyncio
    async def test_medium_radon_forced_ventilation(self, db_session, _building, _diagnostic, _radon_sample_medium):
        result = await evaluate_radon_ventilation(db_session, _building.id)
        assert result.zones_above_reference == 1
        assert result.zones_above_limit == 0
        rec = result.recommendations[0]
        assert rec.mitigation_method == "forced_ventilation"
        assert rec.priority == "medium"

    @pytest.mark.asyncio
    async def test_total_cost_multiple_zones(
        self, db_session, _building, _diagnostic, _radon_sample_high, _radon_sample_medium
    ):
        result = await evaluate_radon_ventilation(db_session, _building.id)
        assert len(result.recommendations) == 2
        assert result.total_estimated_cost_chf == 8000.0 + 3500.0


# ---------------------------------------------------------------------------
# FN3: get_air_quality_monitoring_plan
# ---------------------------------------------------------------------------


class TestAirQualityMonitoringPlan:
    @pytest.mark.asyncio
    async def test_empty_building(self, db_session, _building):
        result = await get_air_quality_monitoring_plan(db_session, _building.id)
        assert result.total_points == 0
        assert result.during_works is False
        assert result.post_remediation is False

    @pytest.mark.asyncio
    async def test_nonexistent_building(self, db_session):
        result = await get_air_quality_monitoring_plan(db_session, uuid.uuid4())
        assert result.total_points == 0

    @pytest.mark.asyncio
    async def test_asbestos_monitoring(self, db_session, _building, _diagnostic, _asbestos_sample):
        result = await get_air_quality_monitoring_plan(db_session, _building.id)
        assert result.total_points == 1
        assert result.during_works is True
        assert result.post_remediation is True
        point = result.monitoring_points[0]
        assert point.parameter == "fiber_count"
        assert point.frequency == "continuous"

    @pytest.mark.asyncio
    async def test_radon_monitoring(self, db_session, _building, _diagnostic, _radon_sample_high):
        result = await get_air_quality_monitoring_plan(db_session, _building.id)
        assert result.total_points == 1
        assert result.post_remediation is True
        point = result.monitoring_points[0]
        assert point.parameter == "radon_level"
        assert point.threshold_value == 300.0
        assert point.alarm_trigger == 1000.0

    @pytest.mark.asyncio
    async def test_multiple_pollutants_monitoring(
        self, db_session, _building, _diagnostic, _asbestos_sample, _pcb_sample, _radon_sample_medium
    ):
        result = await get_air_quality_monitoring_plan(db_session, _building.id)
        assert result.total_points == 3
        params = {p.parameter for p in result.monitoring_points}
        assert "fiber_count" in params
        assert "pcb_concentration" in params
        assert "radon_level" in params
        assert result.during_works is True
        assert result.estimated_duration_days >= 30


# ---------------------------------------------------------------------------
# FN4: get_portfolio_ventilation_status
# ---------------------------------------------------------------------------


class TestPortfolioVentilationStatus:
    @pytest.mark.asyncio
    async def test_empty_org(self, db_session, _org):
        # Create org with no buildings
        empty_org = Organization(
            id=uuid.uuid4(),
            name="EmptyOrg",
            type="property_management",
        )
        db_session.add(empty_org)
        await db_session.commit()
        result = await get_portfolio_ventilation_status(db_session, empty_org.id)
        assert result.total_buildings == 0
        assert result.orap_compliance_rate == 1.0

    @pytest.mark.asyncio
    async def test_building_with_radon(self, db_session, _org, _owner, _building, _diagnostic, _radon_sample_high):
        result = await get_portfolio_ventilation_status(db_session, _org.id)
        assert result.total_buildings == 1
        assert result.buildings_needing_upgrade == 1
        assert result.orap_compliance_rate == 0.0
        assert len(result.radon_mitigation_priority_list) == 1
        status = result.radon_mitigation_priority_list[0]
        assert status.radon_priority == "critical"
        assert status.orap_compliant is False

    @pytest.mark.asyncio
    async def test_compliant_building(self, db_session, _org, _owner, _building):
        result = await get_portfolio_ventilation_status(db_session, _org.id)
        assert result.total_buildings == 1
        assert result.buildings_needing_upgrade == 0
        assert result.orap_compliance_rate == 1.0


# ---------------------------------------------------------------------------
# API integration tests
# ---------------------------------------------------------------------------


class TestVentilationAPI:
    @pytest.mark.asyncio
    async def test_ventilation_assessment_endpoint(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/ventilation-assessment",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["building_id"] == str(sample_building.id)
        assert "requirements" in data
        assert "zones_needing_upgrade" in data

    @pytest.mark.asyncio
    async def test_radon_ventilation_endpoint(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/radon-ventilation",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["building_id"] == str(sample_building.id)
        assert "recommendations" in data
        assert "total_estimated_cost_chf" in data

    @pytest.mark.asyncio
    async def test_air_quality_monitoring_endpoint(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/air-quality-monitoring",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["building_id"] == str(sample_building.id)
        assert "monitoring_points" in data

    @pytest.mark.asyncio
    async def test_portfolio_ventilation_endpoint(self, client, auth_headers):
        org_id = uuid.uuid4()
        resp = await client.get(
            f"/api/v1/organizations/{org_id}/ventilation-status",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["organization_id"] == str(org_id)

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_403(self, client, sample_building):
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/ventilation-assessment",
        )
        assert resp.status_code == 401
