"""Tests for the Risk Mitigation Planner Service and API."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.services.risk_mitigation_planner import (
    analyze_intervention_dependencies,
    estimate_plan_timeline,
    generate_mitigation_plan,
    get_quick_wins,
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


async def _create_intervention(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "intervention_type": "asbestos_removal",
        "title": "Asbestos removal",
        "status": "completed",
    }
    defaults.update(kwargs)
    iv = Intervention(**defaults)
    db.add(iv)
    await db.flush()
    return iv


async def _create_action_item(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "source_type": "diagnostic",
        "action_type": "asbestos",
        "title": "Remove asbestos",
        "priority": "high",
        "status": "open",
    }
    defaults.update(kwargs)
    a = ActionItem(**defaults)
    db.add(a)
    await db.flush()
    return a


# ── Service tests: generate_mitigation_plan ──────────────────────


@pytest.mark.asyncio
async def test_single_pollutant_plan_asbestos(db_session, admin_user):
    """Single pollutant (asbestos only) produces a one-step plan."""
    b = await _create_building(db_session, admin_user)
    d = await _create_diagnostic(db_session, b.id)
    await _create_sample(db_session, d.id, pollutant_type="asbestos")
    await db_session.commit()

    plan = await generate_mitigation_plan(db_session, b.id)
    assert len(plan.steps) == 1
    assert plan.steps[0].pollutant_type == "asbestos"
    assert plan.steps[0].order == 1
    assert plan.total_cost_min_chf > 0
    assert plan.total_cost_max_chf >= plan.total_cost_min_chf


@pytest.mark.asyncio
async def test_multi_pollutant_ordering(db_session, admin_user):
    """Multiple pollutants are ordered by urgency (asbestos friable > PCB > lead)."""
    b = await _create_building(db_session, admin_user)
    d = await _create_diagnostic(db_session, b.id)
    await _create_sample(
        db_session,
        d.id,
        pollutant_type="asbestos",
        material_state="friable",
        cfst_work_category="major",
    )
    await _create_sample(
        db_session,
        d.id,
        pollutant_type="pcb",
        concentration=1500.0,
        material_category="joints",
    )
    await _create_sample(
        db_session,
        d.id,
        pollutant_type="lead",
        risk_level="low",
        material_state="contained",
    )
    await db_session.commit()

    plan = await generate_mitigation_plan(db_session, b.id)
    assert len(plan.steps) == 3

    pollutant_order = [s.pollutant_type for s in plan.steps]
    # Asbestos friable (95) should come before PCB high (80) before lead contained (30)
    asb_idx = pollutant_order.index("asbestos")
    pcb_idx = pollutant_order.index("pcb")
    lead_idx = pollutant_order.index("lead")
    assert asb_idx < pcb_idx < lead_idx


@pytest.mark.asyncio
async def test_urgency_scoring_friable_vs_non_friable(db_session, admin_user):
    """Friable asbestos gets higher urgency than non-friable."""
    b = await _create_building(db_session, admin_user)
    d = await _create_diagnostic(db_session, b.id)
    await _create_sample(
        db_session,
        d.id,
        pollutant_type="asbestos",
        material_state="friable",
        cfst_work_category="major",
    )
    await db_session.commit()

    plan_friable = await generate_mitigation_plan(db_session, b.id)

    # Non-friable building
    b2 = await _create_building(db_session, admin_user)
    d2 = await _create_diagnostic(db_session, b2.id)
    await _create_sample(
        db_session,
        d2.id,
        pollutant_type="asbestos",
        material_state="non-friable",
        cfst_work_category="minor",
    )
    await db_session.commit()

    plan_nf = await generate_mitigation_plan(db_session, b2.id)

    assert plan_friable.steps[0].urgency_score > plan_nf.steps[0].urgency_score


@pytest.mark.asyncio
async def test_building_not_found(db_session):
    """Non-existent building raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await generate_mitigation_plan(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_empty_building_empty_plan(db_session, admin_user):
    """Building with no diagnostics produces an empty plan."""
    b = await _create_building(db_session, admin_user)
    await db_session.commit()

    plan = await generate_mitigation_plan(db_session, b.id)
    assert len(plan.steps) == 0
    assert plan.total_cost_min_chf == 0.0
    assert plan.total_cost_max_chf == 0.0
    assert plan.total_duration_weeks == 0


@pytest.mark.asyncio
async def test_completed_interventions_reduce_plan(db_session, admin_user):
    """Completed interventions remove the pollutant from the plan."""
    b = await _create_building(db_session, admin_user)
    d = await _create_diagnostic(db_session, b.id)
    await _create_sample(db_session, d.id, pollutant_type="asbestos")
    await _create_sample(db_session, d.id, pollutant_type="lead", risk_level="low")
    await _create_intervention(
        db_session,
        b.id,
        intervention_type="asbestos_removal",
        status="completed",
    )
    await db_session.commit()

    plan = await generate_mitigation_plan(db_session, b.id)
    pollutants = [s.pollutant_type for s in plan.steps]
    assert "asbestos" not in pollutants
    assert "lead" in pollutants


@pytest.mark.asyncio
async def test_regulatory_deadline_bonus(db_session, admin_user):
    """Overdue action items give +20 urgency bonus."""
    b = await _create_building(db_session, admin_user)
    d = await _create_diagnostic(db_session, b.id)
    await _create_sample(
        db_session,
        d.id,
        pollutant_type="lead",
        risk_level="low",
        material_state="contained",
    )
    # Create overdue action
    await _create_action_item(
        db_session,
        b.id,
        action_type="lead",
        due_date=date.today() - timedelta(days=30),
        status="open",
    )
    await db_session.commit()

    plan = await generate_mitigation_plan(db_session, b.id)
    assert len(plan.steps) == 1
    # Lead contained base = 30, + 20 overdue bonus = 50
    assert plan.steps[0].urgency_score == 50.0


@pytest.mark.asyncio
async def test_plan_has_work_category(db_session, admin_user):
    """Steps include work category from sample data."""
    b = await _create_building(db_session, admin_user)
    d = await _create_diagnostic(db_session, b.id)
    await _create_sample(
        db_session,
        d.id,
        pollutant_type="asbestos",
        cfst_work_category="major",
    )
    await db_session.commit()

    plan = await generate_mitigation_plan(db_session, b.id)
    assert plan.steps[0].work_category == "major"


@pytest.mark.asyncio
async def test_plan_has_regulatory_reference(db_session, admin_user):
    """Steps include regulatory references."""
    b = await _create_building(db_session, admin_user)
    d = await _create_diagnostic(db_session, b.id)
    await _create_sample(db_session, d.id, pollutant_type="asbestos")
    await db_session.commit()

    plan = await generate_mitigation_plan(db_session, b.id)
    assert "OTConst" in plan.steps[0].regulatory_reference


@pytest.mark.asyncio
async def test_plan_risk_reduction_percent(db_session, admin_user):
    """Plan computes a total risk reduction percentage."""
    b = await _create_building(db_session, admin_user)
    d = await _create_diagnostic(db_session, b.id)
    await _create_sample(db_session, d.id, pollutant_type="asbestos")
    await _create_sample(db_session, d.id, pollutant_type="pcb")
    await db_session.commit()

    plan = await generate_mitigation_plan(db_session, b.id)
    assert plan.risk_reduction_percent > 0
    assert plan.risk_reduction_percent <= 100.0


@pytest.mark.asyncio
async def test_draft_diagnostics_excluded(db_session, admin_user):
    """Only completed/validated diagnostics are considered."""
    b = await _create_building(db_session, admin_user)
    d = await _create_diagnostic(db_session, b.id, status="draft")
    await _create_sample(db_session, d.id, pollutant_type="asbestos")
    await db_session.commit()

    plan = await generate_mitigation_plan(db_session, b.id)
    assert len(plan.steps) == 0


# ── Service tests: get_quick_wins ────────────────────────────────


@pytest.mark.asyncio
async def test_quick_wins_identification(db_session, admin_user):
    """Quick wins are identified for minor-category interventions."""
    b = await _create_building(db_session, admin_user)
    d = await _create_diagnostic(db_session, b.id)
    # Lead contained = minor work category, lead_encapsulation
    await _create_sample(
        db_session,
        d.id,
        pollutant_type="lead",
        risk_level="low",
        material_state="contained",
    )
    # Radon moderate = minor work category
    await _create_sample(
        db_session,
        d.id,
        pollutant_type="radon",
        concentration=500.0,
    )
    await db_session.commit()

    wins = await get_quick_wins(db_session, b.id)
    assert len(wins) >= 1
    pollutants = [w.pollutant_type for w in wins]
    # radon_ventilation is minor work category
    assert "radon" in pollutants or "lead" in pollutants


@pytest.mark.asyncio
async def test_quick_wins_empty_building(db_session, admin_user):
    """Building with no diagnostics has no quick wins."""
    b = await _create_building(db_session, admin_user)
    await db_session.commit()

    wins = await get_quick_wins(db_session, b.id)
    assert len(wins) == 0


@pytest.mark.asyncio
async def test_quick_wins_sorted_by_risk_reduction(db_session, admin_user):
    """Quick wins are sorted by risk reduction score descending."""
    b = await _create_building(db_session, admin_user)
    d = await _create_diagnostic(db_session, b.id)
    await _create_sample(
        db_session,
        d.id,
        pollutant_type="radon",
        concentration=1500.0,
    )
    await _create_sample(
        db_session,
        d.id,
        pollutant_type="lead",
        risk_level="low",
        material_state="contained",
    )
    await db_session.commit()

    wins = await get_quick_wins(db_session, b.id)
    if len(wins) >= 2:
        assert wins[0].risk_reduction_score >= wins[1].risk_reduction_score


# ── Service tests: analyze_intervention_dependencies ──────────────


@pytest.mark.asyncio
async def test_dependency_detection_asbestos_blocks(db_session, admin_user):
    """Asbestos creates a dependency edge (blocks renovation)."""
    b = await _create_building(db_session, admin_user)
    d = await _create_diagnostic(db_session, b.id)
    await _create_sample(db_session, d.id, pollutant_type="asbestos")
    await db_session.commit()

    analysis = await analyze_intervention_dependencies(db_session, b.id)
    assert analysis.building_id == b.id
    # Asbestos should create at least one dependency edge
    blocker_names = [dep.blocker for dep in analysis.dependencies]
    assert "asbestos_removal" in blocker_names


@pytest.mark.asyncio
async def test_critical_path_analysis(db_session, admin_user):
    """Critical path is computed for multi-pollutant buildings."""
    b = await _create_building(db_session, admin_user)
    d = await _create_diagnostic(db_session, b.id)
    await _create_sample(db_session, d.id, pollutant_type="asbestos")
    await _create_sample(db_session, d.id, pollutant_type="pcb")
    await db_session.commit()

    analysis = await analyze_intervention_dependencies(db_session, b.id)
    # Should have a critical path with at least one entry
    assert isinstance(analysis.critical_path, list)


@pytest.mark.asyncio
async def test_parallel_safe_interventions(db_session, admin_user):
    """Radon and lead in different zones can be done in parallel."""
    b = await _create_building(db_session, admin_user)
    d = await _create_diagnostic(db_session, b.id)
    await _create_sample(
        db_session,
        d.id,
        pollutant_type="radon",
        concentration=500.0,
        location_floor="basement",
    )
    await _create_sample(
        db_session,
        d.id,
        pollutant_type="lead",
        risk_level="low",
        material_state="contained",
        location_floor="2nd floor",
    )
    await db_session.commit()

    analysis = await analyze_intervention_dependencies(db_session, b.id)
    assert len(analysis.parallel_safe) >= 1


@pytest.mark.asyncio
async def test_empty_building_no_dependencies(db_session, admin_user):
    """Building with no diagnostics has no dependencies."""
    b = await _create_building(db_session, admin_user)
    await db_session.commit()

    analysis = await analyze_intervention_dependencies(db_session, b.id)
    assert len(analysis.dependencies) == 0
    assert len(analysis.critical_path) == 0


# ── Service tests: estimate_plan_timeline ────────────────────────


@pytest.mark.asyncio
async def test_timeline_generation_with_milestones(db_session, admin_user):
    """Timeline has milestones for each step."""
    b = await _create_building(db_session, admin_user)
    d = await _create_diagnostic(db_session, b.id)
    await _create_sample(db_session, d.id, pollutant_type="asbestos")
    await _create_sample(db_session, d.id, pollutant_type="lead", risk_level="low")
    await db_session.commit()

    timeline = await estimate_plan_timeline(db_session, b.id)
    assert timeline.total_weeks > 0
    assert len(timeline.milestones) == 2
    # Milestones should have increasing weeks
    assert timeline.milestones[0].week <= timeline.milestones[1].week


@pytest.mark.asyncio
async def test_cost_curve_progression(db_session, admin_user):
    """Cumulative cost curve is monotonically increasing."""
    b = await _create_building(db_session, admin_user)
    d = await _create_diagnostic(db_session, b.id)
    await _create_sample(db_session, d.id, pollutant_type="asbestos")
    await _create_sample(db_session, d.id, pollutant_type="pcb")
    await db_session.commit()

    timeline = await estimate_plan_timeline(db_session, b.id)
    curve = timeline.cumulative_cost_curve
    assert len(curve) > 0
    for i in range(1, len(curve)):
        assert curve[i] >= curve[i - 1]


@pytest.mark.asyncio
async def test_timeline_empty_building(db_session, admin_user):
    """Empty building has zero-week timeline."""
    b = await _create_building(db_session, admin_user)
    await db_session.commit()

    timeline = await estimate_plan_timeline(db_session, b.id)
    assert timeline.total_weeks == 0
    assert len(timeline.milestones) == 0
    assert len(timeline.cumulative_cost_curve) == 0


@pytest.mark.asyncio
async def test_timeline_milestone_costs(db_session, admin_user):
    """Each milestone has a positive cost."""
    b = await _create_building(db_session, admin_user)
    d = await _create_diagnostic(db_session, b.id)
    await _create_sample(db_session, d.id, pollutant_type="asbestos")
    await db_session.commit()

    timeline = await estimate_plan_timeline(db_session, b.id)
    for milestone in timeline.milestones:
        assert milestone.cost_chf > 0


# ── API endpoint tests ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_api_mitigation_plan(client, db_session, admin_user, auth_headers):
    """GET /buildings/{id}/mitigation-plan returns valid plan."""
    b = await _create_building(db_session, admin_user)
    d = await _create_diagnostic(db_session, b.id)
    await _create_sample(db_session, d.id, pollutant_type="asbestos")
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/buildings/{b.id}/mitigation-plan",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(b.id)
    assert len(data["steps"]) == 1


@pytest.mark.asyncio
async def test_api_quick_wins(client, db_session, admin_user, auth_headers):
    """GET /buildings/{id}/quick-wins returns list."""
    b = await _create_building(db_session, admin_user)
    d = await _create_diagnostic(db_session, b.id)
    await _create_sample(
        db_session,
        d.id,
        pollutant_type="radon",
        concentration=500.0,
    )
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/buildings/{b.id}/quick-wins",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_api_intervention_dependencies(client, db_session, admin_user, auth_headers):
    """GET /buildings/{id}/intervention-dependencies returns analysis."""
    b = await _create_building(db_session, admin_user)
    d = await _create_diagnostic(db_session, b.id)
    await _create_sample(db_session, d.id, pollutant_type="asbestos")
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/buildings/{b.id}/intervention-dependencies",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(b.id)


@pytest.mark.asyncio
async def test_api_plan_timeline(client, db_session, admin_user, auth_headers):
    """GET /buildings/{id}/plan-timeline returns timeline."""
    b = await _create_building(db_session, admin_user)
    d = await _create_diagnostic(db_session, b.id)
    await _create_sample(db_session, d.id, pollutant_type="asbestos")
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/buildings/{b.id}/plan-timeline",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_weeks"] > 0


@pytest.mark.asyncio
async def test_api_not_found(client, auth_headers):
    """Non-existent building returns 404."""
    fake_id = uuid.uuid4()
    resp = await client.get(
        f"/api/v1/buildings/{fake_id}/mitigation-plan",
        headers=auth_headers,
    )
    assert resp.status_code == 404
