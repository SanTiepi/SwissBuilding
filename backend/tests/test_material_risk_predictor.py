"""Tests for material_risk_predictor — pollutant probability from material type + age."""

from __future__ import annotations

import uuid

import pytest

from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.diagnostic import Diagnostic
from app.models.material import Material
from app.models.sample import Sample
from app.models.zone import Zone
from app.services.material_risk_predictor import (
    predict_building_material_risks,
    predict_pollutant_risk,
)

# ── Helpers ────────────────────────────────────────────────────────


async def _create_building(db, admin_user):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=admin_user.id,
        owner_id=admin_user.id,
        status="active",
    )
    db.add(b)
    await db.flush()
    return b


async def _create_zone(db, building_id):
    z = Zone(
        id=uuid.uuid4(),
        building_id=building_id,
        zone_type="floor",
        name="Ground floor",
    )
    db.add(z)
    await db.flush()
    return z


async def _create_element(db, zone_id):
    e = BuildingElement(
        id=uuid.uuid4(),
        zone_id=zone_id,
        element_type="floor_covering",
        name="Floor covering",
    )
    db.add(e)
    await db.flush()
    return e


async def _create_material(db, element_id, *, material_type="dalle_vinyle", installation_year=1975, name="Vinyl tile"):
    m = Material(
        id=uuid.uuid4(),
        element_id=element_id,
        material_type=material_type,
        name=name,
        installation_year=installation_year,
    )
    db.add(m)
    await db.flush()
    return m


# ── predict_pollutant_risk Tests ──────────────────────────────────


@pytest.mark.asyncio
async def test_exact_match_dalle_vinyle():
    """dalle_vinyle from 1975 → asbestos 0.85, hap 0.30."""
    result = await predict_pollutant_risk("dalle_vinyle", 1975)
    assert result["asbestos"] == pytest.approx(0.85)
    assert result["hap"] == pytest.approx(0.30)


@pytest.mark.asyncio
async def test_flocage_high_asbestos():
    """flocage from 1965 → asbestos 0.95."""
    result = await predict_pollutant_risk("flocage", 1965)
    assert result["asbestos"] == pytest.approx(0.95)
    assert "hap" not in result


@pytest.mark.asyncio
async def test_year_outside_range():
    """dalle_vinyle from 2000 → no match (outside 1960-1985)."""
    result = await predict_pollutant_risk("dalle_vinyle", 2000)
    assert result == {}


@pytest.mark.asyncio
async def test_year_boundary_start():
    """dalle_vinyle at exact start year 1960 → matches."""
    result = await predict_pollutant_risk("dalle_vinyle", 1960)
    assert "asbestos" in result


@pytest.mark.asyncio
async def test_year_boundary_end():
    """dalle_vinyle at exact end year 1985 → matches."""
    result = await predict_pollutant_risk("dalle_vinyle", 1985)
    assert "asbestos" in result


@pytest.mark.asyncio
async def test_unknown_material_type():
    """Unknown material type → empty result."""
    result = await predict_pollutant_risk("titanium_alloy", 1975)
    assert result == {}


@pytest.mark.asyncio
async def test_peinture_two_ranges():
    """peinture spans two ranges — 1950 matches first, 1970 matches second."""
    result_old = await predict_pollutant_risk("peinture", 1950)
    assert result_old == {"lead": 0.80}

    result_mid = await predict_pollutant_risk("peinture", 1970)
    assert result_mid["lead"] == pytest.approx(0.40)
    assert result_mid["pcb"] == pytest.approx(0.15)


@pytest.mark.asyncio
async def test_none_year_returns_max():
    """None installation year → aggregate max across all ranges."""
    result = await predict_pollutant_risk("peinture", None)
    # Max lead across both ranges: 0.80
    assert result["lead"] == pytest.approx(0.80)
    # pcb only in second range: 0.15
    assert result["pcb"] == pytest.approx(0.15)


# ── predict_building_material_risks Tests ─────────────────────────


@pytest.mark.asyncio
async def test_building_no_materials(db_session, admin_user):
    """Building with no zones → empty result."""
    building = await _create_building(db_session, admin_user)
    result = await predict_building_material_risks(db_session, building.id)
    assert result == []


@pytest.mark.asyncio
async def test_building_with_risky_material(db_session, admin_user):
    """Building with dalle_vinyle from 1975 → asbestos + hap predicted."""
    building = await _create_building(db_session, admin_user)
    zone = await _create_zone(db_session, building.id)
    element = await _create_element(db_session, zone.id)
    await _create_material(
        db_session,
        element.id,
        material_type="dalle_vinyle",
        installation_year=1975,
        name="Vinyl tile 1975",
    )

    result = await predict_building_material_risks(db_session, building.id)
    assert len(result) == 1
    assert "asbestos" in result[0]["predictions"]
    assert "hap" in result[0]["predictions"]
    assert result[0]["contradictions"] == []


@pytest.mark.asyncio
async def test_contradiction_detection(db_session, admin_user):
    """Material predicts asbestos 0.85 but diagnostic says clean → contradiction."""
    building = await _create_building(db_session, admin_user)
    zone = await _create_zone(db_session, building.id)
    element = await _create_element(db_session, zone.id)
    await _create_material(
        db_session,
        element.id,
        material_type="dalle_vinyle",
        installation_year=1975,
    )

    # Create diagnostic with clean asbestos sample
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="asbestos",
        status="completed",
    )
    db_session.add(diag)
    await db_session.flush()

    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S-001",
        pollutant_type="asbestos",
        concentration=0.0,
        unit="mg/kg",
        threshold_exceeded=False,
    )
    db_session.add(sample)
    await db_session.flush()

    result = await predict_building_material_risks(db_session, building.id)
    assert len(result) == 1
    assert len(result[0]["contradictions"]) == 1
    assert result[0]["contradictions"][0]["pollutant"] == "asbestos"
    assert result[0]["contradictions"][0]["diagnostic_result"] == "clean"
