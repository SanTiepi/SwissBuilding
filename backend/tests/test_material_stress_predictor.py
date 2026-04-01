"""Tests for Material Stress Predictor service."""

import uuid

import pytest

from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.models.user import User
from app.models.zone import Zone
from app.services.material_stress_predictor import (
    _compute_climate_stress_factor,
    _infer_material_type,
    _project_condition,
    predict_degradation,
)
from tests.conftest import _HASH_ADMIN

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _setup_user(db):
    user = User(
        id=uuid.uuid4(),
        email=f"stress-{uuid.uuid4().hex[:6]}@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Test",
        last_name="User",
        role="admin",
    )
    db.add(user)
    await db.commit()
    return user


async def _setup_building(db, user, **kw):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Stress 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1965,
        "building_type": "residential",
        "created_by": user.id,
        "status": "active",
    }
    defaults.update(kw)
    b = Building(**defaults)
    db.add(b)
    await db.commit()
    return b


async def _setup_diagnostic_with_sample(db, building_id, pollutant="asbestos", exceeded=True, **sample_kw):
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type=pollutant,
        status="completed",
    )
    db.add(diag)
    await db.commit()

    defaults = {
        "id": uuid.uuid4(),
        "diagnostic_id": diag.id,
        "sample_number": f"S-{uuid.uuid4().hex[:6]}",
        "pollutant_type": pollutant,
        "concentration": 2.5,
        "unit": "%",
        "threshold_exceeded": exceeded,
        "risk_level": "high" if exceeded else "low",
    }
    defaults.update(sample_kw)
    s = Sample(**defaults)
    db.add(s)
    await db.commit()
    return diag, s


async def _setup_zone_with_element(db, building_id, element_type="wall", condition="good"):
    zone = Zone(
        id=uuid.uuid4(),
        building_id=building_id,
        zone_type="floor",
        name="Floor 1",
    )
    db.add(zone)
    await db.commit()

    el = BuildingElement(
        id=uuid.uuid4(),
        zone_id=zone.id,
        element_type=element_type,
        name=f"Element {element_type}",
        condition=condition,
    )
    db.add(el)
    await db.commit()
    return zone, el


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_infer_asbestos_friable():
    s = Sample(pollutant_type="asbestos", material_state="friable")
    assert _infer_material_type(s) == "asbestos_friable"


@pytest.mark.asyncio
async def test_infer_asbestos_bonded():
    s = Sample(pollutant_type="asbestos", material_state="bonded")
    assert _infer_material_type(s) == "asbestos_bonded"


@pytest.mark.asyncio
async def test_infer_pcb():
    s = Sample(pollutant_type="pcb", material_state=None)
    assert _infer_material_type(s) == "pcb_joint"


@pytest.mark.asyncio
async def test_compute_stress_factor_high_freeze():
    stress = _compute_climate_stress_factor("asbestos_friable", {"freeze_thaw": 1.0, "uv": 0.5, "moisture": 0.8})
    assert stress > 0.4  # High sensitivity material + high exposure


@pytest.mark.asyncio
async def test_compute_stress_factor_zero():
    stress = _compute_climate_stress_factor("asbestos_friable", {"freeze_thaw": 0, "uv": 0, "moisture": 0})
    assert stress == 0.0


@pytest.mark.asyncio
async def test_project_condition_new_building():
    cond = _project_condition(5, 80, 0.2)
    assert cond == "good"


@pytest.mark.asyncio
async def test_project_condition_old_high_stress():
    cond = _project_condition(60, 50, 0.5)
    assert cond == "critical"


@pytest.mark.asyncio
async def test_predict_building_not_found(db_session):
    with pytest.raises(ValueError, match="not found"):
        await predict_degradation(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_predict_with_asbestos_sample(db_session):
    user = await _setup_user(db_session)
    building = await _setup_building(db_session, user, construction_year=1965)
    await _setup_diagnostic_with_sample(
        db_session,
        building.id,
        pollutant="asbestos",
        exceeded=True,
        material_state="friable",
    )

    results = await predict_degradation(db_session, building.id)
    assert len(results) >= 1
    first = results[0]
    assert first["material"] == "asbestos_friable"
    assert "climate_stress_factor" in first
    assert "projected_condition" in first
    assert "years_to_critical" in first
    assert "recommendation" in first


@pytest.mark.asyncio
async def test_predict_with_concrete_elements(db_session):
    user = await _setup_user(db_session)
    building = await _setup_building(db_session, user, construction_year=1960)
    await _setup_zone_with_element(db_session, building.id, element_type="structural", condition="fair")

    results = await predict_degradation(db_session, building.id)
    # Should include concrete from structural elements
    materials = [r["material"] for r in results]
    assert "concrete" in materials
