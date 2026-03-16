"""Tests for the Completion Workspace service and API."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.models.building import Building
from app.schemas.completeness import CompletenessResult
from app.schemas.completion_workspace import StepStatusUpdate
from app.schemas.dossier_completion import (
    CompletionBlocker,
    CompletionRecommendation,
    DossierCompletionReport,
)
from app.services.completion_workspace_service import (
    build_workspace_from_report,
    generate_workspace,
    get_next_steps,
    update_step_status,
)
from app.services.dossier_completion_agent import READINESS_TYPES

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_building(db, admin_user, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Test 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1970,
        "building_type": "residential",
        "created_by": admin_user.id,
        "owner_id": admin_user.id,
        "status": "active",
    }
    defaults.update(kwargs)
    b = Building(**defaults)
    db.add(b)
    await db.flush()
    return b


def _make_report(
    building_id=None,
    *,
    overall_status="incomplete",
    completeness_score=0.5,
    trust_score=0.4,
    top_blockers=None,
    recommended_actions=None,
    gap_categories=None,
    data_quality_warnings=None,
):
    """Build a DossierCompletionReport for testing."""
    return DossierCompletionReport(
        building_id=building_id or uuid.uuid4(),
        overall_status=overall_status,
        completeness_score=completeness_score,
        trust_score=trust_score,
        readiness_summary={rt: "not_evaluated" for rt in READINESS_TYPES},
        top_blockers=top_blockers or [],
        recommended_actions=recommended_actions or [],
        gap_categories=gap_categories or {},
        data_quality_warnings=data_quality_warnings or [],
        assessed_at=datetime.now(UTC),
    )


def _make_trust_score(**kwargs):
    defaults = {
        "overall_score": 0.5,
        "percent_proven": 0.4,
        "percent_inferred": 0.1,
        "percent_declared": 0.3,
        "percent_obsolete": 0.1,
        "percent_contradictory": 0.1,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_readiness(status="ready", blockers_json=None):
    return SimpleNamespace(
        status=status,
        score=0.9 if status == "ready" else 0.4,
        blockers_json=blockers_json or [],
    )


def _make_completeness(overall_score=0.9):
    return CompletenessResult(
        building_id=uuid.uuid4(),
        workflow_stage="avt",
        overall_score=overall_score,
        checks=[],
        missing_items=[],
        ready_to_proceed=overall_score >= 0.8,
        evaluated_at=datetime.now(UTC),
    )


_PATCH_PREFIX = "app.services.dossier_completion_agent"


def _patch_all_services(
    unknowns=None,
    trust=None,
    completeness_score=0.9,
    readiness_statuses=None,
    readiness_blockers=None,
):
    if unknowns is None:
        unknowns = []
    if trust is None:
        trust = _make_trust_score()
    if readiness_statuses is None:
        readiness_statuses = {rt: "ready" for rt in READINESS_TYPES}
    if readiness_blockers is None:
        readiness_blockers = {rt: [] for rt in READINESS_TYPES}

    async def _mock_readiness(_db, _bid, rtype, **_kwargs):
        return _make_readiness(
            status=readiness_statuses.get(rtype, "ready"),
            blockers_json=readiness_blockers.get(rtype, []),
        )

    return {
        "generate_unknowns": patch(
            f"{_PATCH_PREFIX}.unknown_generator.generate_unknowns",
            new_callable=AsyncMock,
            return_value=unknowns,
        ),
        "calculate_trust": patch(
            f"{_PATCH_PREFIX}.trust_score_calculator.calculate_trust_score",
            new_callable=AsyncMock,
            return_value=trust,
        ),
        "evaluate_completeness": patch(
            f"{_PATCH_PREFIX}.completeness_engine.evaluate_completeness",
            new_callable=AsyncMock,
            return_value=_make_completeness(completeness_score),
        ),
        "evaluate_readiness": patch(
            f"{_PATCH_PREFIX}.readiness_reasoner.evaluate_readiness",
            side_effect=_mock_readiness,
        ),
        "generate_actions": patch(
            f"{_PATCH_PREFIX}.action_generator.generate_actions_from_diagnostic",
            new_callable=AsyncMock,
            return_value=[],
        ),
    }


def _make_unknown(
    unknown_type="missing_diagnostic",
    severity="high",
    status="open",
    blocks_readiness=False,
    title="Missing diagnostic",
    entity_type=None,
    entity_id=None,
):
    return SimpleNamespace(
        id=uuid.uuid4(),
        unknown_type=unknown_type,
        severity=severity,
        status=status,
        blocks_readiness=blocks_readiness,
        title=title,
        entity_type=entity_type,
        entity_id=entity_id,
    )


# ---------------------------------------------------------------------------
# Service unit tests (pure, no DB)
# ---------------------------------------------------------------------------


def test_generate_workspace_from_report_with_gaps():
    """Workspace contains steps from blockers, recommendations, gaps, and warnings."""
    report = _make_report(
        top_blockers=[
            CompletionBlocker(
                priority="high",
                description="Missing asbestos diagnostic",
                source="readiness",
            ),
        ],
        recommended_actions=[
            CompletionRecommendation(
                priority="high",
                description="Commission asbestos diagnostic",
                category="diagnostic",
            ),
            CompletionRecommendation(
                priority="medium",
                description="Upload floor plan",
                category="document",
            ),
        ],
        gap_categories={"missing_diagnostic": 2, "uninspected_zone": 1},
        data_quality_warnings=["30% of data is declared-only"],
    )

    ws = build_workspace_from_report(report)

    assert ws.total_steps > 0
    assert ws.completed_steps == 0
    assert ws.progress_percent == 0.0
    assert len(ws.steps) == ws.total_steps
    assert ws.next_recommended_step is not None


def test_steps_ordered_by_priority():
    """Steps within the same category are ordered by priority."""
    report = _make_report(
        recommended_actions=[
            CompletionRecommendation(priority="low", description="Low action", category="evidence"),
            CompletionRecommendation(priority="high", description="High action", category="evidence"),
            CompletionRecommendation(priority="medium", description="Med action", category="evidence"),
        ],
    )

    ws = build_workspace_from_report(report)

    priorities = [s.priority for s in ws.steps if s.category == "evidence"]
    priority_values = [{"critical": 0, "high": 1, "medium": 2, "low": 3}[p] for p in priorities]
    assert priority_values == sorted(priority_values)


def test_dependencies_assigned():
    """Verification steps depend on evidence/diagnostic/documentation steps."""
    report = _make_report(
        recommended_actions=[
            CompletionRecommendation(priority="high", description="Collect evidence", category="evidence"),
        ],
        data_quality_warnings=["10% of data has contradictions"],
    )

    ws = build_workspace_from_report(report)

    verification_steps = [s for s in ws.steps if s.category == "verification"]
    evidence_steps = [s for s in ws.steps if s.category == "evidence"]

    assert len(verification_steps) > 0
    assert len(evidence_steps) > 0
    # Verification steps should depend on evidence steps
    for vs in verification_steps:
        assert len(vs.depends_on) > 0
        for es in evidence_steps:
            assert es.id in vs.depends_on


def test_update_step_status_changes_progress():
    """Updating a step to completed recalculates progress."""
    report = _make_report(
        recommended_actions=[
            CompletionRecommendation(priority="high", description="Action 1", category="evidence"),
            CompletionRecommendation(priority="medium", description="Action 2", category="evidence"),
        ],
    )

    ws = build_workspace_from_report(report)
    assert ws.completed_steps == 0

    step_id = ws.steps[0].id
    updated = update_step_status(ws, step_id, StepStatusUpdate(status="completed"))

    assert updated.completed_steps == 1
    assert updated.progress_percent > 0.0


def test_completing_step_unblocks_dependents():
    """Completing a prerequisite step unblocks dependent steps."""
    report = _make_report(
        recommended_actions=[
            CompletionRecommendation(priority="high", description="Collect evidence", category="evidence"),
        ],
        data_quality_warnings=["20% of data is obsolete"],
    )

    ws = build_workspace_from_report(report)

    # Find the verification step and manually block it
    verification_steps = [s for s in ws.steps if s.category == "verification"]
    evidence_steps = [s for s in ws.steps if s.category == "evidence"]
    assert len(verification_steps) > 0
    assert len(evidence_steps) > 0

    vs = verification_steps[0]
    vs.status = "blocked"
    vs.blocker_reason = "Waiting for evidence"

    # Complete the evidence step
    updated = update_step_status(ws, evidence_steps[0].id, StepStatusUpdate(status="completed"))

    # The verification step should be unblocked
    updated_vs = next(s for s in updated.steps if s.id == vs.id)
    assert updated_vs.status == "pending"
    assert updated_vs.blocker_reason is None


def test_get_next_steps_returns_actionable():
    """get_next_steps only returns pending, non-blocked steps."""
    report = _make_report(
        recommended_actions=[
            CompletionRecommendation(priority="high", description="Action A", category="evidence"),
            CompletionRecommendation(priority="medium", description="Action B", category="evidence"),
            CompletionRecommendation(priority="low", description="Action C", category="evidence"),
        ],
        data_quality_warnings=["Some warning"],
    )

    ws = build_workspace_from_report(report)

    # Verification steps are blocked by evidence steps (dependencies)
    next_steps = get_next_steps(ws, count=3)
    assert len(next_steps) <= 3
    for step in next_steps:
        assert step.status == "pending"
        assert step.category != "verification"  # blocked by deps


def test_skip_step():
    """Skipping a step updates status and recalculates."""
    report = _make_report(
        recommended_actions=[
            CompletionRecommendation(priority="high", description="Action 1", category="evidence"),
        ],
    )

    ws = build_workspace_from_report(report)
    step_id = ws.steps[0].id

    updated = update_step_status(ws, step_id, StepStatusUpdate(status="skipped"))

    target = next(s for s in updated.steps if s.id == step_id)
    assert target.status == "skipped"


def test_blocked_step_has_blocker_reason():
    """Blocking a step stores the blocker_reason."""
    report = _make_report(
        recommended_actions=[
            CompletionRecommendation(priority="high", description="Action 1", category="evidence"),
        ],
    )

    ws = build_workspace_from_report(report)
    step_id = ws.steps[0].id

    updated = update_step_status(
        ws,
        step_id,
        StepStatusUpdate(status="blocked", blocker_reason="Waiting for lab results"),
    )

    target = next(s for s in updated.steps if s.id == step_id)
    assert target.status == "blocked"
    assert target.blocker_reason == "Waiting for lab results"


def test_empty_report_returns_zero_steps():
    """A building with no gaps returns a workspace with 0 steps."""
    report = _make_report(
        overall_status="complete",
        completeness_score=0.98,
        trust_score=0.9,
    )

    ws = build_workspace_from_report(report)

    assert ws.total_steps == 0
    assert ws.completed_steps == 0
    assert ws.progress_percent == 100.0
    assert ws.next_recommended_step is None


def test_next_steps_respects_count():
    """get_next_steps returns at most `count` steps."""
    report = _make_report(
        recommended_actions=[
            CompletionRecommendation(priority="high", description=f"Action {i}", category="evidence") for i in range(10)
        ],
    )

    ws = build_workspace_from_report(report)

    assert len(get_next_steps(ws, count=2)) <= 2
    assert len(get_next_steps(ws, count=5)) <= 5


def test_step_numbers_are_sequential():
    """Step numbers are sequential starting from 1."""
    report = _make_report(
        recommended_actions=[
            CompletionRecommendation(priority="high", description="A", category="evidence"),
            CompletionRecommendation(priority="medium", description="B", category="diagnostic"),
            CompletionRecommendation(priority="low", description="C", category="document"),
        ],
    )

    ws = build_workspace_from_report(report)
    numbers = [s.step_number for s in ws.steps]
    assert numbers == list(range(1, len(ws.steps) + 1))


# ---------------------------------------------------------------------------
# Integration tests (with DB)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_workspace_returns_workspace(db_session, admin_user):
    """generate_workspace returns a workspace for a building with gaps."""
    building = await _create_building(db_session, admin_user)
    await db_session.commit()

    unknowns = [
        _make_unknown(unknown_type="missing_diagnostic", title="Need asbestos diag"),
        _make_unknown(unknown_type="uninspected_zone", title="Zone B not inspected"),
    ]

    patches = _patch_all_services(
        unknowns=unknowns,
        completeness_score=0.5,
        readiness_statuses={rt: "not_evaluated" for rt in READINESS_TYPES},
    )

    with (
        patches["generate_unknowns"],
        patches["calculate_trust"],
        patches["evaluate_completeness"],
        patches["evaluate_readiness"],
        patches["generate_actions"],
    ):
        ws = await generate_workspace(db_session, building.id)

    assert ws is not None
    assert ws.building_id == building.id
    assert ws.total_steps > 0


@pytest.mark.asyncio
async def test_generate_workspace_returns_none_for_nonexistent(db_session, admin_user):
    """generate_workspace returns None for nonexistent building."""
    patches = _patch_all_services()
    with (
        patches["generate_unknowns"],
        patches["calculate_trust"],
        patches["evaluate_completeness"],
        patches["evaluate_readiness"],
        patches["generate_actions"],
    ):
        ws = await generate_workspace(db_session, uuid.uuid4())

    assert ws is None


@pytest.mark.asyncio
async def test_update_step_raises_for_unknown_step():
    """update_step_status raises ValueError for unknown step id."""
    report = _make_report(
        recommended_actions=[
            CompletionRecommendation(priority="high", description="X", category="evidence"),
        ],
    )
    ws = build_workspace_from_report(report)

    with pytest.raises(ValueError, match="not found"):
        update_step_status(ws, uuid.uuid4(), StepStatusUpdate(status="completed"))


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_get_workspace(client, admin_user, auth_headers):
    """GET /buildings/{id}/completion-workspace returns 200."""
    # Create a building in the DB used by the test client
    from app.database import get_db
    from app.main import app

    building_id = uuid.uuid4()
    b = Building(
        id=building_id,
        address="Rue API 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1975,
        building_type="residential",
        created_by=admin_user.id,
        owner_id=admin_user.id,
        status="active",
    )

    # Insert building via the override session
    async for session in app.dependency_overrides[get_db]():
        session.add(b)
        await session.commit()

    unknowns = [_make_unknown(title="API test gap")]
    patches = _patch_all_services(
        unknowns=unknowns,
        completeness_score=0.5,
        readiness_statuses={rt: "not_evaluated" for rt in READINESS_TYPES},
    )

    with (
        patches["generate_unknowns"],
        patches["calculate_trust"],
        patches["evaluate_completeness"],
        patches["evaluate_readiness"],
        patches["generate_actions"],
    ):
        response = await client.get(
            f"/api/v1/buildings/{building_id}/completion-workspace",
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["building_id"] == str(building_id)
    assert "steps" in data
    assert "total_steps" in data


@pytest.mark.asyncio
async def test_api_get_workspace_404(client, auth_headers):
    """GET /buildings/{id}/completion-workspace returns 404 for nonexistent."""
    fake_id = uuid.uuid4()

    patches = _patch_all_services()
    with (
        patches["generate_unknowns"],
        patches["calculate_trust"],
        patches["evaluate_completeness"],
        patches["evaluate_readiness"],
        patches["generate_actions"],
    ):
        response = await client.get(
            f"/api/v1/buildings/{fake_id}/completion-workspace",
            headers=auth_headers,
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_api_next_steps(client, admin_user, auth_headers):
    """GET /buildings/{id}/completion-workspace/next-steps returns correct count."""
    from app.database import get_db
    from app.main import app

    building_id = uuid.uuid4()
    b = Building(
        id=building_id,
        address="Rue Next 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1980,
        building_type="residential",
        created_by=admin_user.id,
        owner_id=admin_user.id,
        status="active",
    )

    async for session in app.dependency_overrides[get_db]():
        session.add(b)
        await session.commit()

    unknowns = [
        _make_unknown(title="Gap 1"),
        _make_unknown(title="Gap 2"),
        _make_unknown(title="Gap 3"),
        _make_unknown(title="Gap 4"),
    ]
    patches = _patch_all_services(
        unknowns=unknowns,
        completeness_score=0.5,
        readiness_statuses={rt: "not_evaluated" for rt in READINESS_TYPES},
    )

    with (
        patches["generate_unknowns"],
        patches["calculate_trust"],
        patches["evaluate_completeness"],
        patches["evaluate_readiness"],
        patches["generate_actions"],
    ):
        response = await client.get(
            f"/api/v1/buildings/{building_id}/completion-workspace/next-steps?count=2",
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 2
