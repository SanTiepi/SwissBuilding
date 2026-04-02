"""Tests for the CECB lookup service — energy certificate endpoint logic."""

import uuid
from datetime import UTC, datetime

import pytest

from app.models.building import Building
from app.models.intervention import Intervention
from app.services.cecb_lookup_service import (
    _estimate_from_construction,
    get_building_energy_certificate,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_building(
    db_session,
    admin_user,
    egid=None,
    construction_year=1965,
    cecb_class=None,
    cecb_heating_demand=None,
    cecb_cooling_demand=None,
    cecb_dhw_demand=None,
    cecb_certificate_date=None,
    cecb_source=None,
):
    bld = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=construction_year,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
        egid=egid,
        cecb_class=cecb_class,
        cecb_heating_demand=cecb_heating_demand,
        cecb_cooling_demand=cecb_cooling_demand,
        cecb_dhw_demand=cecb_dhw_demand,
        cecb_certificate_date=cecb_certificate_date,
        cecb_source=cecb_source,
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
        description="Test intervention",
        created_by=admin_user.id,
    )
    db_session.add(iv)
    await db_session.commit()
    return iv


# ---------------------------------------------------------------------------
# _estimate_from_construction (unit)
# ---------------------------------------------------------------------------


class TestEstimateFromConstruction:
    def test_pre_1970(self):
        cls, kwh = _estimate_from_construction(1960, [])
        assert cls == "G"
        assert kwh == 350.0

    def test_1985(self):
        cls, kwh = _estimate_from_construction(1985, [])
        assert cls == "E"
        assert kwh == 180.0

    def test_2020(self):
        cls, kwh = _estimate_from_construction(2022, [])
        assert cls == "B"
        assert kwh == 60.0

    def test_none_year(self):
        cls, _kwh = _estimate_from_construction(None, [])
        assert cls == "G"

    def test_with_interventions(self):
        cls, kwh = _estimate_from_construction(1960, ["full_renovation"])
        # G (index 6) - 2.0 improvement = index 4 = E
        assert cls == "E"
        assert kwh == 180.0


# ---------------------------------------------------------------------------
# get_building_energy_certificate — real CECB
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_certificate_with_real_cecb(db_session, admin_user):
    """Building with CECB data returns cecb_official source."""
    bld = await _make_building(
        db_session,
        admin_user,
        egid=11111,
        construction_year=1960,
        cecb_class="B",
        cecb_heating_demand=55.0,
        cecb_cooling_demand=10.0,
        cecb_dhw_demand=25.0,
        cecb_certificate_date=datetime(2024, 6, 1, tzinfo=UTC),
        cecb_source="CECB VD 2024",
    )

    cert = await get_building_energy_certificate(db_session, bld.id)
    assert cert.energy_class == "B"
    assert cert.source == "cecb_official"
    assert cert.energy_consumption_kwh_m2 == 55.0
    assert cert.heating_demand == 55.0
    assert cert.cooling_demand == 10.0
    assert cert.dhw_demand == 25.0
    assert cert.certificate_date is not None
    assert cert.energy_emissions_co2_m2 == pytest.approx(55.0 * 0.15, rel=0.01)


@pytest.mark.asyncio
async def test_certificate_cecb_without_heating_demand(db_session, admin_user):
    """CECB with class but no heating demand uses KWH_PER_CLASS fallback."""
    bld = await _make_building(
        db_session,
        admin_user,
        cecb_class="D",
        cecb_source="CECB GE 2023",
    )

    cert = await get_building_energy_certificate(db_session, bld.id)
    assert cert.energy_class == "D"
    assert cert.source == "cecb_official"
    assert cert.energy_consumption_kwh_m2 == 130.0  # KWH_PER_CLASS["D"]


# ---------------------------------------------------------------------------
# get_building_energy_certificate — estimation fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_certificate_estimated_old_building(db_session, admin_user):
    """Old building without CECB falls back to estimation."""
    bld = await _make_building(db_session, admin_user, construction_year=1960)

    cert = await get_building_energy_certificate(db_session, bld.id)
    assert cert.energy_class == "G"
    assert cert.source == "estimated"
    assert cert.energy_consumption_kwh_m2 == 350.0
    assert cert.heating_demand is None
    assert cert.certificate_date is None


@pytest.mark.asyncio
async def test_certificate_estimated_modern_building(db_session, admin_user):
    """Modern building without CECB estimates B class."""
    bld = await _make_building(db_session, admin_user, construction_year=2022)

    cert = await get_building_energy_certificate(db_session, bld.id)
    assert cert.energy_class == "B"
    assert cert.source == "estimated"


@pytest.mark.asyncio
async def test_certificate_estimated_with_interventions(db_session, admin_user):
    """Completed interventions improve the estimated class."""
    bld = await _make_building(db_session, admin_user, construction_year=1960)
    await _add_intervention(db_session, admin_user, bld, "full_renovation")

    cert = await get_building_energy_certificate(db_session, bld.id)
    # G (1960) - 2.0 (full_renovation) = E
    assert cert.energy_class == "E"
    assert cert.source == "estimated"


@pytest.mark.asyncio
async def test_certificate_ignores_pending_interventions(db_session, admin_user):
    """Only completed interventions affect estimation."""
    bld = await _make_building(db_session, admin_user, construction_year=1960)
    await _add_intervention(db_session, admin_user, bld, "full_renovation", status="planned")

    cert = await get_building_energy_certificate(db_session, bld.id)
    assert cert.energy_class == "G"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_certificate_not_found(db_session, admin_user):
    """Missing building raises ValueError."""
    fake_id = uuid.uuid4()
    with pytest.raises(ValueError, match="not found"):
        await get_building_energy_certificate(db_session, fake_id)


@pytest.mark.asyncio
async def test_certificate_has_building_id(db_session, admin_user):
    """Response always includes the correct building_id."""
    bld = await _make_building(db_session, admin_user, construction_year=2000)
    cert = await get_building_energy_certificate(db_session, bld.id)
    assert cert.building_id == bld.id


@pytest.mark.asyncio
async def test_certificate_emissions_formula(db_session, admin_user):
    """CO2 emissions = kwh * CO2_FACTOR (0.15)."""
    bld = await _make_building(
        db_session,
        admin_user,
        cecb_class="A",
        cecb_heating_demand=30.0,
    )
    cert = await get_building_energy_certificate(db_session, bld.id)
    assert cert.energy_emissions_co2_m2 == pytest.approx(30.0 * 0.15, rel=0.01)
