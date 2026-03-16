"""Tests for readiness-driven action generator."""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    ACTION_PRIORITY_CRITICAL,
    ACTION_PRIORITY_MEDIUM,
    ACTION_SOURCE_READINESS,
    ACTION_STATUS_DONE,
    ACTION_STATUS_OPEN,
    ACTION_TYPE_DOCUMENTATION,
    ACTION_TYPE_INVESTIGATION,
    ACTION_TYPE_NOTIFICATION,
)
from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.readiness_assessment import ReadinessAssessment
from app.services.readiness_action_generator import generate_readiness_actions


@pytest.fixture
async def building(db_session: AsyncSession, admin_user):
    """Create a test building."""
    b = Building(
        id=uuid.uuid4(),
        address="Rue Readiness 10",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.commit()
    await db_session.refresh(b)
    return b


def _make_check(check_id: str, status: str, *, detail: str | None = None, legal_basis: str | None = None):
    return {
        "id": check_id,
        "label": check_id,
        "status": status,
        "detail": detail,
        "legal_basis": legal_basis,
        "required": True,
    }


@pytest.fixture
async def blocked_assessment(db_session: AsyncSession, building):
    """Create a blocked safe_to_start assessment with 3 failed checks."""
    assessment = ReadinessAssessment(
        id=uuid.uuid4(),
        building_id=building.id,
        readiness_type="safe_to_start",
        status="blocked",
        score=0.3,
        checks_json=[
            _make_check("completed_diagnostic", "fail", detail="No completed or validated diagnostic"),
            _make_check(
                "all_pollutants_evaluated",
                "fail",
                detail="Missing: hap, radon",
            ),
            _make_check(
                "suva_notification",
                "fail",
                detail="SUVA notification required but not filed",
                legal_basis="OTConst Art. 82-86",
            ),
            _make_check("waste_classified", "pass"),
        ],
        blockers_json=[
            {"message": "No completed diagnostic"},
            {"message": "Missing pollutant evaluation"},
            {"message": "SUVA notification required"},
        ],
        conditions_json=[],
    )
    db_session.add(assessment)
    await db_session.commit()
    await db_session.refresh(assessment)
    return assessment


@pytest.mark.asyncio
async def test_generates_actions_from_blocked_assessment(db_session, building, blocked_assessment):
    """Should create one action per failed check."""
    actions = await generate_readiness_actions(db_session, building.id)

    assert len(actions) == 3
    titles = {a.title for a in actions}
    assert "Complete pollutant diagnostic" in titles
    assert "Evaluate missing pollutants: Missing: hap, radon" in titles
    assert "File SUVA notification for asbestos" in titles


@pytest.mark.asyncio
async def test_idempotent_no_duplicates(db_session, building, blocked_assessment):
    """Running twice should not create duplicate actions."""
    first = await generate_readiness_actions(db_session, building.id)
    assert len(first) == 3

    await db_session.commit()

    second = await generate_readiness_actions(db_session, building.id)
    assert len(second) == 0

    # Verify total count is still 3
    result = await db_session.execute(
        select(ActionItem).where(
            ActionItem.building_id == building.id,
            ActionItem.source_type == ACTION_SOURCE_READINESS,
        )
    )
    all_actions = result.scalars().all()
    assert len(all_actions) == 3


@pytest.mark.asyncio
async def test_auto_resolves_when_check_passes(db_session, building, blocked_assessment):
    """When a check transitions from fail to pass, the action should be marked done."""
    actions = await generate_readiness_actions(db_session, building.id)
    assert len(actions) == 3
    await db_session.commit()

    # Update the assessment: completed_diagnostic now passes
    blocked_assessment.checks_json = [
        _make_check("completed_diagnostic", "pass", detail="1 completed diagnostic(s)"),
        _make_check("all_pollutants_evaluated", "fail", detail="Missing: hap, radon"),
        _make_check(
            "suva_notification",
            "fail",
            detail="SUVA notification required but not filed",
            legal_basis="OTConst Art. 82-86",
        ),
        _make_check("waste_classified", "pass"),
    ]
    await db_session.commit()

    # Run again — should auto-resolve the completed_diagnostic action
    new_actions = await generate_readiness_actions(db_session, building.id)
    assert len(new_actions) == 0
    await db_session.commit()

    # Check the completed_diagnostic action is now done
    result = await db_session.execute(
        select(ActionItem).where(
            ActionItem.building_id == building.id,
            ActionItem.source_type == ACTION_SOURCE_READINESS,
        )
    )
    all_actions = list(result.scalars().all())
    by_check = {}
    for a in all_actions:
        meta = a.metadata_json or {}
        by_check[meta.get("check_id")] = a.status

    assert by_check["completed_diagnostic"] == ACTION_STATUS_DONE
    assert by_check["all_pollutants_evaluated"] == ACTION_STATUS_OPEN
    assert by_check["suva_notification"] == ACTION_STATUS_OPEN


@pytest.mark.asyncio
async def test_no_assessments_returns_empty(db_session, building):
    """Building with no readiness assessments returns empty list."""
    actions = await generate_readiness_actions(db_session, building.id)
    assert actions == []


@pytest.mark.asyncio
async def test_filters_by_readiness_type(db_session, building):
    """When readiness_type is specified, only process that type."""
    # Create two assessments with different types
    a1 = ReadinessAssessment(
        id=uuid.uuid4(),
        building_id=building.id,
        readiness_type="safe_to_start",
        status="blocked",
        score=0.0,
        checks_json=[_make_check("completed_diagnostic", "fail", detail="No diagnostic")],
        blockers_json=[{"message": "No diagnostic"}],
        conditions_json=[],
    )
    a2 = ReadinessAssessment(
        id=uuid.uuid4(),
        building_id=building.id,
        readiness_type="safe_to_tender",
        status="blocked",
        score=0.0,
        checks_json=[_make_check("diagnostic_report", "fail", detail="No report")],
        blockers_json=[{"message": "No report"}],
        conditions_json=[],
    )
    db_session.add_all([a1, a2])
    await db_session.commit()

    # Only process safe_to_start
    actions = await generate_readiness_actions(db_session, building.id, readiness_type="safe_to_start")
    assert len(actions) == 1
    assert actions[0].title == "Complete pollutant diagnostic"


@pytest.mark.asyncio
async def test_handles_all_four_readiness_types(db_session, building):
    """Each readiness type can produce actions from its failed checks."""
    assessments = [
        ReadinessAssessment(
            id=uuid.uuid4(),
            building_id=building.id,
            readiness_type="safe_to_start",
            status="blocked",
            score=0.0,
            checks_json=[_make_check("completed_diagnostic", "fail")],
            blockers_json=[{"message": "blocker"}],
            conditions_json=[],
        ),
        ReadinessAssessment(
            id=uuid.uuid4(),
            building_id=building.id,
            readiness_type="safe_to_tender",
            status="blocked",
            score=0.0,
            checks_json=[_make_check("waste_elimination_plan", "fail")],
            blockers_json=[{"message": "blocker"}],
            conditions_json=[],
        ),
        ReadinessAssessment(
            id=uuid.uuid4(),
            building_id=building.id,
            readiness_type="safe_to_reopen",
            status="blocked",
            score=0.0,
            checks_json=[_make_check("air_clearance", "fail", legal_basis="CFST 6503")],
            blockers_json=[{"message": "blocker"}],
            conditions_json=[],
        ),
        ReadinessAssessment(
            id=uuid.uuid4(),
            building_id=building.id,
            readiness_type="safe_to_requalify",
            status="conditional",
            score=0.5,
            checks_json=[_make_check("diagnostic_age", "fail", detail="5.2 years old")],
            blockers_json=[],
            conditions_json=[{"message": "Requalification recommended"}],
        ),
    ]
    for a in assessments:
        db_session.add(a)
    await db_session.commit()

    actions = await generate_readiness_actions(db_session, building.id)
    assert len(actions) == 4

    titles = {a.title for a in actions}
    assert "Complete pollutant diagnostic" in titles
    assert "Prepare waste elimination plan" in titles
    assert "Perform air clearance measurements" in titles
    assert "Schedule requalification diagnostic" in titles


@pytest.mark.asyncio
async def test_action_has_correct_fields(db_session, building, blocked_assessment):
    """Verify source_type, priority, action_type from mapping."""
    actions = await generate_readiness_actions(db_session, building.id)

    # Find the completed_diagnostic action
    diag_action = [a for a in actions if "Complete pollutant diagnostic" in a.title]
    assert len(diag_action) == 1
    action = diag_action[0]

    assert action.source_type == ACTION_SOURCE_READINESS
    assert action.priority == ACTION_PRIORITY_CRITICAL
    assert action.action_type == ACTION_TYPE_INVESTIGATION
    assert action.status == ACTION_STATUS_OPEN
    assert action.building_id == building.id

    # Find the SUVA notification action
    suva_action = [a for a in actions if "SUVA" in a.title]
    assert len(suva_action) == 1
    assert suva_action[0].action_type == ACTION_TYPE_NOTIFICATION
    assert suva_action[0].priority == ACTION_PRIORITY_CRITICAL

    # Check description includes legal basis
    assert "OTConst Art. 82-86" in (suva_action[0].description or "")


@pytest.mark.asyncio
async def test_conditional_assessment_generates_actions(db_session, building):
    """Conditional assessments with 'conditional' check status also generate actions."""
    assessment = ReadinessAssessment(
        id=uuid.uuid4(),
        building_id=building.id,
        readiness_type="safe_to_start",
        status="conditional",
        score=0.8,
        checks_json=[
            _make_check("completed_diagnostic", "pass"),
            _make_check("diagnostic_report", "conditional", detail="No diagnostic report uploaded"),
        ],
        blockers_json=[],
        conditions_json=[{"message": "Diagnostic report not yet uploaded"}],
    )
    db_session.add(assessment)
    await db_session.commit()

    actions = await generate_readiness_actions(db_session, building.id)
    assert len(actions) == 1
    assert actions[0].title == "Upload diagnostic report"
    assert actions[0].priority == ACTION_PRIORITY_MEDIUM
    assert actions[0].action_type == ACTION_TYPE_DOCUMENTATION


@pytest.mark.asyncio
async def test_ready_assessment_no_actions(db_session, building):
    """Ready assessments should not generate new actions."""
    assessment = ReadinessAssessment(
        id=uuid.uuid4(),
        building_id=building.id,
        readiness_type="safe_to_start",
        status="ready",
        score=1.0,
        checks_json=[
            _make_check("completed_diagnostic", "pass"),
            _make_check("all_pollutants_evaluated", "pass"),
        ],
        blockers_json=[],
        conditions_json=[],
    )
    db_session.add(assessment)
    await db_session.commit()

    actions = await generate_readiness_actions(db_session, building.id)
    assert actions == []
