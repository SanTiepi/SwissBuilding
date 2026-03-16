"""Tests for the Dossier Completion Agent."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.models.building import Building
from app.schemas.completeness import CompletenessResult
from app.services.dossier_completion_agent import (
    READINESS_TYPES,
    _build_trust_warnings,
    _determine_overall_status,
    run_dossier_completion,
)

# ── Helpers ────────────────────────────────────────────────────────


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


def _make_trust_score(**kwargs):
    """Create a mock trust score object."""
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
    """Create a mock readiness assessment."""
    return SimpleNamespace(
        status=status,
        score=0.9 if status == "ready" else 0.4,
        blockers_json=blockers_json or [],
    )


def _make_completeness(overall_score=0.9):
    """Create a mock completeness result."""
    return CompletenessResult(
        building_id=uuid.uuid4(),
        workflow_stage="avt",
        overall_score=overall_score,
        checks=[],
        missing_items=[],
        ready_to_proceed=overall_score >= 0.8,
        evaluated_at=datetime.now(UTC),
    )


def _make_unknown(
    unknown_type="missing_diagnostic",
    severity="high",
    status="open",
    blocks_readiness=False,
    title="Missing diagnostic",
    entity_type=None,
    entity_id=None,
):
    """Create a mock unknown issue."""
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


# Patch targets
_PATCH_PREFIX = "app.services.dossier_completion_agent"


def _patch_all_services(
    unknowns=None,
    trust=None,
    completeness_score=0.9,
    readiness_statuses=None,
    readiness_blockers=None,
):
    """Return a dict of patch objects for all sub-services."""
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

    patches = {
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
    return patches


# ── Tests ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_complete_building(db_session, admin_user):
    """Complete building: all services return good data -> 'complete' status."""
    building = await _create_building(db_session, admin_user)
    await db_session.commit()

    patches = _patch_all_services(
        completeness_score=0.98,
        trust=_make_trust_score(
            overall_score=0.85,
            percent_declared=0.1,
            percent_obsolete=0.0,
            percent_contradictory=0.0,
        ),
    )

    with (
        patches["generate_unknowns"],
        patches["calculate_trust"],
        patches["evaluate_completeness"],
        patches["evaluate_readiness"],
        patches["generate_actions"],
    ):
        report = await run_dossier_completion(db_session, building.id)

    assert report is not None
    assert report.overall_status == "complete"
    assert report.completeness_score == 0.98
    assert report.trust_score == 0.85


@pytest.mark.asyncio
async def test_critical_gaps_when_readiness_blocked(db_session, admin_user):
    """Building with blocked readiness -> 'critical_gaps' status."""
    building = await _create_building(db_session, admin_user)
    await db_session.commit()

    patches = _patch_all_services(
        completeness_score=0.5,
        trust=_make_trust_score(overall_score=0.3),
        readiness_statuses={
            "safe_to_start": "blocked",
            "safe_to_tender": "blocked",
            "safe_to_reopen": "not_evaluated",
            "safe_to_requalify": "not_evaluated",
        },
        readiness_blockers={
            "safe_to_start": [{"description": "Missing asbestos diagnostic"}],
            "safe_to_tender": [{"description": "No cost estimate"}],
            "safe_to_reopen": [],
            "safe_to_requalify": [],
        },
    )

    with (
        patches["generate_unknowns"],
        patches["calculate_trust"],
        patches["evaluate_completeness"],
        patches["evaluate_readiness"],
        patches["generate_actions"],
    ):
        report = await run_dossier_completion(db_session, building.id)

    assert report is not None
    assert report.overall_status == "critical_gaps"
    assert len(report.top_blockers) >= 2


@pytest.mark.asyncio
async def test_incomplete_building(db_session, admin_user):
    """Building with moderate gaps -> 'incomplete' status."""
    building = await _create_building(db_session, admin_user)
    await db_session.commit()

    patches = _patch_all_services(
        completeness_score=0.6,
        trust=_make_trust_score(overall_score=0.4),
        readiness_statuses={rt: "not_evaluated" for rt in READINESS_TYPES},
    )

    with (
        patches["generate_unknowns"],
        patches["calculate_trust"],
        patches["evaluate_completeness"],
        patches["evaluate_readiness"],
        patches["generate_actions"],
    ):
        report = await run_dossier_completion(db_session, building.id)

    assert report is not None
    assert report.overall_status == "incomplete"


@pytest.mark.asyncio
async def test_near_complete_building(db_session, admin_user):
    """Building with high completeness, no blocked readiness -> 'near_complete'."""
    building = await _create_building(db_session, admin_user)
    await db_session.commit()

    patches = _patch_all_services(
        completeness_score=0.85,
        trust=_make_trust_score(overall_score=0.5),
        readiness_statuses={
            "safe_to_start": "ready",
            "safe_to_tender": "conditional",
            "safe_to_reopen": "not_evaluated",
            "safe_to_requalify": "not_evaluated",
        },
    )

    with (
        patches["generate_unknowns"],
        patches["calculate_trust"],
        patches["evaluate_completeness"],
        patches["evaluate_readiness"],
        patches["generate_actions"],
    ):
        report = await run_dossier_completion(db_session, building.id)

    assert report is not None
    assert report.overall_status == "near_complete"


@pytest.mark.asyncio
async def test_blockers_sorted_by_priority(db_session, admin_user):
    """Blockers are sorted: high priority first."""
    building = await _create_building(db_session, admin_user)
    await db_session.commit()

    unknowns = [
        _make_unknown(severity="low", blocks_readiness=True, title="Low prio"),
        _make_unknown(severity="high", blocks_readiness=True, title="High prio"),
        _make_unknown(severity="medium", blocks_readiness=True, title="Med prio"),
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
        report = await run_dossier_completion(db_session, building.id)

    priorities = [b.priority for b in report.top_blockers]
    assert priorities == sorted(priorities, key=lambda p: {"high": 0, "medium": 1, "low": 2}[p])


@pytest.mark.asyncio
async def test_recommendations_from_unknowns(db_session, admin_user):
    """Recommendations are generated from open unknowns."""
    building = await _create_building(db_session, admin_user)
    await db_session.commit()

    unknowns = [
        _make_unknown(unknown_type="missing_diagnostic", title="Need asbestos diag"),
        _make_unknown(unknown_type="uninspected_zone", title="Zone B not inspected"),
        _make_unknown(unknown_type="missing_document", title="Missing floor plan"),
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
        report = await run_dossier_completion(db_session, building.id)

    assert len(report.recommended_actions) == 3
    categories = {r.category for r in report.recommended_actions}
    assert "diagnostic" in categories
    assert "evidence" in categories
    assert "document" in categories


@pytest.mark.asyncio
async def test_trust_warnings_generated(db_session, admin_user):
    """Trust warnings are generated for high declared/obsolete/contradictory %."""
    building = await _create_building(db_session, admin_user)
    await db_session.commit()

    patches = _patch_all_services(
        completeness_score=0.5,
        trust=_make_trust_score(
            overall_score=0.3,
            percent_declared=0.4,
            percent_obsolete=0.15,
            percent_contradictory=0.1,
        ),
        readiness_statuses={rt: "not_evaluated" for rt in READINESS_TYPES},
    )

    with (
        patches["generate_unknowns"],
        patches["calculate_trust"],
        patches["evaluate_completeness"],
        patches["evaluate_readiness"],
        patches["generate_actions"],
    ):
        report = await run_dossier_completion(db_session, building.id)

    assert len(report.data_quality_warnings) == 3
    assert any("declared-only" in w for w in report.data_quality_warnings)
    assert any("obsolete" in w for w in report.data_quality_warnings)
    assert any("contradictions" in w for w in report.data_quality_warnings)


@pytest.mark.asyncio
async def test_gap_categories_aggregated(db_session, admin_user):
    """Gap categories are counted correctly from unknowns."""
    building = await _create_building(db_session, admin_user)
    await db_session.commit()

    unknowns = [
        _make_unknown(unknown_type="missing_diagnostic"),
        _make_unknown(unknown_type="missing_diagnostic"),
        _make_unknown(unknown_type="uninspected_zone"),
        _make_unknown(unknown_type="missing_document"),
        _make_unknown(unknown_type="missing_diagnostic", status="resolved"),  # not open
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
        report = await run_dossier_completion(db_session, building.id)

    assert report.gap_categories["missing_diagnostic"] == 2
    assert report.gap_categories["uninspected_zone"] == 1
    assert report.gap_categories["missing_document"] == 1


@pytest.mark.asyncio
async def test_returns_none_for_nonexistent_building(db_session, admin_user):
    """Returns None for non-existent building."""
    fake_id = uuid.uuid4()

    patches = _patch_all_services()
    with (
        patches["generate_unknowns"],
        patches["calculate_trust"],
        patches["evaluate_completeness"],
        patches["evaluate_readiness"],
        patches["generate_actions"],
    ):
        report = await run_dossier_completion(db_session, fake_id)

    assert report is None


@pytest.mark.asyncio
async def test_empty_building_returns_report(db_session, admin_user):
    """Empty building (no data) returns appropriate fallback."""
    building = await _create_building(db_session, admin_user)
    await db_session.commit()

    patches = _patch_all_services(
        completeness_score=0.0,
        trust=_make_trust_score(
            overall_score=0.0,
            percent_declared=0.0,
            percent_obsolete=0.0,
            percent_contradictory=0.0,
        ),
        readiness_statuses={rt: "not_evaluated" for rt in READINESS_TYPES},
    )

    with (
        patches["generate_unknowns"],
        patches["calculate_trust"],
        patches["evaluate_completeness"],
        patches["evaluate_readiness"],
        patches["generate_actions"],
    ):
        report = await run_dossier_completion(db_session, building.id)

    assert report is not None
    assert report.overall_status == "incomplete"
    assert report.completeness_score == 0.0
    assert report.trust_score == 0.0
    assert len(report.data_quality_warnings) == 0


@pytest.mark.asyncio
async def test_readiness_summary_contains_all_types(db_session, admin_user):
    """Readiness summary has entries for all 4 readiness types."""
    building = await _create_building(db_session, admin_user)
    await db_session.commit()

    patches = _patch_all_services(
        completeness_score=0.5,
        readiness_statuses={
            "safe_to_start": "ready",
            "safe_to_tender": "blocked",
            "safe_to_reopen": "conditional",
            "safe_to_requalify": "not_evaluated",
        },
    )

    with (
        patches["generate_unknowns"],
        patches["calculate_trust"],
        patches["evaluate_completeness"],
        patches["evaluate_readiness"],
        patches["generate_actions"],
    ):
        report = await run_dossier_completion(db_session, building.id)

    assert report.readiness_summary["safe_to_start"] == "ready"
    assert report.readiness_summary["safe_to_tender"] == "blocked"
    assert report.readiness_summary["safe_to_reopen"] == "conditional"
    assert report.readiness_summary["safe_to_requalify"] == "not_evaluated"


@pytest.mark.asyncio
async def test_mixed_readiness_statuses(db_session, admin_user):
    """Mixed readiness: some ready, some blocked -> critical_gaps."""
    building = await _create_building(db_session, admin_user)
    await db_session.commit()

    patches = _patch_all_services(
        completeness_score=0.9,
        trust=_make_trust_score(overall_score=0.8),
        readiness_statuses={
            "safe_to_start": "ready",
            "safe_to_tender": "ready",
            "safe_to_reopen": "blocked",
            "safe_to_requalify": "ready",
        },
        readiness_blockers={
            "safe_to_start": [],
            "safe_to_tender": [],
            "safe_to_reopen": [{"description": "Post-works inspection missing"}],
            "safe_to_requalify": [],
        },
    )

    with (
        patches["generate_unknowns"],
        patches["calculate_trust"],
        patches["evaluate_completeness"],
        patches["evaluate_readiness"],
        patches["generate_actions"],
    ):
        report = await run_dossier_completion(db_session, building.id)

    # Even with high completeness/trust, one blocked readiness -> critical_gaps
    assert report.overall_status == "critical_gaps"


@pytest.mark.asyncio
async def test_refresh_calls_all_generators(db_session, admin_user):
    """Force refresh triggers all generator sub-services."""
    building = await _create_building(db_session, admin_user)
    await db_session.commit()

    patches = _patch_all_services(
        completeness_score=0.5,
        readiness_statuses={rt: "not_evaluated" for rt in READINESS_TYPES},
    )

    with (
        patches["generate_unknowns"] as mock_unknowns,
        patches["calculate_trust"] as mock_trust,
        patches["evaluate_completeness"] as mock_completeness,
        patches["evaluate_readiness"] as mock_readiness,
        patches["generate_actions"],
    ):
        report = await run_dossier_completion(db_session, building.id, force_refresh=True)

    assert report is not None
    mock_unknowns.assert_awaited_once()
    mock_trust.assert_awaited_once()
    mock_completeness.assert_awaited_once()
    assert mock_readiness.call_count == 4  # one per readiness type


@pytest.mark.asyncio
async def test_top_blockers_limited_to_10(db_session, admin_user):
    """Top blockers list is limited to 10 items."""
    building = await _create_building(db_session, admin_user)
    await db_session.commit()

    unknowns = [_make_unknown(severity="high", blocks_readiness=True, title=f"Blocker {i}") for i in range(15)]

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
        report = await run_dossier_completion(db_session, building.id)

    assert len(report.top_blockers) == 10


@pytest.mark.asyncio
async def test_recommended_actions_limited_to_10(db_session, admin_user):
    """Recommended actions list is limited to 10 items."""
    building = await _create_building(db_session, admin_user)
    await db_session.commit()

    unknowns = [_make_unknown(unknown_type="missing_diagnostic", title=f"Gap {i}") for i in range(15)]

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
        report = await run_dossier_completion(db_session, building.id)

    assert len(report.recommended_actions) == 10


def test_determine_overall_status_complete():
    """Unit: complete status logic."""
    assert _determine_overall_status(0.98, 0.8, {rt: "ready" for rt in READINESS_TYPES}) == "complete"


def test_determine_overall_status_critical_gaps():
    """Unit: critical_gaps when any readiness is blocked."""
    statuses = {rt: "ready" for rt in READINESS_TYPES}
    statuses["safe_to_start"] = "blocked"
    assert _determine_overall_status(0.9, 0.8, statuses) == "critical_gaps"


def test_determine_overall_status_near_complete():
    """Unit: near_complete for high completeness, no blocked."""
    statuses = {rt: "conditional" for rt in READINESS_TYPES}
    assert _determine_overall_status(0.85, 0.5, statuses) == "near_complete"


def test_determine_overall_status_incomplete():
    """Unit: incomplete fallback."""
    statuses = {rt: "not_evaluated" for rt in READINESS_TYPES}
    assert _determine_overall_status(0.4, 0.3, statuses) == "incomplete"


def test_build_trust_warnings_all():
    """Unit: trust warnings for all threshold breaches."""
    trust = _make_trust_score(
        percent_declared=0.4,
        percent_obsolete=0.2,
        percent_contradictory=0.1,
    )
    warnings = _build_trust_warnings(trust)
    assert len(warnings) == 3


def test_build_trust_warnings_none():
    """Unit: no warnings when all values are below thresholds."""
    trust = _make_trust_score(
        percent_declared=0.1,
        percent_obsolete=0.05,
        percent_contradictory=0.01,
    )
    warnings = _build_trust_warnings(trust)
    assert len(warnings) == 0


@pytest.mark.asyncio
async def test_report_has_correct_schema_fields(db_session, admin_user):
    """Report has all expected fields from DossierCompletionReport schema."""
    building = await _create_building(db_session, admin_user)
    await db_session.commit()

    patches = _patch_all_services(
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
        report = await run_dossier_completion(db_session, building.id)

    assert report is not None
    assert report.building_id == building.id
    assert report.overall_status in ("complete", "near_complete", "incomplete", "critical_gaps")
    assert 0.0 <= report.completeness_score <= 1.0
    assert 0.0 <= report.trust_score <= 1.0
    assert isinstance(report.readiness_summary, dict)
    assert isinstance(report.top_blockers, list)
    assert isinstance(report.recommended_actions, list)
    assert isinstance(report.gap_categories, dict)
    assert isinstance(report.data_quality_warnings, list)
    assert report.assessed_at is not None
