"""Tests for OLED waste management service and API."""

import uuid
from datetime import date

import pytest
from httpx import AsyncClient

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.zone import Zone
from app.services.waste_management_service import (
    _classify_sample,
    classify_building_waste,
    estimate_waste_volumes,
    generate_waste_plan,
    get_portfolio_waste_forecast,
)

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
async def building_with_samples(db_session, admin_user):
    """Building with diagnostic and pollutant samples."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue des Déchets 10",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1960,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.flush()

    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="full",
        status="completed",
    )
    db_session.add(diag)
    await db_session.flush()

    # Asbestos sample → special
    s1 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S001",
        pollutant_type="asbestos",
        concentration=None,
        unit=None,
        location_floor="1er",
        location_room="Salon",
        location_detail="Faux plafond",
    )
    # PCB > 50 → special
    s2 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S002",
        pollutant_type="pcb",
        concentration=120.0,
        unit="mg/kg",
        location_floor="2e",
        location_room="Cuisine",
    )
    # HAP → type_e
    s3 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S003",
        pollutant_type="hap",
        concentration=50.0,
        unit="mg/kg",
        location_floor="SS",
    )
    # Lead > 5000 → special
    s4 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S004",
        pollutant_type="lead",
        concentration=8000.0,
        unit="mg/kg",
    )
    db_session.add_all([s1, s2, s3, s4])

    # Add a zone with area for volume estimation
    zone = Zone(
        id=uuid.uuid4(),
        building_id=building.id,
        zone_type="floor",
        name="1er étage",
        surface_area_m2=100.0,
        created_by=admin_user.id,
    )
    db_session.add(zone)

    await db_session.commit()
    return building


@pytest.fixture
async def building_no_samples(db_session, admin_user):
    """Building with no diagnostics or samples."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue Propre 5",
        postal_code="1200",
        city="Genève",
        canton="GE",
        construction_year=2020,
        building_type="commercial",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.commit()
    return building


@pytest.fixture
async def org_with_buildings(db_session, admin_user, building_with_samples):
    """Organization with a member owning buildings."""
    org = Organization(
        id=uuid.uuid4(),
        name="Régie Test SA",
        type="property_management",
    )
    db_session.add(org)
    await db_session.flush()

    # Assign admin_user to org
    admin_user.organization_id = org.id
    db_session.add(admin_user)

    # Add a planned intervention
    intervention = Intervention(
        id=uuid.uuid4(),
        building_id=building_with_samples.id,
        intervention_type="remediation",
        title="Désamiantage partiel",
        status="planned",
        date_start=date(2026, 6, 1),
        created_by=admin_user.id,
    )
    db_session.add(intervention)
    await db_session.commit()
    return org


# ── Unit tests: _classify_sample ─────────────────────────────────────


class TestClassifySample:
    def test_asbestos_is_special(self):
        s = Sample(pollutant_type="asbestos", concentration=None)
        cat, basis = _classify_sample(s)
        assert cat == "special"
        assert "asbestos" in basis.lower()

    def test_amiante_is_special(self):
        s = Sample(pollutant_type="amiante", concentration=None)
        cat, _ = _classify_sample(s)
        assert cat == "special"

    def test_pcb_above_threshold_is_special(self):
        s = Sample(pollutant_type="pcb", concentration=80.0, unit="mg/kg")
        cat, basis = _classify_sample(s)
        assert cat == "special"
        assert "50" in basis

    def test_pcb_below_threshold_is_type_e(self):
        s = Sample(pollutant_type="pcb", concentration=30.0, unit="mg/kg")
        cat, _ = _classify_sample(s)
        assert cat == "type_e"

    def test_lead_above_threshold_is_special(self):
        s = Sample(pollutant_type="lead", concentration=6000.0, unit="mg/kg")
        cat, basis = _classify_sample(s)
        assert cat == "special"
        assert "5000" in basis

    def test_lead_below_threshold_is_type_e(self):
        s = Sample(pollutant_type="lead", concentration=3000.0, unit="mg/kg")
        cat, _ = _classify_sample(s)
        assert cat == "type_e"

    def test_plomb_above_threshold_is_special(self):
        s = Sample(pollutant_type="plomb", concentration=7000.0)
        cat, _ = _classify_sample(s)
        assert cat == "special"

    def test_hap_is_type_e(self):
        s = Sample(pollutant_type="hap", concentration=50.0)
        cat, _ = _classify_sample(s)
        assert cat == "type_e"

    def test_clean_material_is_type_b(self):
        s = Sample(pollutant_type=None, concentration=None)
        cat, _ = _classify_sample(s)
        assert cat == "type_b"

    def test_unknown_pollutant_is_type_b(self):
        s = Sample(pollutant_type="unknown_stuff", concentration=None)
        cat, _ = _classify_sample(s)
        assert cat == "type_b"


# ── Service tests ────────────────────────────────────────────────────


class TestClassifyBuildingWaste:
    @pytest.mark.asyncio
    async def test_classify_with_samples(self, db_session, building_with_samples):
        result = await classify_building_waste(db_session, building_with_samples.id)
        assert result.building_id == building_with_samples.id
        assert len(result.items) == 4
        assert result.summary["special"] == 3  # asbestos + pcb>50 + lead>5000
        assert result.summary["type_e"] == 1  # hap

    @pytest.mark.asyncio
    async def test_classify_no_samples(self, db_session, building_no_samples):
        result = await classify_building_waste(db_session, building_no_samples.id)
        assert result.building_id == building_no_samples.id
        assert len(result.items) == 0
        assert result.summary["type_b"] == 0

    @pytest.mark.asyncio
    async def test_classify_nonexistent_building(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await classify_building_waste(db_session, uuid.uuid4())


class TestEstimateWasteVolumes:
    @pytest.mark.asyncio
    async def test_volumes_with_zones(self, db_session, building_with_samples):
        result = await estimate_waste_volumes(db_session, building_with_samples.id)
        assert result.building_id == building_with_samples.id
        assert result.total_volume_m3 > 0
        assert result.total_weight_tons > 0
        assert len(result.estimates) > 0
        # Check all categories have correct packaging
        for est in result.estimates:
            assert est.waste_category in ("type_b", "type_e", "special")
            assert est.density_factor > 0

    @pytest.mark.asyncio
    async def test_volumes_no_zones(self, db_session, building_no_samples):
        result = await estimate_waste_volumes(db_session, building_no_samples.id)
        # Should still return a default type_b entry (0 volume since no zones)
        assert result.building_id == building_no_samples.id
        assert len(result.estimates) >= 1


class TestGenerateWastePlan:
    @pytest.mark.asyncio
    async def test_plan_with_samples(self, db_session, building_with_samples):
        result = await generate_waste_plan(db_session, building_with_samples.id)
        assert result.building_id == building_with_samples.id
        assert len(result.disposal_routes) > 0
        assert result.total_estimated_cost_chf >= 0
        assert len(result.regulatory_references) > 0

        # Should have special route for asbestos/pcb/lead
        categories = {r.waste_category for r in result.disposal_routes}
        assert "special" in categories

    @pytest.mark.asyncio
    async def test_plan_nonexistent_building(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await generate_waste_plan(db_session, uuid.uuid4())


class TestPortfolioWasteForecast:
    @pytest.mark.asyncio
    async def test_forecast_with_buildings(self, db_session, org_with_buildings):
        result = await get_portfolio_waste_forecast(db_session, org_with_buildings.id)
        assert result.organization_id == org_with_buildings.id
        assert len(result.buildings) >= 1
        assert result.total_disposal_cost_chf >= 0
        assert len(result.regulatory_filing_requirements) > 0

    @pytest.mark.asyncio
    async def test_forecast_empty_org(self, db_session):
        org = Organization(
            id=uuid.uuid4(),
            name="Empty Org",
            type="diagnostic_lab",
        )
        db_session.add(org)
        await db_session.commit()
        result = await get_portfolio_waste_forecast(db_session, org.id)
        assert result.organization_id == org.id
        assert len(result.buildings) == 0
        assert result.total_disposal_cost_chf == 0.0

    @pytest.mark.asyncio
    async def test_forecast_planned_intervention_date(self, db_session, org_with_buildings, building_with_samples):
        result = await get_portfolio_waste_forecast(db_session, org_with_buildings.id)
        bldg_entry = next(
            (b for b in result.buildings if b.building_id == building_with_samples.id),
            None,
        )
        assert bldg_entry is not None
        assert bldg_entry.planned_intervention_date == "2026-06-01"


# ── API tests ────────────────────────────────────────────────────────


class TestWasteManagementAPI:
    @pytest.mark.asyncio
    async def test_get_classification(self, client: AsyncClient, auth_headers, building_with_samples):
        resp = await client.get(
            f"/api/v1/buildings/{building_with_samples.id}/waste-classification",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["building_id"] == str(building_with_samples.id)
        assert len(data["items"]) == 4

    @pytest.mark.asyncio
    async def test_get_classification_404(self, client: AsyncClient, auth_headers):
        resp = await client.get(
            f"/api/v1/buildings/{uuid.uuid4()}/waste-classification",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_waste_plan(self, client: AsyncClient, auth_headers, building_with_samples):
        resp = await client.get(
            f"/api/v1/buildings/{building_with_samples.id}/waste-plan",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["disposal_routes"]) > 0
        assert data["total_estimated_cost_chf"] >= 0

    @pytest.mark.asyncio
    async def test_get_waste_volumes(self, client: AsyncClient, auth_headers, building_with_samples):
        resp = await client.get(
            f"/api/v1/buildings/{building_with_samples.id}/waste-volumes",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_volume_m3"] > 0

    @pytest.mark.asyncio
    async def test_get_waste_forecast(self, client: AsyncClient, auth_headers, org_with_buildings):
        resp = await client.get(
            f"/api/v1/organizations/{org_with_buildings.id}/waste-forecast",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["organization_id"] == str(org_with_buildings.id)

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient, building_with_samples):
        resp = await client.get(
            f"/api/v1/buildings/{building_with_samples.id}/waste-classification",
        )
        assert resp.status_code in (401, 403)
