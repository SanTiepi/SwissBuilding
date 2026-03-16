"""Tests for the Remediation Cost Estimation Service and API."""

from __future__ import annotations

import uuid

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.services.remediation_cost_service import (
    compare_building_costs,
    estimate_building_cost,
    estimate_pollutant_cost,
    get_cost_factors,
)

# ── Helpers ────────────────────────────────────────────────────────


async def _create_building(db, admin_user, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Test 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1975,
        "building_type": "residential",
        "surface_area_m2": 500.0,
        "floors_above": 3,
        "floors_below": 1,
        "created_by": admin_user.id,
        "status": "active",
    }
    defaults.update(kwargs)
    b = Building(**defaults)
    db.add(b)
    await db.flush()
    return b


async def _create_diagnostic(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "diagnostic_type": "asbestos",
        "status": "completed",
    }
    defaults.update(kwargs)
    d = Diagnostic(**defaults)
    db.add(d)
    await db.flush()
    return d


async def _create_sample(db, diagnostic_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "diagnostic_id": diagnostic_id,
        "sample_number": f"S-{uuid.uuid4().hex[:6]}",
        "pollutant_type": "asbestos",
        "cfst_work_category": "minor",
        "waste_disposal_type": "type_b",
        "risk_level": "medium",
        "material_category": "insulation",
    }
    defaults.update(kwargs)
    s = Sample(**defaults)
    db.add(s)
    await db.flush()
    return s


# ── Service tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_empty_building_zero_cost(db_session, admin_user):
    """Building with no diagnostics should return zero cost."""
    b = await _create_building(db_session, admin_user)
    await db_session.commit()

    result = await estimate_building_cost(db_session, b.id)
    assert result.total_min_chf == 0.0
    assert result.total_max_chf == 0.0
    assert result.waste_cost_chf == 0.0
    assert result.safety_cost_chf == 0.0
    assert result.lab_cost_chf == 0.0
    assert result.timeline_weeks_estimate == 0
    assert result.pollutant_breakdowns == []


@pytest.mark.asyncio
async def test_asbestos_minor(db_session, admin_user):
    """Asbestos minor work category cost calculation."""
    b = await _create_building(db_session, admin_user, surface_area_m2=200.0)
    d = await _create_diagnostic(db_session, b.id)
    await _create_sample(db_session, d.id, pollutant_type="asbestos", cfst_work_category="minor")
    await db_session.commit()

    result = await estimate_building_cost(db_session, b.id)
    assert len(result.pollutant_breakdowns) == 1
    bd = result.pollutant_breakdowns[0]
    assert bd.pollutant_type == "asbestos"
    assert bd.work_category == "minor"
    # 45 CHF/m² * 200 m² * 1.2 (pre-1991) = 10800
    assert bd.unit_cost_chf == 45.0
    assert bd.subtotal_chf == 10800.0


@pytest.mark.asyncio
async def test_asbestos_medium(db_session, admin_user):
    """Asbestos medium work category."""
    b = await _create_building(db_session, admin_user, surface_area_m2=100.0)
    d = await _create_diagnostic(db_session, b.id)
    await _create_sample(db_session, d.id, pollutant_type="asbestos", cfst_work_category="medium")
    await db_session.commit()

    result = await estimate_pollutant_cost(db_session, b.id, "asbestos")
    assert result.unit_cost_chf == 120.0
    # 120 * 100 * 1.2 = 14400
    assert result.subtotal_chf == 14400.0


@pytest.mark.asyncio
async def test_asbestos_major(db_session, admin_user):
    """Asbestos major work category."""
    b = await _create_building(db_session, admin_user, surface_area_m2=100.0)
    d = await _create_diagnostic(db_session, b.id)
    await _create_sample(db_session, d.id, pollutant_type="asbestos", cfst_work_category="major")
    await db_session.commit()

    result = await estimate_pollutant_cost(db_session, b.id, "asbestos")
    assert result.unit_cost_chf == 280.0
    # 280 * 100 * 1.2 = 33600
    assert result.subtotal_chf == 33600.0


@pytest.mark.asyncio
async def test_pcb_joints(db_session, admin_user):
    """PCB cost for joints material."""
    b = await _create_building(db_session, admin_user, surface_area_m2=100.0)
    d = await _create_diagnostic(db_session, b.id, diagnostic_type="pcb")
    await _create_sample(
        db_session,
        d.id,
        pollutant_type="pcb",
        material_category="joints",
        cfst_work_category=None,
        waste_disposal_type=None,
    )
    await db_session.commit()

    result = await estimate_pollutant_cost(db_session, b.id, "pcb")
    assert result.unit_cost_chf == 150.0


@pytest.mark.asyncio
async def test_pcb_coatings(db_session, admin_user):
    """PCB cost for coatings material."""
    b = await _create_building(db_session, admin_user, surface_area_m2=100.0)
    d = await _create_diagnostic(db_session, b.id, diagnostic_type="pcb")
    await _create_sample(
        db_session,
        d.id,
        pollutant_type="pcb",
        material_category="coatings",
        cfst_work_category=None,
        waste_disposal_type=None,
    )
    await db_session.commit()

    result = await estimate_pollutant_cost(db_session, b.id, "pcb")
    assert result.unit_cost_chf == 200.0


@pytest.mark.asyncio
async def test_lead_rate(db_session, admin_user):
    """Lead paint removal rate."""
    b = await _create_building(db_session, admin_user, surface_area_m2=100.0)
    d = await _create_diagnostic(db_session, b.id, diagnostic_type="lead")
    await _create_sample(
        db_session,
        d.id,
        pollutant_type="lead",
        cfst_work_category=None,
        waste_disposal_type=None,
    )
    await db_session.commit()

    result = await estimate_pollutant_cost(db_session, b.id, "lead")
    assert result.unit_cost_chf == 80.0
    # 80 * 100 * 1.2 = 9600
    assert result.subtotal_chf == 9600.0


@pytest.mark.asyncio
async def test_hap_rate(db_session, admin_user):
    """HAP remediation rate."""
    b = await _create_building(db_session, admin_user, surface_area_m2=100.0)
    d = await _create_diagnostic(db_session, b.id, diagnostic_type="hap")
    await _create_sample(
        db_session,
        d.id,
        pollutant_type="hap",
        cfst_work_category=None,
        waste_disposal_type=None,
    )
    await db_session.commit()

    result = await estimate_pollutant_cost(db_session, b.id, "hap")
    assert result.unit_cost_chf == 100.0
    # 100 * 100 * 1.2 = 12000
    assert result.subtotal_chf == 12000.0


@pytest.mark.asyncio
async def test_radon_fixed_plus_variable(db_session, admin_user):
    """Radon: fixed 5000 CHF + 15 CHF/m² * surface."""
    b = await _create_building(db_session, admin_user, surface_area_m2=200.0)
    d = await _create_diagnostic(db_session, b.id, diagnostic_type="radon")
    await _create_sample(
        db_session,
        d.id,
        pollutant_type="radon",
        cfst_work_category=None,
        waste_disposal_type=None,
    )
    await db_session.commit()

    result = await estimate_pollutant_cost(db_session, b.id, "radon")
    # (5000 + 15 * 200) * 1.2 = (5000 + 3000) * 1.2 = 9600
    assert result.subtotal_chf == 9600.0
    assert result.unit_cost_chf == 15.0


@pytest.mark.asyncio
async def test_cost_range_min_max(db_session, admin_user):
    """Total min/max should be ±30% of base total."""
    b = await _create_building(db_session, admin_user, surface_area_m2=100.0, floors_above=1, floors_below=0)
    d = await _create_diagnostic(db_session, b.id)
    await _create_sample(
        db_session,
        d.id,
        pollutant_type="asbestos",
        cfst_work_category="minor",
        waste_disposal_type=None,
    )
    await db_session.commit()

    result = await estimate_building_cost(db_session, b.id)
    # Remediation: 45 * 100 * 1.2 = 5400
    # Lab: 150 * 1 = 150
    # Safety: 1 * (3000 + 500 * 1) = 3500
    # Total base = 5400 + 0 + 150 + 3500 = 9050
    expected_base = 9050.0
    assert result.total_min_chf == pytest.approx(expected_base * 0.7, rel=1e-2)
    assert result.total_max_chf == pytest.approx(expected_base * 1.3, rel=1e-2)


@pytest.mark.asyncio
async def test_waste_surcharge_type_b(db_session, admin_user):
    """Waste surcharge for type_b = 20% of subtotal."""
    b = await _create_building(db_session, admin_user, surface_area_m2=100.0)
    d = await _create_diagnostic(db_session, b.id)
    await _create_sample(
        db_session,
        d.id,
        pollutant_type="asbestos",
        cfst_work_category="minor",
        waste_disposal_type="type_b",
    )
    await db_session.commit()

    result = await estimate_pollutant_cost(db_session, b.id, "asbestos")
    # subtotal = 45 * 100 * 1.2 = 5400
    # waste = 5400 * 0.20 = 1080
    assert result.waste_surcharge_chf == 1080.0


@pytest.mark.asyncio
async def test_waste_surcharge_type_e(db_session, admin_user):
    """Waste surcharge for type_e = 35%."""
    b = await _create_building(db_session, admin_user, surface_area_m2=100.0)
    d = await _create_diagnostic(db_session, b.id)
    await _create_sample(
        db_session,
        d.id,
        pollutant_type="asbestos",
        cfst_work_category="minor",
        waste_disposal_type="type_e",
    )
    await db_session.commit()

    result = await estimate_pollutant_cost(db_session, b.id, "asbestos")
    # 5400 * 0.35 = 1890
    assert result.waste_surcharge_chf == 1890.0


@pytest.mark.asyncio
async def test_waste_surcharge_special(db_session, admin_user):
    """Waste surcharge for special = 50%."""
    b = await _create_building(db_session, admin_user, surface_area_m2=100.0)
    d = await _create_diagnostic(db_session, b.id)
    await _create_sample(
        db_session,
        d.id,
        pollutant_type="asbestos",
        cfst_work_category="minor",
        waste_disposal_type="special",
    )
    await db_session.commit()

    result = await estimate_pollutant_cost(db_session, b.id, "asbestos")
    # 5400 * 0.50 = 2700
    assert result.waste_surcharge_chf == 2700.0


@pytest.mark.asyncio
async def test_safety_cost_varies_by_floors(db_session, admin_user):
    """Safety cost: 3000 base + 500/floor."""
    b1 = await _create_building(db_session, admin_user, floors_above=2, floors_below=0, surface_area_m2=100.0)
    d1 = await _create_diagnostic(db_session, b1.id)
    await _create_sample(db_session, d1.id, pollutant_type="asbestos", waste_disposal_type=None)
    await db_session.commit()

    r1 = await estimate_building_cost(db_session, b1.id)
    # floors=2, safety = 1 * (3000 + 500*2) = 4000
    assert r1.safety_cost_chf == 4000.0


@pytest.mark.asyncio
async def test_safety_cost_multiple_floors(db_session, admin_user):
    """Safety cost with many floors."""
    b = await _create_building(db_session, admin_user, floors_above=5, floors_below=2, surface_area_m2=100.0)
    d = await _create_diagnostic(db_session, b.id)
    await _create_sample(db_session, d.id, pollutant_type="asbestos", waste_disposal_type=None)
    await db_session.commit()

    result = await estimate_building_cost(db_session, b.id)
    # floors=7, safety = 1 * (3000 + 500*7) = 6500
    assert result.safety_cost_chf == 6500.0


@pytest.mark.asyncio
async def test_lab_cost_from_sample_count(db_session, admin_user):
    """Lab costs: 150 CHF per asbestos sample."""
    b = await _create_building(db_session, admin_user, surface_area_m2=100.0)
    d = await _create_diagnostic(db_session, b.id)
    await _create_sample(db_session, d.id, pollutant_type="asbestos", waste_disposal_type=None)
    await _create_sample(db_session, d.id, pollutant_type="asbestos", waste_disposal_type=None)
    await _create_sample(db_session, d.id, pollutant_type="asbestos", waste_disposal_type=None)
    await db_session.commit()

    result = await estimate_building_cost(db_session, b.id)
    # 3 samples * 150 CHF = 450
    assert result.lab_cost_chf == 450.0


@pytest.mark.asyncio
async def test_lab_cost_pcb(db_session, admin_user):
    """Lab costs: 200 CHF per PCB sample."""
    b = await _create_building(db_session, admin_user, surface_area_m2=100.0)
    d = await _create_diagnostic(db_session, b.id, diagnostic_type="pcb")
    await _create_sample(
        db_session,
        d.id,
        pollutant_type="pcb",
        cfst_work_category=None,
        waste_disposal_type=None,
    )
    await _create_sample(
        db_session,
        d.id,
        pollutant_type="pcb",
        cfst_work_category=None,
        waste_disposal_type=None,
    )
    await db_session.commit()

    result = await estimate_building_cost(db_session, b.id)
    # 2 * 200 = 400
    assert result.lab_cost_chf == 400.0


@pytest.mark.asyncio
async def test_multiple_pollutants(db_session, admin_user):
    """Building with asbestos + lead should sum both."""
    b = await _create_building(db_session, admin_user, surface_area_m2=100.0)
    d1 = await _create_diagnostic(db_session, b.id, diagnostic_type="asbestos")
    await _create_sample(
        db_session,
        d1.id,
        pollutant_type="asbestos",
        cfst_work_category="minor",
        waste_disposal_type=None,
    )
    d2 = await _create_diagnostic(db_session, b.id, diagnostic_type="lead")
    await _create_sample(
        db_session,
        d2.id,
        pollutant_type="lead",
        cfst_work_category=None,
        waste_disposal_type=None,
    )
    await db_session.commit()

    result = await estimate_building_cost(db_session, b.id)
    assert len(result.pollutant_breakdowns) == 2
    types = {bd.pollutant_type for bd in result.pollutant_breakdowns}
    assert types == {"asbestos", "lead"}
    # Safety: 2 pollutants * (3000 + 500*4) = 2 * 5000 = 10000
    assert result.safety_cost_chf == 10000.0
    # Timeline: 2 * 3 = 6 weeks
    assert result.timeline_weeks_estimate == 6


@pytest.mark.asyncio
async def test_age_factor_post_1991(db_session, admin_user):
    """Post-1991 building should have age_factor = 1.0."""
    b = await _create_building(db_session, admin_user, construction_year=2005, surface_area_m2=100.0)
    d = await _create_diagnostic(db_session, b.id)
    await _create_sample(
        db_session,
        d.id,
        pollutant_type="asbestos",
        cfst_work_category="minor",
        waste_disposal_type=None,
    )
    await db_session.commit()

    result = await estimate_pollutant_cost(db_session, b.id, "asbestos")
    # 45 * 100 * 1.0 = 4500 (no age surcharge)
    assert result.subtotal_chf == 4500.0


@pytest.mark.asyncio
async def test_cost_factors_basic(db_session, admin_user):
    """Cost factors for a building with diagnostics."""
    b = await _create_building(db_session, admin_user, surface_area_m2=300.0, floors_above=3, floors_below=1)
    d = await _create_diagnostic(db_session, b.id)
    await _create_sample(
        db_session,
        d.id,
        pollutant_type="asbestos",
        cfst_work_category="major",
        risk_level="critical",
        waste_disposal_type="special",
    )
    await db_session.commit()

    factors = await get_cost_factors(db_session, b.id)
    assert factors.building_id == b.id
    assert factors.age_factor == 1.2  # pre-1991
    assert factors.floors_factor == 1.3  # 4 floors -> 1 + 3*0.1
    assert factors.pollutant_count == 1
    assert factors.surface_area_m2 == 300.0
    assert "asbestos_critical" in factors.urgency_flags
    assert "asbestos_major_works" in factors.urgency_flags
    assert "asbestos_special_waste" in factors.urgency_flags


@pytest.mark.asyncio
async def test_cost_factors_no_pollutants(db_session, admin_user):
    """Cost factors with no diagnostics."""
    b = await _create_building(db_session, admin_user, construction_year=2010, surface_area_m2=150.0)
    await db_session.commit()

    factors = await get_cost_factors(db_session, b.id)
    assert factors.age_factor == 1.0
    assert factors.pollutant_count == 0
    assert factors.urgency_flags == []


@pytest.mark.asyncio
async def test_compare_ranking(db_session, admin_user):
    """Compare buildings: higher cost ranked first."""
    b1 = await _create_building(db_session, admin_user, surface_area_m2=100.0, address="Cheap St 1")
    b2 = await _create_building(db_session, admin_user, surface_area_m2=500.0, address="Expensive St 2")

    d1 = await _create_diagnostic(db_session, b1.id)
    await _create_sample(
        db_session,
        d1.id,
        pollutant_type="asbestos",
        cfst_work_category="minor",
        waste_disposal_type=None,
    )
    d2 = await _create_diagnostic(db_session, b2.id)
    await _create_sample(
        db_session,
        d2.id,
        pollutant_type="asbestos",
        cfst_work_category="major",
        waste_disposal_type=None,
    )
    await db_session.commit()

    results = await compare_building_costs(db_session, [b1.id, b2.id])
    assert len(results) == 2
    # b2 should rank first (higher cost)
    assert results[0].building_id == b2.id
    assert results[0].rank == 1
    assert results[1].building_id == b1.id
    assert results[1].rank == 2


@pytest.mark.asyncio
async def test_compare_cost_per_m2(db_session, admin_user):
    """Compare should compute cost_per_m2."""
    b = await _create_building(db_session, admin_user, surface_area_m2=200.0)
    d = await _create_diagnostic(db_session, b.id)
    await _create_sample(
        db_session,
        d.id,
        pollutant_type="asbestos",
        cfst_work_category="minor",
        waste_disposal_type=None,
    )
    await db_session.commit()

    results = await compare_building_costs(db_session, [b.id])
    assert len(results) == 1
    assert results[0].cost_per_m2 > 0
    assert results[0].total_estimate_chf > 0


@pytest.mark.asyncio
async def test_compare_primary_cost_driver(db_session, admin_user):
    """Compare should identify primary cost driver."""
    b = await _create_building(db_session, admin_user, surface_area_m2=100.0)
    d1 = await _create_diagnostic(db_session, b.id, diagnostic_type="asbestos")
    await _create_sample(
        db_session,
        d1.id,
        pollutant_type="asbestos",
        cfst_work_category="major",
        waste_disposal_type=None,
    )
    d2 = await _create_diagnostic(db_session, b.id, diagnostic_type="lead")
    await _create_sample(
        db_session,
        d2.id,
        pollutant_type="lead",
        cfst_work_category=None,
        waste_disposal_type=None,
    )
    await db_session.commit()

    results = await compare_building_costs(db_session, [b.id])
    # Asbestos major (280) > lead (80), so asbestos is the driver
    assert results[0].primary_cost_driver == "asbestos"


@pytest.mark.asyncio
async def test_compare_too_many_buildings(db_session, admin_user):
    """Compare with > 10 buildings should raise ValueError."""
    ids = [uuid.uuid4() for _ in range(11)]
    with pytest.raises(ValueError, match="Cannot compare more than 10"):
        await compare_building_costs(db_session, ids)


@pytest.mark.asyncio
async def test_building_not_found(db_session):
    """Non-existent building should raise ValueError."""
    fake_id = uuid.uuid4()
    with pytest.raises(ValueError, match="not found"):
        await estimate_building_cost(db_session, fake_id)


@pytest.mark.asyncio
async def test_draft_diagnostic_excluded(db_session, admin_user):
    """Draft diagnostics should not be counted."""
    b = await _create_building(db_session, admin_user, surface_area_m2=100.0)
    d = await _create_diagnostic(db_session, b.id, status="draft")
    await _create_sample(
        db_session,
        d.id,
        pollutant_type="asbestos",
        cfst_work_category="minor",
        waste_disposal_type=None,
    )
    await db_session.commit()

    result = await estimate_building_cost(db_session, b.id)
    assert result.total_min_chf == 0.0
    assert result.pollutant_breakdowns == []


# ── API tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_api_get_remediation_costs(client, db_session, admin_user, auth_headers):
    """GET /buildings/{id}/remediation-costs returns estimate."""
    b = await _create_building(db_session, admin_user, surface_area_m2=100.0)
    d = await _create_diagnostic(db_session, b.id)
    await _create_sample(db_session, d.id, pollutant_type="asbestos", waste_disposal_type=None)
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{b.id}/remediation-costs", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(b.id)
    assert "pollutant_breakdowns" in data
    assert data["total_min_chf"] >= 0


@pytest.mark.asyncio
async def test_api_get_pollutant_cost(client, db_session, admin_user, auth_headers):
    """GET /buildings/{id}/remediation-costs/asbestos returns breakdown."""
    b = await _create_building(db_session, admin_user, surface_area_m2=100.0)
    d = await _create_diagnostic(db_session, b.id)
    await _create_sample(db_session, d.id, pollutant_type="asbestos", waste_disposal_type=None)
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{b.id}/remediation-costs/asbestos", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["pollutant_type"] == "asbestos"


@pytest.mark.asyncio
async def test_api_compare_costs(client, db_session, admin_user, auth_headers):
    """POST /remediation-costs/compare returns ranked list."""
    b1 = await _create_building(db_session, admin_user, surface_area_m2=100.0)
    b2 = await _create_building(db_session, admin_user, surface_area_m2=200.0)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/remediation-costs/compare",
        json={"building_ids": [str(b1.id), str(b2.id)]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_api_cost_factors(client, db_session, admin_user, auth_headers):
    """GET /buildings/{id}/cost-factors returns factors."""
    b = await _create_building(db_session, admin_user, surface_area_m2=100.0)
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{b.id}/cost-factors", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(b.id)
    assert "age_factor" in data
    assert "urgency_flags" in data


@pytest.mark.asyncio
async def test_api_not_found(client, auth_headers):
    """404 for non-existent building."""
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/buildings/{fake_id}/remediation-costs", headers=auth_headers)
    assert resp.status_code == 404
