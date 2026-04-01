"""Tests for the RénoPredict cost prediction module."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import String

from app.models.remediation_cost_reference import RemediationCostReference
from app.schemas.cost_prediction import CostPredictionRequest
from app.services.cost_predictor_service import (
    ACCESSIBILITY_COEFFICIENTS,
    BREAKDOWN_TEMPLATE,
    CANTON_COEFFICIENTS,
    CONDITION_COEFFICIENTS,
    CostPredictionError,
    predict_cost,
)

# ── Ensure table exists (model not in conftest hub imports) ───────


@pytest.fixture(autouse=True, scope="module")
async def _ensure_cost_table(_engine):
    """Create the remediation_cost_references table if missing."""
    from geoalchemy2 import Geometry
    from sqlalchemy import MetaData, inspect

    async with _engine.begin() as conn:
        tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
        if "remediation_cost_references" not in tables:
            meta = MetaData()
            src_table = RemediationCostReference.__table__
            new_table = src_table.to_metadata(meta)
            for col in new_table.columns:
                if isinstance(src_table.columns[col.name].type, Geometry):
                    col.type = String()
                    col.nullable = True
            await conn.run_sync(meta.create_all)


# ── Helpers ────────────────────────────────────────────────────────


async def _seed_reference(db, **kwargs):
    """Insert a RemediationCostReference with sensible defaults."""
    defaults = {
        "id": uuid.uuid4(),
        "pollutant_type": "asbestos",
        "material_type": "flocage",
        "condition": "degrade",
        "method": "depose",
        "cost_per_m2_min": 150,
        "cost_per_m2_median": 250,
        "cost_per_m2_max": 350,
        "is_forfait": False,
        "duration_days_estimate": 30,
        "complexity": "complexe",
        "active": True,
    }
    defaults.update(kwargs)
    ref = RemediationCostReference(**defaults)
    db.add(ref)
    await db.flush()
    return ref


async def _seed_all_references(db):
    """Seed the full set of cost references for integration-style tests."""
    refs = [
        {
            "pollutant_type": "asbestos",
            "material_type": "flocage",
            "cost_per_m2_min": 150,
            "cost_per_m2_median": 250,
            "cost_per_m2_max": 350,
            "complexity": "complexe",
            "duration_days_estimate": 30,
        },
        {
            "pollutant_type": "asbestos",
            "material_type": "dalle_vinyle",
            "cost_per_m2_min": 50,
            "cost_per_m2_median": 85,
            "cost_per_m2_max": 120,
            "complexity": "moyenne",
            "duration_days_estimate": 10,
        },
        {
            "pollutant_type": "pcb",
            "material_type": "joint",
            "cost_per_m2_min": 100,
            "cost_per_m2_median": 175,
            "cost_per_m2_max": 250,
            "complexity": "moyenne",
            "duration_days_estimate": 15,
        },
        {
            "pollutant_type": "lead",
            "material_type": "peinture",
            "method": "decapage",
            "cost_per_m2_min": 60,
            "cost_per_m2_median": 105,
            "cost_per_m2_max": 150,
            "complexity": "simple",
            "duration_days_estimate": 7,
        },
        {
            "pollutant_type": "hap",
            "material_type": "revetement",
            "cost_per_m2_min": 80,
            "cost_per_m2_median": 140,
            "cost_per_m2_max": 200,
            "complexity": "moyenne",
            "duration_days_estimate": 15,
        },
        {
            "pollutant_type": "radon",
            "material_type": "other",
            "condition": "bon",
            "method": "ventilation",
            "cost_per_m2_min": None,
            "cost_per_m2_median": None,
            "cost_per_m2_max": None,
            "is_forfait": True,
            "forfait_min": 5000,
            "forfait_median": 10000,
            "forfait_max": 15000,
            "complexity": "simple",
            "duration_days_estimate": 5,
        },
        {
            "pollutant_type": "pfas",
            "material_type": "other",
            "cost_per_m2_min": 100,
            "cost_per_m2_median": 200,
            "cost_per_m2_max": 300,
            "complexity": "complexe",
            "duration_days_estimate": 22,
        },
    ]
    for r in refs:
        await _seed_reference(db, **r)
    await db.flush()


# ── Basic prediction tests ────────────────────────────────────────


@pytest.mark.asyncio
async def test_predict_asbestos_flocage_basic(db_session):
    """Asbestos flocage 100m² VD normal → 15000/25000/35000."""
    await _seed_reference(db_session)
    req = CostPredictionRequest(
        pollutant_type="asbestos",
        material_type="flocage",
        condition="degrade",
        surface_m2=100,
        canton="VD",
        accessibility="normal",
    )
    resp = await predict_cost(db_session, req)
    assert resp.pollutant_type == "asbestos"
    assert resp.material_type == "flocage"
    assert resp.surface_m2 == 100
    # VD=1.0, normal=1.0, degrade=1.0 → 150*100, 250*100, 350*100
    assert resp.cost_min == 15000.0
    assert resp.cost_median == 25000.0
    assert resp.cost_max == 35000.0
    assert resp.complexity == "complexe"
    assert resp.method == "depose"
    assert resp.duration_days == 30


@pytest.mark.asyncio
async def test_predict_asbestos_dalle_vinyle(db_session):
    """Asbestos dalle_vinyle 200m²."""
    await _seed_reference(
        db_session,
        material_type="dalle_vinyle",
        cost_per_m2_min=50,
        cost_per_m2_median=85,
        cost_per_m2_max=120,
        complexity="moyenne",
        duration_days_estimate=10,
    )
    req = CostPredictionRequest(
        pollutant_type="asbestos",
        material_type="dalle_vinyle",
        surface_m2=200,
    )
    resp = await predict_cost(db_session, req)
    assert resp.cost_min == 10000.0  # 50*200
    assert resp.cost_median == 17000.0  # 85*200
    assert resp.cost_max == 24000.0  # 120*200
    assert resp.complexity == "moyenne"


@pytest.mark.asyncio
async def test_predict_pcb_joint(db_session):
    """PCB joint 50m²."""
    await _seed_reference(
        db_session,
        pollutant_type="pcb",
        material_type="joint",
        cost_per_m2_min=100,
        cost_per_m2_median=175,
        cost_per_m2_max=250,
        complexity="moyenne",
        duration_days_estimate=15,
    )
    req = CostPredictionRequest(
        pollutant_type="pcb",
        material_type="joint",
        surface_m2=50,
    )
    resp = await predict_cost(db_session, req)
    assert resp.cost_min == 5000.0
    assert resp.cost_median == 8750.0
    assert resp.cost_max == 12500.0


@pytest.mark.asyncio
async def test_predict_lead_peinture(db_session):
    """Lead peinture 80m²."""
    await _seed_reference(
        db_session,
        pollutant_type="lead",
        material_type="peinture",
        method="decapage",
        cost_per_m2_min=60,
        cost_per_m2_median=105,
        cost_per_m2_max=150,
        complexity="simple",
        duration_days_estimate=7,
    )
    req = CostPredictionRequest(
        pollutant_type="lead",
        material_type="peinture",
        surface_m2=80,
    )
    resp = await predict_cost(db_session, req)
    assert resp.cost_min == 4800.0  # 60*80
    assert resp.cost_median == 8400.0  # 105*80
    assert resp.cost_max == 12000.0  # 150*80
    assert resp.method == "decapage"
    assert resp.complexity == "simple"


@pytest.mark.asyncio
async def test_predict_radon_forfait(db_session):
    """Radon is forfait — surface_m2 is irrelevant."""
    await _seed_reference(
        db_session,
        pollutant_type="radon",
        material_type="other",
        condition="bon",
        method="ventilation",
        cost_per_m2_min=None,
        cost_per_m2_median=None,
        cost_per_m2_max=None,
        is_forfait=True,
        forfait_min=5000,
        forfait_median=10000,
        forfait_max=15000,
        complexity="simple",
        duration_days_estimate=5,
    )
    req = CostPredictionRequest(
        pollutant_type="radon",
        material_type="other",
        surface_m2=0,
        canton="VD",
        accessibility="normal",
        condition="bon",
    )
    resp = await predict_cost(db_session, req)
    # Forfait with bon=0.85, VD=1.0, normal=1.0 → 5000*0.85, 10000*0.85, 15000*0.85
    assert resp.cost_min == 4250.0
    assert resp.cost_median == 8500.0
    assert resp.cost_max == 12750.0
    assert resp.surface_m2 == 0.0
    assert resp.method == "ventilation"


# ── Canton coefficient tests ──────────────────────────────────────


@pytest.mark.asyncio
async def test_predict_with_canton_ge_coefficient(db_session):
    """GE has 1.15 coefficient — costs should be 15% higher."""
    await _seed_reference(db_session)
    req = CostPredictionRequest(
        pollutant_type="asbestos",
        material_type="flocage",
        surface_m2=100,
        canton="GE",
    )
    resp = await predict_cost(db_session, req)
    assert resp.canton_coefficient == 1.15
    # 150*100*1.15*1.0*1.0 = 17250
    assert resp.cost_min == 17250.0
    assert resp.cost_median == 28750.0
    assert resp.cost_max == 40250.0


@pytest.mark.asyncio
async def test_predict_with_canton_vs_coefficient(db_session):
    """VS has 0.95 coefficient — costs should be 5% lower."""
    await _seed_reference(db_session)
    req = CostPredictionRequest(
        pollutant_type="asbestos",
        material_type="flocage",
        surface_m2=100,
        canton="VS",
    )
    resp = await predict_cost(db_session, req)
    assert resp.canton_coefficient == 0.95
    assert resp.cost_min == 14250.0  # 150*100*0.95
    assert resp.cost_median == 23750.0  # 250*100*0.95
    assert resp.cost_max == 33250.0  # 350*100*0.95


@pytest.mark.asyncio
async def test_canton_not_covered_uses_default(db_session):
    """Unknown canton falls back to coefficient 1.0."""
    await _seed_reference(db_session)
    req = CostPredictionRequest(
        pollutant_type="asbestos",
        material_type="flocage",
        surface_m2=100,
        canton="TI",
    )
    resp = await predict_cost(db_session, req)
    assert resp.canton_coefficient == 1.0
    assert resp.cost_min == 15000.0


# ── Accessibility tests ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_predict_difficult_accessibility(db_session):
    """Difficult access multiplies costs by 1.3."""
    await _seed_reference(db_session)
    req = CostPredictionRequest(
        pollutant_type="asbestos",
        material_type="flocage",
        surface_m2=100,
        accessibility="difficile",
    )
    resp = await predict_cost(db_session, req)
    assert resp.accessibility_coefficient == 1.3
    assert resp.cost_min == 19500.0  # 150*100*1.3
    assert resp.cost_median == 32500.0  # 250*100*1.3
    assert resp.cost_max == 45500.0  # 350*100*1.3


@pytest.mark.asyncio
async def test_predict_tres_difficile_accessibility(db_session):
    """Très difficile access multiplies costs by 1.6."""
    await _seed_reference(db_session)
    req = CostPredictionRequest(
        pollutant_type="asbestos",
        material_type="flocage",
        surface_m2=10,
        accessibility="tres_difficile",
    )
    resp = await predict_cost(db_session, req)
    assert resp.accessibility_coefficient == 1.6
    assert resp.cost_min == 2400.0  # 150*10*1.6
    assert resp.cost_median == 4000.0  # 250*10*1.6
    assert resp.cost_max == 5600.0  # 350*10*1.6


# ── Condition coefficient tests ───────────────────────────────────


@pytest.mark.asyncio
async def test_predict_friable_condition_increases_cost(db_session):
    """Friable condition multiplies costs by 1.25."""
    await _seed_reference(db_session)
    req = CostPredictionRequest(
        pollutant_type="asbestos",
        material_type="flocage",
        condition="friable",
        surface_m2=100,
    )
    resp = await predict_cost(db_session, req)
    assert resp.cost_min == 18750.0  # 150*100*1.25
    assert resp.cost_median == 31250.0  # 250*100*1.25
    assert resp.cost_max == 43750.0  # 350*100*1.25


@pytest.mark.asyncio
async def test_predict_bon_condition_reduces_cost(db_session):
    """Bon condition multiplies costs by 0.85."""
    await _seed_reference(db_session)
    req = CostPredictionRequest(
        pollutant_type="asbestos",
        material_type="flocage",
        condition="bon",
        surface_m2=100,
    )
    resp = await predict_cost(db_session, req)
    assert resp.cost_min == 12750.0  # 150*100*0.85
    assert resp.cost_median == 21250.0  # 250*100*0.85
    assert resp.cost_max == 29750.0  # 350*100*0.85


# ── Error handling tests ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_predict_surface_zero_returns_error_for_non_forfait(db_session):
    """surface_m2=0 for a non-forfait reference should raise an error."""
    await _seed_reference(db_session)
    req = CostPredictionRequest(
        pollutant_type="asbestos",
        material_type="flocage",
        surface_m2=0,
    )
    with pytest.raises(CostPredictionError, match="surface_m2 must be > 0"):
        await predict_cost(db_session, req)


@pytest.mark.asyncio
async def test_predict_unknown_pollutant_returns_error(db_session):
    """Unknown pollutant type should raise validation error."""
    req = CostPredictionRequest(
        pollutant_type="mercury",
        material_type="flocage",
        surface_m2=100,
    )
    with pytest.raises(CostPredictionError, match="Unknown pollutant_type"):
        await predict_cost(db_session, req)


@pytest.mark.asyncio
async def test_predict_unknown_material_fallback(db_session):
    """Unknown material falls back to 'other' for the pollutant."""
    await _seed_reference(
        db_session,
        pollutant_type="pfas",
        material_type="other",
        cost_per_m2_min=100,
        cost_per_m2_median=200,
        cost_per_m2_max=300,
        complexity="complexe",
    )
    req = CostPredictionRequest(
        pollutant_type="pfas",
        material_type="unknown_material",
        surface_m2=50,
    )
    resp = await predict_cost(db_session, req)
    # Falls back to pfas/other
    assert resp.material_type == "unknown_material"
    assert resp.cost_min == 5000.0  # 100*50


@pytest.mark.asyncio
async def test_predict_no_reference_at_all(db_session):
    """No reference for pollutant/material and no 'other' fallback → 404."""
    req = CostPredictionRequest(
        pollutant_type="lead",
        material_type="flocage",
        surface_m2=100,
    )
    with pytest.raises(CostPredictionError, match="No cost reference found"):
        await predict_cost(db_session, req)


# ── Breakdown tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_breakdown_sums_to_100_percent(db_session):
    """All breakdown percentages should sum to 100%."""
    await _seed_reference(db_session)
    req = CostPredictionRequest(
        pollutant_type="asbestos",
        material_type="flocage",
        surface_m2=100,
    )
    resp = await predict_cost(db_session, req)
    total_pct = sum(item.percentage for item in resp.breakdown)
    assert abs(total_pct - 100.0) < 0.1  # floating point tolerance


@pytest.mark.asyncio
async def test_breakdown_amounts_sum_to_total(db_session):
    """Breakdown amount_median values should sum to the total cost_median."""
    await _seed_reference(db_session)
    req = CostPredictionRequest(
        pollutant_type="asbestos",
        material_type="flocage",
        surface_m2=100,
    )
    resp = await predict_cost(db_session, req)
    total_breakdown_median = sum(item.amount_median for item in resp.breakdown)
    assert abs(total_breakdown_median - resp.cost_median) < 1.0  # rounding tolerance


# ── Invariant tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_min_less_than_median_less_than_max(db_session):
    """cost_min <= cost_median <= cost_max for all predictions."""
    await _seed_reference(db_session)
    req = CostPredictionRequest(
        pollutant_type="asbestos",
        material_type="flocage",
        surface_m2=100,
        canton="GE",
        accessibility="difficile",
    )
    resp = await predict_cost(db_session, req)
    assert resp.cost_min <= resp.cost_median <= resp.cost_max


@pytest.mark.asyncio
async def test_disclaimer_always_present(db_session):
    """Response should always contain the disclaimer."""
    await _seed_reference(db_session)
    req = CostPredictionRequest(
        pollutant_type="asbestos",
        material_type="flocage",
        surface_m2=100,
    )
    resp = await predict_cost(db_session, req)
    assert "indicative" in resp.disclaimer.lower()


# ── Seed data test ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_seed_data_loaded(db_session):
    """Verify that seeding all references works and data is queryable."""
    await _seed_all_references(db_session)
    from sqlalchemy import func, select

    result = await db_session.execute(select(func.count()).select_from(RemediationCostReference))
    count = result.scalar()
    assert count >= 7  # We seed at least 7 references


# ── Combined coefficient tests ───────────────────────────────────


@pytest.mark.asyncio
async def test_combined_coefficients_ge_difficile_friable(db_session):
    """GE + difficile + friable should compound all three coefficients."""
    await _seed_reference(db_session)
    req = CostPredictionRequest(
        pollutant_type="asbestos",
        material_type="flocage",
        condition="friable",
        surface_m2=100,
        canton="GE",
        accessibility="difficile",
    )
    resp = await predict_cost(db_session, req)
    # GE=1.15, difficile=1.3, friable=1.25 → combined=1.15*1.3*1.25=1.86875
    expected_min = round(150 * 100 * 1.15 * 1.3 * 1.25, 2)
    assert resp.cost_min == expected_min


# ── Coefficient constant tests ───────────────────────────────────


def test_canton_coefficients_complete():
    """All main cantons should be covered."""
    for canton in ("VD", "GE", "ZH", "BE", "VS", "FR"):
        assert canton in CANTON_COEFFICIENTS


def test_accessibility_coefficients_complete():
    """All accessibility levels should be covered."""
    for level in ("facile", "normal", "difficile", "tres_difficile"):
        assert level in ACCESSIBILITY_COEFFICIENTS


def test_condition_coefficients_complete():
    """All condition levels should be covered."""
    for cond in ("bon", "degrade", "friable"):
        assert cond in CONDITION_COEFFICIENTS


def test_breakdown_template_sums_to_one():
    """Breakdown template percentages must sum to 1.0."""
    total = sum(pct for _, pct in BREAKDOWN_TEMPLATE)
    assert abs(total - 1.0) < 0.001
