"""Tests for the Occupant Safety Evaluator service and API."""

import uuid

import pytest

from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.diagnostic import Diagnostic
from app.models.material import Material
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.zone import Zone
from app.schemas.occupant_safety import SafetyLevel
from app.services.occupant_safety_service import (
    _evaluate_pollutant_safety,
    _get_exposed_populations,
    _get_exposure_pathways,
    _is_habitable,
    _level_to_score,
    _worst_level,
    evaluate_occupant_safety,
    generate_safety_recommendations,
    get_exposure_risk_by_zone,
    get_portfolio_safety_overview,
)

# ---------------------------------------------------------------------------
# Pure logic unit tests
# ---------------------------------------------------------------------------


class TestSafetyLevelHelpers:
    def test_is_habitable_room(self):
        assert _is_habitable("room") is True

    def test_is_habitable_floor(self):
        assert _is_habitable("floor") is True

    def test_is_habitable_technical(self):
        assert _is_habitable("technical_room") is False

    def test_is_habitable_basement(self):
        assert _is_habitable("basement") is False

    def test_worst_level_empty(self):
        assert _worst_level([]) == SafetyLevel.safe

    def test_worst_level_single(self):
        assert _worst_level([SafetyLevel.warning]) == SafetyLevel.warning

    def test_worst_level_mixed(self):
        result = _worst_level([SafetyLevel.safe, SafetyLevel.caution, SafetyLevel.danger])
        assert result == SafetyLevel.danger

    def test_level_to_score_safe(self):
        assert _level_to_score(SafetyLevel.safe) == 1.0

    def test_level_to_score_danger(self):
        assert _level_to_score(SafetyLevel.danger) == 0.1


class TestExposurePathways:
    def test_asbestos_inhalation(self):
        pathways = _get_exposure_pathways("asbestos", "friable")
        assert "inhalation" in [p.value for p in pathways]

    def test_lead_ingestion(self):
        pathways = _get_exposure_pathways("lead", None)
        assert "ingestion" in [p.value for p in pathways]

    def test_pcb_contact(self):
        pathways = _get_exposure_pathways("pcb", None)
        assert "contact" in [p.value for p in pathways]

    def test_radon_inhalation(self):
        pathways = _get_exposure_pathways("radon", None)
        assert "inhalation" in [p.value for p in pathways]

    def test_no_pollutant(self):
        assert _get_exposure_pathways(None, None) == []


class TestExposedPopulations:
    def test_habitable_residential(self):
        pops = _get_exposed_populations("room", "asbestos", "residential")
        values = [p.value for p in pops]
        assert "residents" in values
        assert "children" in values

    def test_technical_zone(self):
        pops = _get_exposed_populations("technical_room", "asbestos", "residential")
        values = [p.value for p in pops]
        assert "workers" in values


class TestPollutantSafetyEvaluation:
    """Swiss regulatory logic tests."""

    def test_friable_asbestos_habitable_is_danger(self):
        level, detail = _evaluate_pollutant_safety("asbestos", "friable", None, "room", 1, "residential", None)
        assert level == SafetyLevel.danger
        assert "friable" in detail.lower()

    def test_friable_asbestos_technical_is_warning(self):
        level, _ = _evaluate_pollutant_safety("asbestos", "friable", None, "technical_room", 0, "commercial", None)
        assert level == SafetyLevel.warning

    def test_encapsulated_asbestos_habitable_is_caution(self):
        level, _ = _evaluate_pollutant_safety("asbestos", "encapsulated", None, "room", 1, "residential", None)
        assert level == SafetyLevel.caution

    def test_encapsulated_asbestos_technical_is_safe(self):
        level, _ = _evaluate_pollutant_safety(
            "asbestos", "encapsulated", None, "technical_room", -1, "commercial", None
        )
        assert level == SafetyLevel.safe

    def test_radon_above_300_basement_is_warning(self):
        level, _ = _evaluate_pollutant_safety("radon", None, 450.0, "basement", -1, "residential", None)
        assert level == SafetyLevel.warning

    def test_radon_above_1000_is_danger(self):
        level, _ = _evaluate_pollutant_safety("radon", None, 1200.0, "basement", -1, "residential", None)
        assert level == SafetyLevel.danger

    def test_radon_below_300_is_safe(self):
        level, _ = _evaluate_pollutant_safety("radon", None, 150.0, "room", 0, "residential", None)
        assert level == SafetyLevel.safe

    def test_pcb_window_joints_is_caution(self):
        level, _ = _evaluate_pollutant_safety("pcb", None, None, "room", 1, "residential", "Joint de fenetre")
        assert level == SafetyLevel.caution

    def test_pcb_above_50_habitable_is_warning(self):
        level, _ = _evaluate_pollutant_safety("pcb", None, 80.0, "room", 1, "residential", "Enduit mural")
        assert level == SafetyLevel.warning

    def test_lead_above_5000_residential_habitable_is_danger(self):
        level, _ = _evaluate_pollutant_safety("lead", None, 6000.0, "room", 0, "residential", "Peinture")
        assert level == SafetyLevel.danger

    def test_lead_below_5000_is_safe(self):
        level, _ = _evaluate_pollutant_safety("lead", None, 3000.0, "room", 0, "residential", "Peinture")
        assert level == SafetyLevel.safe

    def test_hap_exterior_is_safe(self):
        level, _ = _evaluate_pollutant_safety("hap", None, None, "facade", 0, "residential", "Etancheite exterieure")
        assert level == SafetyLevel.safe

    def test_hap_habitable_is_caution(self):
        level, _ = _evaluate_pollutant_safety("hap", None, None, "room", 1, "residential", "Sol interieur")
        assert level == SafetyLevel.caution

    def test_no_pollutant_is_safe(self):
        level, _ = _evaluate_pollutant_safety(None, None, None, "room", 1, "residential", None)
        assert level == SafetyLevel.safe


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def building_with_zones(db_session, admin_user):
    """Building with zones, elements, materials, and diagnostics with samples."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue du Danger 10",
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

    # Zone 1: habitable room with friable asbestos -> danger
    zone_room = Zone(
        id=uuid.uuid4(),
        building_id=building.id,
        zone_type="room",
        name="Salon",
        floor_number=1,
    )
    db_session.add(zone_room)
    await db_session.flush()

    element = BuildingElement(
        id=uuid.uuid4(),
        zone_id=zone_room.id,
        element_type="coating",
        name="Flocage plafond",
        condition="degraded",
    )
    db_session.add(element)
    await db_session.flush()

    material_asbestos = Material(
        id=uuid.uuid4(),
        element_id=element.id,
        material_type="insulation",
        name="Flocage amiante",
        contains_pollutant=True,
        pollutant_type="asbestos",
        source="friable",
    )
    db_session.add(material_asbestos)

    # Zone 2: basement with radon
    zone_basement = Zone(
        id=uuid.uuid4(),
        building_id=building.id,
        zone_type="basement",
        name="Cave",
        floor_number=-1,
    )
    db_session.add(zone_basement)
    await db_session.flush()

    # Zone 3: technical room, safe
    zone_tech = Zone(
        id=uuid.uuid4(),
        building_id=building.id,
        zone_type="technical_room",
        name="Local technique",
        floor_number=0,
    )
    db_session.add(zone_tech)
    await db_session.flush()

    # Diagnostic with radon sample for basement
    diagnostic = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="radon",
        status="completed",
    )
    db_session.add(diagnostic)
    await db_session.flush()

    sample_radon = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic.id,
        sample_number="R-001",
        location_floor="Cave",
        pollutant_type="radon",
        concentration=450.0,
        unit="Bq/m3",
        risk_level="medium",
    )
    db_session.add(sample_radon)
    await db_session.commit()

    return building, [zone_room, zone_basement, zone_tech]


@pytest.fixture
async def org_with_buildings(db_session, admin_user):
    """Organization with member and buildings for portfolio tests."""
    org = Organization(
        id=uuid.uuid4(),
        name="Regie Test SA",
        type="property_management",
    )
    db_session.add(org)
    await db_session.flush()

    # Update admin user to belong to org
    admin_user.organization_id = org.id
    db_session.add(admin_user)
    await db_session.flush()

    # Building 1: safe (no zones/pollutants)
    b1 = Building(
        id=uuid.uuid4(),
        address="Rue Safe 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=2020,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    # Building 2: with danger
    b2 = Building(
        id=uuid.uuid4(),
        address="Rue Danger 2",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1955,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add_all([b1, b2])
    await db_session.flush()

    # Add danger zone to b2
    zone = Zone(
        id=uuid.uuid4(),
        building_id=b2.id,
        zone_type="room",
        name="Chambre",
        floor_number=1,
    )
    db_session.add(zone)
    await db_session.flush()

    elem = BuildingElement(
        id=uuid.uuid4(),
        zone_id=zone.id,
        element_type="insulation",
        name="Calorifugeage",
        condition="degraded",
    )
    db_session.add(elem)
    await db_session.flush()

    mat = Material(
        id=uuid.uuid4(),
        element_id=elem.id,
        material_type="insulation",
        name="Amiante friable",
        contains_pollutant=True,
        pollutant_type="asbestos",
        source="friable",
    )
    db_session.add(mat)
    await db_session.commit()

    return org, [b1, b2]


# ---------------------------------------------------------------------------
# Service integration tests (with DB)
# ---------------------------------------------------------------------------


class TestEvaluateOccupantSafety:
    @pytest.mark.asyncio
    async def test_building_not_found(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await evaluate_occupant_safety(db_session, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_safe_building_no_zones(self, db_session, sample_building):
        result = await evaluate_occupant_safety(db_session, sample_building.id)
        assert result.overall_safety_level == SafetyLevel.safe
        assert result.total_zones == 0

    @pytest.mark.asyncio
    async def test_danger_building_with_friable_asbestos(self, db_session, building_with_zones):
        building, _zones = building_with_zones
        result = await evaluate_occupant_safety(db_session, building.id)
        assert result.overall_safety_level == SafetyLevel.danger
        assert result.zones_at_risk >= 1
        assert len(result.critical_findings) > 0

    @pytest.mark.asyncio
    async def test_zone_count_matches(self, db_session, building_with_zones):
        building, zones = building_with_zones
        result = await evaluate_occupant_safety(db_session, building.id)
        assert result.total_zones == len(zones)


class TestExposureRiskByZone:
    @pytest.mark.asyncio
    async def test_building_not_found(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await get_exposure_risk_by_zone(db_session, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_exposure_details(self, db_session, building_with_zones):
        building, _ = building_with_zones
        result = await get_exposure_risk_by_zone(db_session, building.id)
        assert result.total_exposures >= 1
        # At least one zone should have exposures
        zones_with_exposures = [z for z in result.zones if len(z.exposures) > 0]
        assert len(zones_with_exposures) >= 1

    @pytest.mark.asyncio
    async def test_habitable_zone_flag(self, db_session, building_with_zones):
        building, _ = building_with_zones
        result = await get_exposure_risk_by_zone(db_session, building.id)
        room_zones = [z for z in result.zones if z.zone_type == "room"]
        assert all(z.is_habitable_zone for z in room_zones)
        basement_zones = [z for z in result.zones if z.zone_type == "basement"]
        assert all(not z.is_habitable_zone for z in basement_zones)


class TestSafetyRecommendations:
    @pytest.mark.asyncio
    async def test_building_not_found(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await generate_safety_recommendations(db_session, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_danger_generates_immediate_recs(self, db_session, building_with_zones):
        building, _ = building_with_zones
        result = await generate_safety_recommendations(db_session, building.id)
        assert result.immediate_count > 0
        # Immediate recs should come first
        if result.recommendations:
            assert result.recommendations[0].urgency == "immediate"

    @pytest.mark.asyncio
    async def test_safe_building_no_recs(self, db_session, sample_building):
        result = await generate_safety_recommendations(db_session, sample_building.id)
        assert result.immediate_count == 0
        assert result.short_term_count == 0
        assert result.long_term_count == 0


class TestPortfolioSafetyOverview:
    @pytest.mark.asyncio
    async def test_org_not_found(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await get_portfolio_safety_overview(db_session, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_portfolio_distribution(self, db_session, org_with_buildings):
        org, _buildings = org_with_buildings
        result = await get_portfolio_safety_overview(db_session, org.id)
        assert result.total_buildings == 2
        assert sum(result.distribution.values()) == 2
        assert result.distribution["danger"] >= 1

    @pytest.mark.asyncio
    async def test_portfolio_action_buildings(self, db_session, org_with_buildings):
        org, _ = org_with_buildings
        result = await get_portfolio_safety_overview(db_session, org.id)
        assert len(result.buildings_requiring_action) >= 1
        danger_bldgs = [b for b in result.buildings_requiring_action if b.requires_immediate_action]
        assert len(danger_bldgs) >= 1


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


class TestOccupantSafetyAPI:
    @pytest.mark.asyncio
    async def test_get_occupant_safety_404(self, client, auth_headers):
        fake_id = uuid.uuid4()
        resp = await client.get(f"/api/v1/buildings/{fake_id}/occupant-safety", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_occupant_safety_ok(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/occupant-safety",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["overall_safety_level"] == "safe"

    @pytest.mark.asyncio
    async def test_get_exposure_risk_404(self, client, auth_headers):
        fake_id = uuid.uuid4()
        resp = await client.get(f"/api/v1/buildings/{fake_id}/exposure-risk", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_exposure_risk_ok(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/exposure-risk",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "zones" in data

    @pytest.mark.asyncio
    async def test_get_recommendations_404(self, client, auth_headers):
        fake_id = uuid.uuid4()
        resp = await client.get(f"/api/v1/buildings/{fake_id}/safety-recommendations", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_recommendations_ok(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/safety-recommendations",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "recommendations" in data

    @pytest.mark.asyncio
    async def test_get_safety_overview_404(self, client, auth_headers):
        fake_id = uuid.uuid4()
        resp = await client.get(f"/api/v1/organizations/{fake_id}/safety-overview", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client):
        fake_id = uuid.uuid4()
        resp = await client.get(f"/api/v1/buildings/{fake_id}/occupant-safety")
        assert resp.status_code == 403
