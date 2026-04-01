"""Tests for energy trajectory service."""

import uuid

import pytest

from app.models.building import Building
from app.models.intervention import Intervention
from app.services.energy_trajectory_service import (
    RENOVATION_IMPACT,
    compute_energy_trajectory,
    simulate_renovation_impact,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def old_building(db_session, admin_user):
    """Pre-1970 building (class G, 350 kWh/m2)."""
    bldg = Building(
        id=uuid.uuid4(),
        address="Rue Ancienne 1",
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
async def modern_building(db_session, admin_user):
    """Post-2020 building (class B, 60 kWh/m2)."""
    bldg = Building(
        id=uuid.uuid4(),
        address="Rue Moderne 10",
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
async def building_with_interventions(db_session, admin_user):
    """1990 building with insulation upgrade (E -> D)."""
    bldg = Building(
        id=uuid.uuid4(),
        address="Rue Renovee 5",
        postal_code="3000",
        city="Bern",
        canton="BE",
        construction_year=1990,
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
        intervention_type="insulation_upgrade",
        title="Facade insulation",
        status="completed",
        cost_chf=50000.0,
        created_by=admin_user.id,
    )
    db_session.add(iv)
    await db_session.commit()
    await db_session.refresh(bldg)
    return bldg


@pytest.fixture
async def building_no_surface(db_session, admin_user):
    """Building without surface area (should use default 200m2)."""
    bldg = Building(
        id=uuid.uuid4(),
        address="Rue Inconnue 3",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1990,
        building_type="commercial",
        surface_area_m2=None,
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(bldg)
    await db_session.commit()
    await db_session.refresh(bldg)
    return bldg


# ---------------------------------------------------------------------------
# Tests: compute_energy_trajectory
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trajectory_old_building_all_gaps(db_session, old_building):
    """Pre-1970 building (G=350 kWh) has gaps for all 3 Swiss targets."""
    result = await compute_energy_trajectory(db_session, old_building.id)

    assert result["current_class"] == "G"
    assert result["current_kwh_m2"] == 350.0
    assert result["surface_m2"] == 400.0
    assert len(result["targets"]) == 3

    for t in result["targets"]:
        assert t["on_track"] is False
        assert t["gap_kwh"] > 0
        assert t["gap_pct"] > 0


@pytest.mark.asyncio
async def test_trajectory_modern_building_on_track(db_session, modern_building):
    """Post-2020 building (B=60 kWh) meets 2030 and 2040 targets."""
    result = await compute_energy_trajectory(db_session, modern_building.id)

    assert result["current_class"] == "B"
    assert result["current_kwh_m2"] == 60.0

    # 2030 target = 90 kWh -> on track
    assert result["targets"][0]["on_track"] is True
    assert result["targets"][0]["gap_kwh"] == 0.0

    # 2040 target = 60 kWh -> on track (exactly)
    assert result["targets"][1]["on_track"] is True

    # 2050 target = 35 kWh -> NOT on track
    assert result["targets"][2]["on_track"] is False
    assert result["targets"][2]["gap_kwh"] == 25.0


@pytest.mark.asyncio
async def test_trajectory_with_interventions(db_session, building_with_interventions):
    """Building with insulation upgrade should improve by one class."""
    result = await compute_energy_trajectory(db_session, building_with_interventions.id)

    # 1980 -> base E (index 4), insulation_upgrade -1 -> D (index 3)
    assert result["current_class"] == "D"
    assert result["current_kwh_m2"] == 130.0


@pytest.mark.asyncio
async def test_trajectory_default_surface(db_session, building_no_surface):
    """Building without surface uses default 200m2."""
    result = await compute_energy_trajectory(db_session, building_no_surface.id)

    assert result["surface_m2"] == 200.0


@pytest.mark.asyncio
async def test_trajectory_building_not_found(db_session):
    """Missing building raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await compute_energy_trajectory(db_session, uuid.uuid4())


# ---------------------------------------------------------------------------
# Tests: simulate_renovation_impact
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_simulate_single_measure(db_session, old_building):
    """Facade insulation should reduce consumption by 25%."""
    result = await simulate_renovation_impact(db_session, old_building.id, ["facade_insulation"])

    assert result["current_class"] == "G"
    assert result["current_kwh_m2"] == 350.0
    # 350 * (1 - 0.25) = 262.5
    assert result["projected_kwh_m2"] == 262.5
    assert result["savings_kwh"] > 0
    assert result["savings_chf_per_year"] > 0
    assert result["co2_reduction_kg"] > 0
    assert len(result["measures_detail"]) == 1


@pytest.mark.asyncio
async def test_simulate_multiple_measures(db_session, old_building):
    """Multiple measures compound multiplicatively."""
    result = await simulate_renovation_impact(db_session, old_building.id, ["facade_insulation", "heat_pump"])

    # 350 * 0.75 * 0.60 = 157.5
    assert result["projected_kwh_m2"] == 157.5
    assert len(result["measures_detail"]) == 2

    # Renovation cost should include both
    facade_cost = 250 * 400.0  # cost_per_m2 * surface
    heat_pump_cost = 25000.0  # forfait
    assert result["renovation_cost"] == facade_cost + heat_pump_cost


@pytest.mark.asyncio
async def test_simulate_no_valid_measures(db_session, old_building):
    """Invalid measures return zero impact."""
    result = await simulate_renovation_impact(db_session, old_building.id, ["nonexistent_measure"])

    assert result["projected_kwh_m2"] == result["current_kwh_m2"]
    assert result["savings_kwh"] == 0.0
    assert result["renovation_cost"] == 0.0
    assert result["measures_detail"] == []


@pytest.mark.asyncio
async def test_simulate_all_measures(db_session, old_building):
    """All 5 measures together achieve significant reduction."""
    all_measures = list(RENOVATION_IMPACT.keys())
    result = await simulate_renovation_impact(db_session, old_building.id, all_measures)

    # Must reduce significantly from 350
    assert result["projected_kwh_m2"] < 150.0
    assert result["projected_class"] in ("A", "B", "C", "D")
    assert len(result["measures_detail"]) == 5
    assert result["renovation_cost"] > 0


@pytest.mark.asyncio
async def test_simulate_projected_class_assignment(db_session, modern_building):
    """Post-2020 building + solar panels should stay A or B."""
    result = await simulate_renovation_impact(db_session, modern_building.id, ["solar_panels"])

    # 60 * 0.80 = 48 -> class B
    assert result["projected_kwh_m2"] == 48.0
    assert result["projected_class"] == "B"
