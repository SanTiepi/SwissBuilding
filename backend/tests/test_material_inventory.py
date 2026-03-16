"""Tests for Material Inventory service and API."""

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.material import Material
from app.models.organization import Organization
from app.models.user import User
from app.models.zone import Zone
from app.services.material_inventory_service import (
    _age_estimate,
    _compute_risk,
    _degradation_status,
    assess_material_risk,
    get_material_inventory,
    get_material_lifecycle,
    get_portfolio_material_overview,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def org(db_session):
    org = Organization(
        id=uuid.uuid4(),
        name="Test Org",
        type="property_management",
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def org_user(db_session, org):
    from tests.conftest import _HASH_ADMIN

    user = User(
        id=uuid.uuid4(),
        email="orguser@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Org",
        last_name="User",
        role="admin",
        is_active=True,
        language="fr",
        organization_id=org.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def org_building(db_session, org_user):
    building = Building(
        id=uuid.uuid4(),
        address="Rue Org 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1960,
        building_type="residential",
        created_by=org_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def zone_floor(db_session, sample_building, admin_user):
    zone = Zone(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        zone_type="floor",
        name="1er étage",
        floor_number=1,
        created_by=admin_user.id,
    )
    db_session.add(zone)
    await db_session.commit()
    await db_session.refresh(zone)
    return zone


@pytest.fixture
async def element_wall(db_session, zone_floor, admin_user):
    elem = BuildingElement(
        id=uuid.uuid4(),
        zone_id=zone_floor.id,
        element_type="wall",
        name="Mur porteur",
        condition="fair",
        installation_year=1965,
        created_by=admin_user.id,
    )
    db_session.add(elem)
    await db_session.commit()
    await db_session.refresh(elem)
    return elem


@pytest.fixture
async def element_pipe(db_session, zone_floor, admin_user):
    elem = BuildingElement(
        id=uuid.uuid4(),
        zone_id=zone_floor.id,
        element_type="pipe",
        name="Canalisation",
        condition="poor",
        installation_year=1970,
        created_by=admin_user.id,
    )
    db_session.add(elem)
    await db_session.commit()
    await db_session.refresh(elem)
    return elem


@pytest.fixture
async def material_concrete(db_session, element_wall, admin_user):
    mat = Material(
        id=uuid.uuid4(),
        element_id=element_wall.id,
        material_type="concrete",
        name="Béton armé",
        installation_year=1965,
        contains_pollutant=False,
        created_by=admin_user.id,
    )
    db_session.add(mat)
    await db_session.commit()
    await db_session.refresh(mat)
    return mat


@pytest.fixture
async def material_insulation_asbestos(db_session, element_pipe, admin_user):
    mat = Material(
        id=uuid.uuid4(),
        element_id=element_pipe.id,
        material_type="insulation",
        name="Calorifugeage amiante",
        installation_year=1970,
        contains_pollutant=True,
        pollutant_type="asbestos",
        pollutant_confirmed=True,
        created_by=admin_user.id,
    )
    db_session.add(mat)
    await db_session.commit()
    await db_session.refresh(mat)
    return mat


@pytest.fixture
async def material_coating(db_session, element_wall, admin_user):
    mat = Material(
        id=uuid.uuid4(),
        element_id=element_wall.id,
        material_type="coating",
        name="Peinture plomb",
        installation_year=2020,
        contains_pollutant=True,
        pollutant_type="lead",
        pollutant_confirmed=False,
        created_by=admin_user.id,
    )
    db_session.add(mat)
    await db_session.commit()
    await db_session.refresh(mat)
    return mat


# ---------------------------------------------------------------------------
# Unit tests — helper functions
# ---------------------------------------------------------------------------


class TestAgeEstimate:
    def test_from_material_year(self, element_wall, material_concrete):
        age = _age_estimate(material_concrete, element_wall)
        expected = datetime.now(UTC).year - 1965
        assert age == expected

    def test_fallback_to_element_year(self, element_wall):
        mat = Material(
            id=uuid.uuid4(),
            element_id=element_wall.id,
            material_type="plaster",
            name="Test",
            installation_year=None,
        )
        age = _age_estimate(mat, element_wall)
        expected = datetime.now(UTC).year - 1965
        assert age == expected

    def test_none_when_no_year(self):
        mat = Material(
            id=uuid.uuid4(),
            element_id=uuid.uuid4(),
            material_type="plaster",
            name="Test",
            installation_year=None,
        )
        elem = BuildingElement(
            id=uuid.uuid4(),
            zone_id=uuid.uuid4(),
            element_type="wall",
            name="Test",
            installation_year=None,
        )
        assert _age_estimate(mat, elem) is None


class TestComputeRisk:
    def test_low_risk_healthy_material(self, element_wall, material_concrete):
        score, level, _factors = _compute_risk(material_concrete, element_wall)
        assert level in ("low", "medium")
        assert score > 0

    def test_high_risk_asbestos(self, element_pipe, material_insulation_asbestos):
        _score, level, factors = _compute_risk(material_insulation_asbestos, element_pipe)
        assert level in ("high", "critical")
        assert any("asbestos" in f for f in factors)
        assert any("pollutant_confirmed" in f for f in factors)

    def test_condition_factor(self):
        mat = Material(
            id=uuid.uuid4(),
            element_id=uuid.uuid4(),
            material_type="concrete",
            name="Test",
            installation_year=2020,
            contains_pollutant=False,
        )
        elem_good = BuildingElement(
            id=uuid.uuid4(),
            zone_id=uuid.uuid4(),
            element_type="wall",
            name="Test",
            condition="good",
            installation_year=2020,
        )
        elem_critical = BuildingElement(
            id=uuid.uuid4(),
            zone_id=uuid.uuid4(),
            element_type="wall",
            name="Test",
            condition="critical",
            installation_year=2020,
        )
        score_good, _, _ = _compute_risk(mat, elem_good)
        score_critical, _, _ = _compute_risk(mat, elem_critical)
        assert score_critical > score_good


class TestDegradationStatus:
    def test_healthy(self):
        assert _degradation_status(5, 40) == "healthy"

    def test_aging(self):
        assert _degradation_status(22, 40) == "aging"

    def test_degrading(self):
        assert _degradation_status(32, 40) == "degrading"

    def test_end_of_life(self):
        assert _degradation_status(45, 40) == "end_of_life"

    def test_unknown_no_age(self):
        assert _degradation_status(None, 40) == "unknown"


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_material_inventory_empty(db_session, sample_building):
    result = await get_material_inventory(db_session, sample_building.id)
    assert result.building_id == sample_building.id
    assert result.total_materials == 0
    assert result.groups == []


@pytest.mark.asyncio
async def test_get_material_inventory_grouped(
    db_session,
    sample_building,
    material_concrete,
    material_insulation_asbestos,
    material_coating,
):
    result = await get_material_inventory(db_session, sample_building.id)
    assert result.total_materials == 3
    types = {g.material_type for g in result.groups}
    assert "concrete" in types
    assert "insulation" in types
    assert "coating" in types

    insulation_group = next(g for g in result.groups if g.material_type == "insulation")
    assert insulation_group.count == 1
    assert insulation_group.pollutant_count == 1


@pytest.mark.asyncio
async def test_assess_material_risk_empty(db_session, sample_building):
    result = await assess_material_risk(db_session, sample_building.id)
    assert result.assessed_count == 0


@pytest.mark.asyncio
async def test_assess_material_risk_ordering(
    db_session,
    sample_building,
    material_concrete,
    material_insulation_asbestos,
):
    result = await assess_material_risk(db_session, sample_building.id)
    assert result.assessed_count == 2
    # Asbestos material should have higher risk, thus priority 1
    assert result.materials[0].material_id == material_insulation_asbestos.id
    assert result.materials[0].intervention_priority == 1
    assert result.materials[1].intervention_priority == 2


@pytest.mark.asyncio
async def test_assess_material_risk_counts(
    db_session,
    sample_building,
    material_concrete,
    material_insulation_asbestos,
    material_coating,
):
    result = await assess_material_risk(db_session, sample_building.id)
    assert result.assessed_count == 3
    total = result.critical_count + result.high_count + result.medium_count + result.low_count
    assert total == 3


@pytest.mark.asyncio
async def test_get_material_lifecycle_empty(db_session, sample_building):
    result = await get_material_lifecycle(db_session, sample_building.id)
    assert result.total_materials == 0


@pytest.mark.asyncio
async def test_get_material_lifecycle_with_data(
    db_session,
    sample_building,
    material_concrete,
    material_coating,
):
    result = await get_material_lifecycle(db_session, sample_building.id)
    assert result.total_materials == 2
    # Concrete from 1965 with 80y lifespan: should still be alive in 2026
    concrete_item = next(m for m in result.materials if m.material_type == "concrete")
    assert concrete_item.expected_lifespan_years == 80
    assert concrete_item.age_estimate_years is not None

    # Coating from 2020 with 15y lifespan: should be healthy
    coating_item = next(m for m in result.materials if m.material_type == "coating")
    assert coating_item.degradation_status == "healthy"
    assert coating_item.end_of_life is False


@pytest.mark.asyncio
async def test_get_portfolio_material_overview_empty(db_session, org):
    result = await get_portfolio_material_overview(db_session, org.id)
    assert result.total_buildings == 0
    assert result.total_materials == 0


@pytest.mark.asyncio
async def test_get_portfolio_material_overview_with_data(db_session, org, org_user, org_building):
    # Create zone + element + material in org building
    zone = Zone(
        id=uuid.uuid4(),
        building_id=org_building.id,
        zone_type="floor",
        name="RDC",
        created_by=org_user.id,
    )
    db_session.add(zone)
    await db_session.flush()

    elem = BuildingElement(
        id=uuid.uuid4(),
        zone_id=zone.id,
        element_type="wall",
        name="Mur",
        condition="good",
        installation_year=1960,
        created_by=org_user.id,
    )
    db_session.add(elem)
    await db_session.flush()

    mat = Material(
        id=uuid.uuid4(),
        element_id=elem.id,
        material_type="concrete",
        name="Béton",
        installation_year=1960,
        contains_pollutant=True,
        pollutant_type="asbestos",
        pollutant_confirmed=True,
        created_by=org_user.id,
    )
    db_session.add(mat)
    await db_session.commit()

    result = await get_portfolio_material_overview(db_session, org.id)
    assert result.total_buildings == 1
    assert result.total_materials == 1
    assert result.pollutant_material_count == 1
    assert result.pollutant_percentage == 100.0
    assert len(result.type_distribution) == 1
    assert result.type_distribution[0].material_type == "concrete"


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_material_inventory(
    client: AsyncClient,
    auth_headers,
    sample_building,
    material_concrete,
):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/material-inventory",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert data["total_materials"] == 1


@pytest.mark.asyncio
async def test_api_material_risk(
    client: AsyncClient,
    auth_headers,
    sample_building,
    material_concrete,
):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/material-risk",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["assessed_count"] == 1
    assert len(data["materials"]) == 1


@pytest.mark.asyncio
async def test_api_material_lifecycle(
    client: AsyncClient,
    auth_headers,
    sample_building,
    material_concrete,
):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/material-lifecycle",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_materials"] == 1


@pytest.mark.asyncio
async def test_api_portfolio_material_overview(
    client: AsyncClient,
    auth_headers,
    org,
):
    resp = await client.get(
        f"/api/v1/organizations/{org.id}/material-overview",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["organization_id"] == str(org.id)


@pytest.mark.asyncio
async def test_api_material_inventory_unauthenticated(
    client: AsyncClient,
    sample_building,
):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/material-inventory",
    )
    assert resp.status_code in (401, 403)
