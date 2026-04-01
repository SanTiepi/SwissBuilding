"""Tests for fiscal simulator service."""

import uuid

import pytest

from app.models.building import Building
from app.services.fiscal_simulator_service import (
    SUBSIDY_PROGRAMS,
    check_subsidy_eligibility,
    simulate_fiscal_impact,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def vd_building(db_session, admin_user):
    bldg = Building(
        id=uuid.uuid4(),
        address="Rue Fiscale 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1975,
        building_type="residential",
        surface_area_m2=300.0,
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(bldg)
    await db_session.commit()
    await db_session.refresh(bldg)
    return bldg


@pytest.fixture
async def ge_building(db_session, admin_user):
    bldg = Building(
        id=uuid.uuid4(),
        address="Rue Geneve 5",
        postal_code="1200",
        city="Geneve",
        canton="GE",
        construction_year=1985,
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
async def zh_building(db_session, admin_user):
    bldg = Building(
        id=uuid.uuid4(),
        address="Bahnhofstrasse 10",
        postal_code="8000",
        city="Zurich",
        canton="ZH",
        construction_year=1990,
        building_type="commercial",
        surface_area_m2=500.0,
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(bldg)
    await db_session.commit()
    await db_session.refresh(bldg)
    return bldg


@pytest.fixture
async def be_building(db_session, admin_user):
    bldg = Building(
        id=uuid.uuid4(),
        address="Bundesplatz 1",
        postal_code="3000",
        city="Bern",
        canton="BE",
        construction_year=1980,
        building_type="residential",
        surface_area_m2=350.0,
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(bldg)
    await db_session.commit()
    await db_session.refresh(bldg)
    return bldg


# ---------------------------------------------------------------------------
# Tests: simulate_fiscal_impact
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fiscal_vd_full_deduction_with_energy_bonus(db_session, vd_building):
    """VD: 100% deductible + energy bonus for energy measures."""
    result = await simulate_fiscal_impact(
        db_session, vd_building.id, 100000.0, "VD", ["facade_insulation", "heat_pump"]
    )

    assert result["gross_cost"] == 100000.0
    # Tax deduction: 100000 * 1.0 * (0.30 + 0.10) = 40000
    assert result["tax_deduction"] == 40000.0
    assert result["subsidy_total"] > 0
    assert result["net_cost"] < result["gross_cost"]
    assert result["roi_years"] > 0

    # Check breakdown has subsidies
    assert len(result["breakdown"]["subsidies"]) > 0
    assert result["breakdown"]["deduction_detail"]["energy_bonus_applied"] is True


@pytest.mark.asyncio
async def test_fiscal_ge_subsidies(db_session, ge_building):
    """GE: should get Programme Batiments + Programme Energie GE."""
    result = await simulate_fiscal_impact(db_session, ge_building.id, 80000.0, "GE", ["heat_pump", "solar_panels"])

    subsidy_names = [s["program_id"] for s in result["breakdown"]["subsidies"]]
    assert "programme_batiments" in subsidy_names
    assert "programme_energie_ge" in subsidy_names
    assert "programme_energie_vd" not in subsidy_names


@pytest.mark.asyncio
async def test_fiscal_zh_capped_deduction(db_session, zh_building):
    """ZH: max_deduction_pct = 0.8, so tax base is lower."""
    result = await simulate_fiscal_impact(db_session, zh_building.id, 100000.0, "ZH", ["facade_insulation"])

    # 100000 * 0.8 * (0.30 + 0.10 energy bonus) = 32000
    assert result["tax_deduction"] == 32000.0
    deduction = result["breakdown"]["deduction_detail"]
    assert deduction["max_deduction_pct"] == 0.8
    assert deduction["energy_bonus_applied"] is True


@pytest.mark.asyncio
async def test_fiscal_be_no_energy_bonus(db_session, be_building):
    """BE: no energy_bonus even for energy measures."""
    result = await simulate_fiscal_impact(db_session, be_building.id, 50000.0, "BE", ["heat_pump"])

    # 50000 * 1.0 * 0.30 = 15000 (no energy bonus)
    assert result["tax_deduction"] == 15000.0
    assert result["breakdown"]["deduction_detail"]["energy_bonus_applied"] is False


@pytest.mark.asyncio
async def test_fiscal_unknown_canton(db_session, vd_building):
    """Unknown canton gets zero deduction."""
    result = await simulate_fiscal_impact(db_session, vd_building.id, 50000.0, "XX", ["facade_insulation"])

    assert result["tax_deduction"] == 0.0
    assert result["breakdown"]["deduction_detail"]["deductible_amount"] == 0.0


@pytest.mark.asyncio
async def test_fiscal_no_energy_measures(db_session, vd_building):
    """Non-energy measures still get base deduction but no energy bonus."""
    result = await simulate_fiscal_impact(db_session, vd_building.id, 20000.0, "VD", ["general_repair"])

    # 20000 * 1.0 * 0.30 = 6000 (no energy bonus — "general_repair" is not an energy measure)
    assert result["tax_deduction"] == 6000.0
    assert result["breakdown"]["deduction_detail"]["energy_bonus_applied"] is False
    # No subsidy programs match "general_repair"
    assert result["subsidy_total"] == 0.0


@pytest.mark.asyncio
async def test_fiscal_building_not_found(db_session):
    """Missing building raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await simulate_fiscal_impact(db_session, uuid.uuid4(), 50000.0, "VD", ["heat_pump"])


@pytest.mark.asyncio
async def test_fiscal_net_cost_never_negative(db_session, vd_building):
    """Net cost should not go below zero even with large subsidies/deductions."""
    result = await simulate_fiscal_impact(db_session, vd_building.id, 5000.0, "VD", ["heat_pump", "solar_panels"])

    assert result["net_cost"] >= 0.0


# ---------------------------------------------------------------------------
# Tests: check_subsidy_eligibility
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_eligibility_vd_all_programs(db_session, vd_building):
    """VD building: programme_batiments + programme_energie_vd eligible."""
    result = await check_subsidy_eligibility(db_session, vd_building.id, "VD")

    eligible = [p for p in result if p["eligible"]]
    ineligible = [p for p in result if not p["eligible"]]

    assert len(result) == len(SUBSIDY_PROGRAMS)
    # programme_batiments (all cantons) + programme_energie_vd
    assert len(eligible) == 2
    eligible_ids = {p["program_id"] for p in eligible}
    assert "programme_batiments" in eligible_ids
    assert "programme_energie_vd" in eligible_ids

    # programme_energie_ge should not be eligible
    assert len(ineligible) == 1
    assert ineligible[0]["program_id"] == "programme_energie_ge"
    assert "not covered" in ineligible[0]["reason"]


@pytest.mark.asyncio
async def test_eligibility_ge_programs(db_session, ge_building):
    """GE building: programme_batiments + programme_energie_ge eligible."""
    result = await check_subsidy_eligibility(db_session, ge_building.id, "GE")

    eligible_ids = {p["program_id"] for p in result if p["eligible"]}
    assert "programme_batiments" in eligible_ids
    assert "programme_energie_ge" in eligible_ids
    assert "programme_energie_vd" not in eligible_ids


@pytest.mark.asyncio
async def test_eligibility_be_federal_only(db_session, be_building):
    """BE building: only federal programme_batiments eligible."""
    result = await check_subsidy_eligibility(db_session, be_building.id, "BE")

    eligible = [p for p in result if p["eligible"]]
    assert len(eligible) == 1
    assert eligible[0]["program_id"] == "programme_batiments"


@pytest.mark.asyncio
async def test_eligibility_building_not_found(db_session):
    """Missing building raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await check_subsidy_eligibility(db_session, uuid.uuid4(), "VD")
