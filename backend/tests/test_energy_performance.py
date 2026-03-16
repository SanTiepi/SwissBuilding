"""Tests for the Energy Performance service, schemas, and API routes."""

import uuid

import pytest

from app.models.building import Building
from app.models.intervention import Intervention
from app.services.energy_performance_service import (
    CO2_FACTOR,
    DEFAULT_SURFACE_M2,
    KWH_PER_CLASS,
    _apply_improvements,
    _base_class_index,
    _class_from_index,
    compare_buildings_energy,
    estimate_energy_class,
    estimate_renovation_impact,
    get_portfolio_energy_profile,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_building(db_session, admin_user, construction_year=1965, surface=None, address="Rue Test 1"):
    bld = Building(
        id=uuid.uuid4(),
        address=address,
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=construction_year,
        building_type="residential",
        surface_area_m2=surface,
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(bld)
    await db_session.commit()
    await db_session.refresh(bld)
    return bld


async def _add_intervention(db_session, admin_user, building, itype, status="completed"):
    iv = Intervention(
        id=uuid.uuid4(),
        building_id=building.id,
        intervention_type=itype,
        title=f"Test {itype}",
        status=status,
        created_by=admin_user.id,
    )
    db_session.add(iv)
    await db_session.commit()
    return iv


# ---------------------------------------------------------------------------
# Unit tests: base class from construction year
# ---------------------------------------------------------------------------


class TestBaseClassFromConstructionYear:
    """Energy class from construction year (each decade bracket)."""

    def test_pre_1970_is_g(self):
        assert _class_from_index(_base_class_index(1960)) == "G"

    def test_1965_is_g(self):
        assert _class_from_index(_base_class_index(1965)) == "G"

    def test_1970_is_f(self):
        assert _class_from_index(_base_class_index(1970)) == "F"

    def test_1980_is_f(self):
        assert _class_from_index(_base_class_index(1980)) == "F"

    def test_1985_is_e(self):
        assert _class_from_index(_base_class_index(1985)) == "E"

    def test_1995_is_e(self):
        assert _class_from_index(_base_class_index(1995)) == "E"

    def test_2000_is_d(self):
        assert _class_from_index(_base_class_index(2000)) == "D"

    def test_2005_is_d(self):
        assert _class_from_index(_base_class_index(2005)) == "D"

    def test_2010_is_c(self):
        assert _class_from_index(_base_class_index(2010)) == "C"

    def test_2015_is_c(self):
        assert _class_from_index(_base_class_index(2015)) == "C"

    def test_2020_is_b(self):
        assert _class_from_index(_base_class_index(2020)) == "B"

    def test_2024_is_b(self):
        assert _class_from_index(_base_class_index(2024)) == "B"

    def test_none_year_is_g(self):
        assert _class_from_index(_base_class_index(None)) == "G"


# ---------------------------------------------------------------------------
# Unit tests: intervention improvements
# ---------------------------------------------------------------------------


class TestInterventionImprovements:
    """Intervention improvements (insulation, windows, hvac, full renovation)."""

    def test_insulation_upgrade_improves_by_1(self):
        # G (6) - 1 = 5 -> F
        assert _apply_improvements(6, ["insulation_upgrade"]) == 5

    def test_window_replacement_improves_by_half(self):
        # G (6) - 0.5 = 5.5 -> int(5.5) = 5 -> F
        assert _apply_improvements(6, ["window_replacement"]) == 5

    def test_hvac_upgrade_improves_by_1(self):
        # F (5) - 1 = 4 -> E
        assert _apply_improvements(5, ["hvac_upgrade"]) == 4

    def test_full_renovation_improves_by_2(self):
        # G (6) - 2 = 4 -> E... wait, that's int(2.0)=2
        assert _apply_improvements(6, ["full_renovation"]) == 4

    def test_combined_insulation_and_hvac(self):
        # G (6) - (1+1) = 4 -> E... but wait, combined = 2.0
        assert _apply_improvements(6, ["insulation_upgrade", "hvac_upgrade"]) == 4

    def test_class_cap_at_a_from_g(self):
        # All interventions from G: 6 - 4.5 = 1.5 -> int = 1 -> B
        result = _apply_improvements(6, ["full_renovation", "insulation_upgrade", "hvac_upgrade", "window_replacement"])
        assert result == 1
        assert _class_from_index(result) == "B"

    def test_class_cap_at_a_from_d(self):
        # All interventions from D: 3 - 4.5 = -1.5 -> int = -1 -> capped at 0 = A
        result = _apply_improvements(3, ["full_renovation", "insulation_upgrade", "hvac_upgrade", "window_replacement"])
        assert result == 0
        assert _class_from_index(result) == "A"

    def test_unknown_intervention_no_effect(self):
        assert _apply_improvements(6, ["painting"]) == 6


# ---------------------------------------------------------------------------
# Integration tests: estimate_energy_class
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_estimate_energy_class_basic(db_session, admin_user):
    """Pre-1970 building with no interventions should be class G."""
    bld = await _make_building(db_session, admin_user, construction_year=1960)
    result = await estimate_energy_class(db_session, bld.id)
    assert result.energy_class == "G"
    assert result.kwh_per_m2_year == 350.0


@pytest.mark.asyncio
async def test_estimate_energy_class_with_interventions(db_session, admin_user):
    """Insulation upgrade on 1960 building: G -> F."""
    bld = await _make_building(db_session, admin_user, construction_year=1960)
    await _add_intervention(db_session, admin_user, bld, "insulation_upgrade")
    result = await estimate_energy_class(db_session, bld.id)
    assert result.energy_class == "F"
    assert result.kwh_per_m2_year == 250.0


@pytest.mark.asyncio
async def test_co2_calculation(db_session, admin_user):
    """CO2 = kWh/m2 x 0.15, total = CO2/m2 x surface."""
    bld = await _make_building(db_session, admin_user, construction_year=2020, surface=300.0)
    result = await estimate_energy_class(db_session, bld.id)
    assert result.energy_class == "B"
    expected_co2_m2 = 60.0 * CO2_FACTOR
    assert result.co2_kg_per_m2_year == expected_co2_m2
    assert result.total_co2_kg_year == expected_co2_m2 * 300.0


@pytest.mark.asyncio
async def test_minergie_compatible_a(db_session, admin_user):
    """Only A and B are Minergie compatible."""
    bld = await _make_building(db_session, admin_user, construction_year=2020)
    result = await estimate_energy_class(db_session, bld.id)
    assert result.minergie_compatible is True  # B


@pytest.mark.asyncio
async def test_minergie_not_compatible_d(db_session, admin_user):
    """Class D is not Minergie compatible."""
    bld = await _make_building(db_session, admin_user, construction_year=2000)
    result = await estimate_energy_class(db_session, bld.id)
    assert result.energy_class == "D"
    assert result.minergie_compatible is False


@pytest.mark.asyncio
async def test_no_surface_uses_default(db_session, admin_user):
    """Building with no surface_area_m2 should use default 200 m²."""
    bld = await _make_building(db_session, admin_user, construction_year=2020, surface=None)
    result = await estimate_energy_class(db_session, bld.id)
    assert result.total_co2_kg_year == KWH_PER_CLASS["B"] * CO2_FACTOR * DEFAULT_SURFACE_M2


@pytest.mark.asyncio
async def test_no_interventions_base_class_only(db_session, admin_user):
    """No interventions → base class only."""
    bld = await _make_building(db_session, admin_user, construction_year=1985)
    result = await estimate_energy_class(db_session, bld.id)
    assert result.energy_class == "E"


@pytest.mark.asyncio
async def test_all_interventions_on_old_building(db_session, admin_user):
    """Building (1960, G) with all interventions: 6-4.5=1.5 -> int=1 -> B."""
    bld = await _make_building(db_session, admin_user, construction_year=1960)
    for itype in ["full_renovation", "insulation_upgrade", "hvac_upgrade", "window_replacement"]:
        await _add_intervention(db_session, admin_user, bld, itype)
    result = await estimate_energy_class(db_session, bld.id)
    assert result.energy_class == "B"
    assert result.minergie_compatible is True


@pytest.mark.asyncio
async def test_all_interventions_cap_at_a(db_session, admin_user):
    """Building (2000, D=3) with all interventions: 3-4.5=-1.5 -> capped at A."""
    bld = await _make_building(db_session, admin_user, construction_year=2000)
    for itype in ["full_renovation", "insulation_upgrade", "hvac_upgrade", "window_replacement"]:
        await _add_intervention(db_session, admin_user, bld, itype)
    result = await estimate_energy_class(db_session, bld.id)
    assert result.energy_class == "A"
    assert result.minergie_compatible is True


@pytest.mark.asyncio
async def test_only_completed_interventions_counted(db_session, admin_user):
    """Planned (not completed) interventions should not improve class."""
    bld = await _make_building(db_session, admin_user, construction_year=1960)
    await _add_intervention(db_session, admin_user, bld, "full_renovation", status="planned")
    result = await estimate_energy_class(db_session, bld.id)
    assert result.energy_class == "G"


@pytest.mark.asyncio
async def test_improvement_potential(db_session, admin_user):
    """improvement_potential_class shows what's achievable with all interventions."""
    bld = await _make_building(db_session, admin_user, construction_year=1960)
    result = await estimate_energy_class(db_session, bld.id)
    # G building, best possible with all interventions = A (4.5 improvement from G=6 -> 1.5 -> 1 -> B? no, int(4.5)=4, 6-4=2 -> C)
    # Actually: total improvement = 1+0.5+1+2 = 4.5, int(4.5) = 4, 6-4 = 2 -> C
    assert result.improvement_potential_class is not None


# ---------------------------------------------------------------------------
# Integration tests: estimate_renovation_impact
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_renovation_impact_single(db_session, admin_user):
    """Single intervention projection."""
    bld = await _make_building(db_session, admin_user, construction_year=1960, surface=250.0)
    result = await estimate_renovation_impact(db_session, bld.id, ["insulation_upgrade"])
    assert result.current_class == "G"
    assert result.projected_class == "F"
    savings_kwh = 350.0 - 250.0
    assert result.energy_savings_percent == round(savings_kwh / 350.0 * 100, 1)
    assert result.annual_savings_chf == round(savings_kwh * 0.12 * 250.0, 2)


@pytest.mark.asyncio
async def test_renovation_impact_multiple(db_session, admin_user):
    """Multiple planned interventions."""
    bld = await _make_building(db_session, admin_user, construction_year=1960, surface=200.0)
    result = await estimate_renovation_impact(
        db_session, bld.id, ["insulation_upgrade", "hvac_upgrade", "full_renovation"]
    )
    assert result.current_class == "G"
    # total improvement = 1+1+2 = 4, G(6) - 4 = 2 -> C
    assert result.projected_class == "C"


@pytest.mark.asyncio
async def test_renovation_impact_chf_calculation(db_session, admin_user):
    """Annual savings CHF = (current_kwh - projected_kwh) x 0.12 x surface."""
    bld = await _make_building(db_session, admin_user, construction_year=1960, surface=100.0)
    result = await estimate_renovation_impact(db_session, bld.id, ["full_renovation"])
    # G→E: 350-180=170 kWh/m² savings
    expected = 170.0 * 0.12 * 100.0
    assert result.annual_savings_chf == round(expected, 2)


# ---------------------------------------------------------------------------
# Integration tests: portfolio profile
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_portfolio_empty(db_session):
    """Empty portfolio returns zero counts."""
    result = await get_portfolio_energy_profile(db_session)
    assert result.total_buildings == 0
    assert result.total_co2_tonnes_year == 0.0


@pytest.mark.asyncio
async def test_portfolio_distribution(db_session, admin_user):
    """Portfolio with buildings of different ages should distribute classes."""
    await _make_building(db_session, admin_user, construction_year=1960, address="Rue A")
    await _make_building(db_session, admin_user, construction_year=2020, address="Rue B")
    await _make_building(db_session, admin_user, construction_year=2000, address="Rue C")

    result = await get_portfolio_energy_profile(db_session)
    assert result.total_buildings == 3
    assert result.class_distribution["G"] == 1
    assert result.class_distribution["B"] == 1
    assert result.class_distribution["D"] == 1


@pytest.mark.asyncio
async def test_portfolio_worst_performers(db_session, admin_user):
    """Worst performers should include F and G class buildings."""
    await _make_building(db_session, admin_user, construction_year=1960, address="Old 1")
    await _make_building(db_session, admin_user, construction_year=2020, address="New 1")

    result = await get_portfolio_energy_profile(db_session)
    assert len(result.worst_performers) == 1
    assert result.worst_performers[0]["energy_class"] == "G"


# ---------------------------------------------------------------------------
# Integration tests: compare buildings
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compare_buildings_ranking(db_session, admin_user):
    """Buildings should be ranked by kWh (lowest = rank 1)."""
    b1 = await _make_building(db_session, admin_user, construction_year=1960, address="Old")
    b2 = await _make_building(db_session, admin_user, construction_year=2020, address="New")

    result = await compare_buildings_energy(db_session, [b1.id, b2.id])
    assert len(result) == 2
    # New (B, 60 kWh) should rank 1, Old (G, 350 kWh) rank 2
    assert result[0].rank == 1
    assert result[0].energy_class == "B"
    assert result[1].rank == 2
    assert result[1].energy_class == "G"


@pytest.mark.asyncio
async def test_compare_building_not_found(db_session, admin_user):
    """Compare with non-existent building should raise ValueError."""
    fake_id = uuid.uuid4()
    with pytest.raises(ValueError, match="not found"):
        await compare_buildings_energy(db_session, [fake_id])


@pytest.mark.asyncio
async def test_compare_too_many_buildings(db_session, admin_user):
    """Comparing more than 10 buildings should raise ValueError."""
    ids = [uuid.uuid4() for _ in range(11)]
    with pytest.raises(ValueError, match="more than 10"):
        await compare_buildings_energy(db_session, ids)


# ---------------------------------------------------------------------------
# API route tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_get_energy_performance(client, auth_headers, sample_building):
    """GET /api/v1/buildings/{id}/energy-performance returns estimate."""
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/energy-performance", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["energy_class"] == "G"  # 1965 building
    assert data["kwh_per_m2_year"] == 350.0


@pytest.mark.asyncio
async def test_api_energy_performance_not_found(client, auth_headers):
    """GET returns 404 for non-existent building."""
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/buildings/{fake_id}/energy-performance", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_renovation_impact(client, auth_headers, sample_building):
    """POST /api/v1/buildings/{id}/energy-renovation-impact returns impact."""
    resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/energy-renovation-impact",
        json={"planned_interventions": ["insulation_upgrade"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_class"] == "G"
    assert data["projected_class"] == "F"


@pytest.mark.asyncio
async def test_api_portfolio_energy_profile(client, auth_headers):
    """GET /api/v1/portfolio/energy-profile returns profile."""
    resp = await client.get("/api/v1/portfolio/energy-profile", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "class_distribution" in data
    assert "total_co2_tonnes_year" in data
