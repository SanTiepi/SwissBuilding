"""Tests for carbon footprint service."""

import uuid

import pytest

from app.models.building import Building
from app.models.intervention import Intervention
from app.services.carbon_footprint_service import (
    SWISS_AVERAGE_CO2_PER_M2,
    compute_carbon_footprint,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def old_oil_building(db_session, admin_user):
    """Pre-1970 building: mazout heating, high consumption."""
    bldg = Building(
        id=uuid.uuid4(),
        address="Rue Petrole 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1960,
        building_type="residential",
        surface_area_m2=400.0,
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(bldg)
    await db_session.commit()
    await db_session.refresh(bldg)
    return bldg


@pytest.fixture
async def modern_pac_building(db_session, admin_user):
    """Post-2020 building: heat pump, low consumption."""
    bldg = Building(
        id=uuid.uuid4(),
        address="Rue Ecolo 10",
        postal_code="1200",
        city="Geneve",
        canton="GE",
        construction_year=2022,
        building_type="residential",
        surface_area_m2=250.0,
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(bldg)
    await db_session.commit()
    await db_session.refresh(bldg)
    return bldg


@pytest.fixture
async def renovated_building(db_session, admin_user):
    """1980 building with HVAC upgrade (switches to heat pump)."""
    bldg = Building(
        id=uuid.uuid4(),
        address="Rue Renovee 5",
        postal_code="3000",
        city="Bern",
        canton="BE",
        construction_year=1985,
        building_type="residential",
        surface_area_m2=300.0,
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(bldg)
    await db_session.flush()

    iv = Intervention(
        id=uuid.uuid4(),
        building_id=bldg.id,
        intervention_type="hvac_upgrade",
        title="Heat pump installation",
        status="completed",
        cost_chf=30000.0,
        created_by=admin_user.id,
    )
    db_session.add(iv)
    await db_session.commit()
    await db_session.refresh(bldg)
    return bldg


@pytest.fixture
async def building_no_year(db_session, admin_user):
    """Building with no construction year (worst-case assumption)."""
    bldg = Building(
        id=uuid.uuid4(),
        address="Rue Inconnue 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=None,
        building_type="commercial",
        surface_area_m2=200.0,
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(bldg)
    await db_session.commit()
    await db_session.refresh(bldg)
    return bldg


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_old_building_high_carbon(db_session, old_oil_building):
    """Pre-1970 mazout building should have high CO2 and poor rating."""
    result = await compute_carbon_footprint(db_session, old_oil_building.id)

    assert result["energy_source"] == "mazout"
    assert result["consumption_kwh_m2"] == 220.0  # pre_1970 base
    assert result["per_m2"] > 0
    assert result["total_kg_co2"] > 0
    assert result["rating"] in ("E", "F", "G")
    assert result["comparison_to_average"]["better_than_average"] is False


@pytest.mark.asyncio
async def test_modern_building_low_carbon(db_session, modern_pac_building):
    """Post-2020 heat pump building should have low CO2 and good rating."""
    result = await compute_carbon_footprint(db_session, modern_pac_building.id)

    assert result["energy_source"] == "pac"
    assert result["consumption_kwh_m2"] == 45.0  # post_2020 base
    assert result["per_m2"] < 5.0  # Very low CO2 with heat pump
    assert result["rating"] in ("A", "B")
    assert result["comparison_to_average"]["better_than_average"] is True


@pytest.mark.asyncio
async def test_hvac_upgrade_switches_to_pac(db_session, renovated_building):
    """HVAC upgrade should switch energy source to heat pump."""
    result = await compute_carbon_footprint(db_session, renovated_building.id)

    assert result["energy_source"] == "pac"
    # Base 160 kWh/m2 * (1 - 0.30 hvac reduction) = 112 kWh/m2
    assert result["consumption_kwh_m2"] == 112.0
    assert "hvac_upgrade" in result["interventions_applied"]


@pytest.mark.asyncio
async def test_carbon_rating_scale(db_session, old_oil_building, modern_pac_building):
    """Old building should have worse rating than modern building."""
    old_result = await compute_carbon_footprint(db_session, old_oil_building.id)
    modern_result = await compute_carbon_footprint(db_session, modern_pac_building.id)

    rating_order = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5, "G": 6}
    assert rating_order[old_result["rating"]] > rating_order[modern_result["rating"]]


@pytest.mark.asyncio
async def test_breakdown_contains_source(db_session, old_oil_building):
    """Breakdown should contain the energy source with total CO2."""
    result = await compute_carbon_footprint(db_session, old_oil_building.id)

    assert "mazout" in result["breakdown_by_source"]
    assert result["breakdown_by_source"]["mazout"] == result["total_kg_co2"]


@pytest.mark.asyncio
async def test_comparison_to_average(db_session, old_oil_building):
    """Comparison should show delta percentage vs Swiss average."""
    result = await compute_carbon_footprint(db_session, old_oil_building.id)

    comp = result["comparison_to_average"]
    assert comp["avg_kg_m2"] == SWISS_AVERAGE_CO2_PER_M2
    assert isinstance(comp["delta_pct"], float)
    # Old building is worse than average, so delta > 0
    assert comp["delta_pct"] > 0


@pytest.mark.asyncio
async def test_unknown_construction_year(db_session, building_no_year):
    """No construction year assumes worst case (pre_1970)."""
    result = await compute_carbon_footprint(db_session, building_no_year.id)

    assert result["energy_source"] == "mazout"
    assert result["consumption_kwh_m2"] == 220.0
    assert result["rating"] in ("E", "F", "G")


@pytest.mark.asyncio
async def test_carbon_building_not_found(db_session):
    """Missing building raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await compute_carbon_footprint(db_session, uuid.uuid4())
