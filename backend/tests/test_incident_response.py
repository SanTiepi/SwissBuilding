"""Tests for the Incident Response Service."""

import uuid

import pytest
from httpx import AsyncClient

from app.models.assignment import Assignment
from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.intervention import Intervention
from app.models.material import Material
from app.models.organization import Organization
from app.models.user import User
from app.models.zone import Zone
from app.services.incident_response_service import (
    assess_incident_probability,
    generate_incident_plan,
    get_emergency_contacts,
    get_portfolio_incident_readiness,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def org(db_session):
    o = Organization(
        id=uuid.uuid4(),
        name="Test Diag Lab",
        type="diagnostic_lab",
    )
    db_session.add(o)
    await db_session.commit()
    await db_session.refresh(o)
    return o


@pytest.fixture
async def org_user(db_session, org):
    from tests.conftest import _HASH_ADMIN

    u = User(
        id=uuid.uuid4(),
        email="org-member@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Org",
        last_name="Member",
        role="admin",
        is_active=True,
        language="fr",
        organization_id=org.id,
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest.fixture
async def building_with_zones(db_session, org_user):
    building = Building(
        id=uuid.uuid4(),
        address="Rue Incident 10",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=org_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.flush()

    zone1 = Zone(
        id=uuid.uuid4(),
        building_id=building.id,
        zone_type="room",
        name="Salon principal",
        floor_number=1,
        created_by=org_user.id,
    )
    zone2 = Zone(
        id=uuid.uuid4(),
        building_id=building.id,
        zone_type="basement",
        name="Sous-sol",
        floor_number=-1,
        created_by=org_user.id,
    )
    zone3 = Zone(
        id=uuid.uuid4(),
        building_id=building.id,
        zone_type="technical_room",
        name="Local technique",
        floor_number=0,
        created_by=org_user.id,
    )
    db_session.add_all([zone1, zone2, zone3])
    await db_session.flush()

    # Element + material with asbestos (degraded) in zone1
    elem1 = BuildingElement(
        id=uuid.uuid4(),
        zone_id=zone1.id,
        element_type="ceiling",
        name="Faux plafond",
        condition="degraded",
        created_by=org_user.id,
    )
    db_session.add(elem1)
    await db_session.flush()
    mat1 = Material(
        id=uuid.uuid4(),
        element_id=elem1.id,
        material_type="insulation",
        name="Flocage amiante",
        contains_pollutant=True,
        pollutant_type="asbestos",
        source="friable",
        created_by=org_user.id,
    )
    db_session.add(mat1)

    # Element + material with PCB in zone2
    elem2 = BuildingElement(
        id=uuid.uuid4(),
        zone_id=zone2.id,
        element_type="wall",
        name="Joint fenetre",
        condition="good",
        created_by=org_user.id,
    )
    db_session.add(elem2)
    await db_session.flush()
    mat2 = Material(
        id=uuid.uuid4(),
        element_id=elem2.id,
        material_type="sealant",
        name="Joint PCB",
        contains_pollutant=True,
        pollutant_type="pcb",
        created_by=org_user.id,
    )
    db_session.add(mat2)

    # Element in zone3 (no pollutants)
    elem3 = BuildingElement(
        id=uuid.uuid4(),
        zone_id=zone3.id,
        element_type="pipe",
        name="Conduite chauffage",
        condition="good",
        created_by=org_user.id,
    )
    db_session.add(elem3)

    await db_session.commit()
    await db_session.refresh(building)
    return building, [zone1, zone2, zone3]


@pytest.fixture
async def building_no_zones(db_session, admin_user):
    building = Building(
        id=uuid.uuid4(),
        address="Rue Vide 1",
        postal_code="1200",
        city="Geneve",
        canton="GE",
        construction_year=2000,
        building_type="commercial",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


# ---------------------------------------------------------------------------
# FN1: generate_incident_plan
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_incident_plan_with_pollutants(db_session, building_with_zones):
    building, _zones = building_with_zones
    plan = await generate_incident_plan(db_session, building.id)

    assert plan.building_id == building.id
    assert plan.canton == "VD"
    assert len(plan.scenarios) == 3  # fiber_release, spill, elevated_radon

    # Fiber release should reference asbestos zones
    fiber = next(s for s in plan.scenarios if s.scenario == "fiber_release")
    assert fiber.pollutant == "asbestos"
    assert len(fiber.immediate_actions) > 0
    assert len(fiber.evacuation_zones) > 0
    assert len(fiber.decontamination_steps) > 0
    assert len(fiber.notification_chain) > 0
    assert len(fiber.authority_reporting) > 0

    # Spill should be relevant (PCB present)
    spill = next(s for s in plan.scenarios if s.scenario == "spill")
    assert spill.pollutant == "pcb_lead"
    assert any("Sous-sol" in z for z in spill.evacuation_zones)


@pytest.mark.asyncio
async def test_generate_incident_plan_no_zones(db_session, building_no_zones):
    plan = await generate_incident_plan(db_session, building_no_zones.id)

    assert plan.building_id == building_no_zones.id
    assert len(plan.scenarios) == 3
    # All scenarios should still be generated as templates
    for scenario in plan.scenarios:
        assert len(scenario.immediate_actions) > 0


@pytest.mark.asyncio
async def test_generate_incident_plan_not_found(db_session):
    with pytest.raises(ValueError, match="not found"):
        await generate_incident_plan(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_incident_plan_scenarios_complete(db_session, building_with_zones):
    building, _ = building_with_zones
    plan = await generate_incident_plan(db_session, building.id)

    scenarios_found = {s.scenario for s in plan.scenarios}
    assert "fiber_release" in scenarios_found
    assert "spill" in scenarios_found
    assert "elevated_radon" in scenarios_found


# ---------------------------------------------------------------------------
# FN2: get_emergency_contacts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_emergency_contacts_statutory(db_session, building_with_zones):
    building, _ = building_with_zones
    contacts = await get_emergency_contacts(db_session, building.id)

    assert contacts.building_id == building.id
    roles = [c.role for c in contacts.contacts]
    assert "suva" in roles
    assert "cantonal_authority" in roles
    assert "emergency_services" in roles


@pytest.mark.asyncio
async def test_emergency_contacts_with_assignment(db_session, building_with_zones, org_user):
    building, _ = building_with_zones

    assignment = Assignment(
        id=uuid.uuid4(),
        target_type="building",
        target_id=building.id,
        user_id=org_user.id,
        role="owner_contact",
        created_by=org_user.id,
    )
    db_session.add(assignment)
    await db_session.commit()

    contacts = await get_emergency_contacts(db_session, building.id)

    owner_contacts = [c for c in contacts.contacts if c.role == "building_owner"]
    assert len(owner_contacts) >= 1
    assert any(c.name == "Org Member" for c in owner_contacts)


@pytest.mark.asyncio
async def test_emergency_contacts_fallback_creator(db_session, building_with_zones):
    building, _ = building_with_zones
    contacts = await get_emergency_contacts(db_session, building.id)

    # Creator should appear as fallback building_owner
    owner_contacts = [c for c in contacts.contacts if c.role == "building_owner"]
    assert len(owner_contacts) >= 1


@pytest.mark.asyncio
async def test_emergency_contacts_not_found(db_session):
    with pytest.raises(ValueError, match="not found"):
        await get_emergency_contacts(db_session, uuid.uuid4())


# ---------------------------------------------------------------------------
# FN3: assess_incident_probability
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_incident_probability_with_degraded_materials(db_session, building_with_zones):
    building, _zones = building_with_zones
    result = await assess_incident_probability(db_session, building.id)

    assert result.building_id == building.id
    assert result.total_zones == 3
    assert len(result.zones) == 3

    # Zone with degraded asbestos should be high/critical
    salon_zone = next(z for z in result.zones if z.zone_name == "Salon principal")
    assert salon_zone.has_degraded_material is True
    assert salon_zone.is_public_zone is True  # room is public
    assert salon_zone.risk_level in ("high", "critical")
    assert salon_zone.probability_score > 0.5


@pytest.mark.asyncio
async def test_incident_probability_clean_zone(db_session, building_with_zones):
    building, _zones = building_with_zones
    result = await assess_incident_probability(db_session, building.id)

    # Technical room with no pollutants should be low
    tech_zone = next(z for z in result.zones if z.zone_name == "Local technique")
    assert tech_zone.risk_level == "low"
    assert tech_zone.probability_score == 0.0
    assert tech_zone.pollutants_present == []


@pytest.mark.asyncio
async def test_incident_probability_sorted_by_risk(db_session, building_with_zones):
    building, _ = building_with_zones
    result = await assess_incident_probability(db_session, building.id)

    risk_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    risk_values = [risk_order[z.risk_level] for z in result.zones]
    assert risk_values == sorted(risk_values, reverse=True)


@pytest.mark.asyncio
async def test_incident_probability_with_intervention(db_session, building_with_zones, org_user):
    building, _zones = building_with_zones

    iv = Intervention(
        id=uuid.uuid4(),
        building_id=building.id,
        intervention_type="removal",
        title="Retrait amiante",
        status="in_progress",
        created_by=org_user.id,
    )
    db_session.add(iv)
    await db_session.commit()

    result = await assess_incident_probability(db_session, building.id)

    # All zones should have active intervention flag (no zones_affected = applies to all)
    for zone in result.zones:
        assert zone.has_active_intervention is True


@pytest.mark.asyncio
async def test_incident_probability_no_zones(db_session, building_no_zones):
    result = await assess_incident_probability(db_session, building_no_zones.id)

    assert result.total_zones == 0
    assert result.zones == []
    assert result.overall_risk_level == "low"
    assert result.highest_risk_zone is None


@pytest.mark.asyncio
async def test_incident_probability_not_found(db_session):
    with pytest.raises(ValueError, match="not found"):
        await assess_incident_probability(db_session, uuid.uuid4())


# ---------------------------------------------------------------------------
# FN4: get_portfolio_incident_readiness
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_portfolio_readiness_with_buildings(db_session, org, building_with_zones):
    _building, _ = building_with_zones
    result = await get_portfolio_incident_readiness(db_session, org.id)

    assert result.organization_id == org.id
    assert result.total_buildings >= 1
    assert len(result.buildings) >= 1


@pytest.mark.asyncio
async def test_portfolio_readiness_empty_org(db_session):
    empty_org = Organization(
        id=uuid.uuid4(),
        name="Empty Org",
        type="property_management",
    )
    db_session.add(empty_org)
    await db_session.commit()

    result = await get_portfolio_incident_readiness(db_session, empty_org.id)

    assert result.total_buildings == 0
    assert result.buildings == []
    assert result.coverage_gaps == []


@pytest.mark.asyncio
async def test_portfolio_readiness_empty_org_random_id(db_session):
    result = await get_portfolio_incident_readiness(db_session, uuid.uuid4())
    assert result.total_buildings == 0


@pytest.mark.asyncio
async def test_portfolio_readiness_coverage_gaps(db_session, org, org_user):
    # Create building without any pollutant data
    building = Building(
        id=uuid.uuid4(),
        address="Rue Sans Diagnostic 5",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=2010,
        building_type="commercial",
        created_by=org_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.commit()

    result = await get_portfolio_incident_readiness(db_session, org.id)

    assert result.buildings_needing_plans > 0
    assert any("sans diagnostic" in g for g in result.coverage_gaps)


# ---------------------------------------------------------------------------
# API Endpoint Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_incident_plan(client: AsyncClient, auth_headers, sample_building):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/incident-plan", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert len(data["scenarios"]) == 3


@pytest.mark.asyncio
async def test_api_incident_plan_not_found(client: AsyncClient, auth_headers):
    resp = await client.get(f"/api/v1/buildings/{uuid.uuid4()}/incident-plan", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_emergency_contacts(client: AsyncClient, auth_headers, sample_building):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/emergency-contacts", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert len(data["contacts"]) >= 3  # at least statutory contacts


@pytest.mark.asyncio
async def test_api_incident_probability(client: AsyncClient, auth_headers, sample_building):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/incident-probability", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert "zones" in data


@pytest.mark.asyncio
async def test_api_incident_probability_not_found(client: AsyncClient, auth_headers):
    resp = await client.get(f"/api/v1/buildings/{uuid.uuid4()}/incident-probability", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_unauthenticated(client: AsyncClient, sample_building):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/incident-plan")
    assert resp.status_code in (401, 403)
