"""Tests for Programme I — AI Feedback Loop v1."""

import uuid

import pytest

from app.services.ai_feedback_service import (
    get_metrics,
    get_metrics_summary,
    list_feedback,
    record_feedback,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user_id():
    return uuid.uuid4()


def _entity_id():
    return uuid.uuid4()


# ---------------------------------------------------------------------------
# Tests — record_feedback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_correction_creates_feedback(db_session, admin_user):
    """A correction (original != corrected) creates a 'correct' feedback."""
    fb = await record_feedback(
        db_session,
        entity_type="material",
        entity_id=_entity_id(),
        field_name="material_type",
        original_value="asbestos",
        corrected_value="concrete",
        user_id=admin_user.id,
    )
    await db_session.commit()

    assert fb.feedback_type == "correct"
    assert fb.field_name == "material_type"
    assert fb.original_value == "asbestos"
    assert fb.corrected_value == "concrete"
    assert fb.confidence_delta == -0.15


@pytest.mark.asyncio
async def test_record_confirmation_creates_confirm_feedback(db_session, admin_user):
    """When original == corrected, feedback_type is 'confirm' with delta 0."""
    fb = await record_feedback(
        db_session,
        entity_type="diagnostic",
        entity_id=_entity_id(),
        field_name="hazard_level",
        original_value="high",
        corrected_value="high",
        user_id=admin_user.id,
    )
    await db_session.commit()

    assert fb.feedback_type == "confirm"
    assert fb.confidence_delta == 0.0


@pytest.mark.asyncio
async def test_record_feedback_stores_model_version(db_session, admin_user):
    """model_version is persisted."""
    fb = await record_feedback(
        db_session,
        entity_type="sample",
        entity_id=_entity_id(),
        field_name="pollutant_type",
        original_value="pcb",
        corrected_value="lead",
        user_id=admin_user.id,
        model_version="gpt-4o-2026-01",
    )
    await db_session.commit()

    assert fb.model_version == "gpt-4o-2026-01"


@pytest.mark.asyncio
async def test_record_feedback_stores_notes(db_session, admin_user):
    """Notes are optional and persisted."""
    fb = await record_feedback(
        db_session,
        entity_type="material",
        entity_id=_entity_id(),
        field_name="material_type",
        original_value="pvc",
        corrected_value="vinyl",
        user_id=admin_user.id,
        notes="PVC and vinyl are often confused",
    )
    await db_session.commit()

    assert fb.notes == "PVC and vinyl are often confused"


# ---------------------------------------------------------------------------
# Tests — metrics aggregation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_first_correction_creates_metrics(db_session, admin_user):
    """First feedback for a field creates AIMetrics with error_rate 1.0."""
    await record_feedback(
        db_session,
        entity_type="material",
        entity_id=_entity_id(),
        field_name="material_type",
        original_value="asbestos",
        corrected_value="concrete",
        user_id=admin_user.id,
    )
    await db_session.commit()

    metrics = await get_metrics(db_session, entity_type="material")
    assert len(metrics) == 1
    m = metrics[0]
    assert m.entity_type == "material"
    assert m.field_name == "material_type"
    assert m.total_extractions == 1
    assert m.total_corrections == 1
    assert m.error_rate == 1.0


@pytest.mark.asyncio
async def test_mixed_feedback_calculates_error_rate(db_session, admin_user):
    """2 corrections + 1 confirmation = error_rate 2/3."""
    eid = _entity_id()
    await record_feedback(
        db_session,
        entity_type="material",
        entity_id=eid,
        field_name="material_type",
        original_value="asbestos",
        corrected_value="concrete",
        user_id=admin_user.id,
    )
    await record_feedback(
        db_session,
        entity_type="material",
        entity_id=eid,
        field_name="material_type",
        original_value="lead",
        corrected_value="paint",
        user_id=admin_user.id,
    )
    await record_feedback(
        db_session,
        entity_type="material",
        entity_id=eid,
        field_name="material_type",
        original_value="pvc",
        corrected_value="pvc",
        user_id=admin_user.id,
    )
    await db_session.commit()

    metrics = await get_metrics(db_session, entity_type="material")
    m = metrics[0]
    assert m.total_extractions == 3
    assert m.total_corrections == 2
    assert abs(m.error_rate - 2 / 3) < 0.01


@pytest.mark.asyncio
async def test_common_errors_tracked(db_session, admin_user):
    """Repeated correction patterns are counted in common_errors."""
    eid = _entity_id()
    for _ in range(3):
        await record_feedback(
            db_session,
            entity_type="material",
            entity_id=eid,
            field_name="material_type",
            original_value="asbestos",
            corrected_value="concrete",
            user_id=admin_user.id,
        )
    await db_session.commit()

    metrics = await get_metrics(db_session, entity_type="material")
    errors = metrics[0].common_errors
    assert len(errors) == 1
    assert errors[0]["original"] == "asbestos"
    assert errors[0]["corrected"] == "concrete"
    assert errors[0]["count"] == 3


@pytest.mark.asyncio
async def test_multiple_error_patterns(db_session, admin_user):
    """Different correction patterns are tracked separately."""
    eid = _entity_id()
    await record_feedback(
        db_session,
        entity_type="material",
        entity_id=eid,
        field_name="material_type",
        original_value="asbestos",
        corrected_value="concrete",
        user_id=admin_user.id,
    )
    await record_feedback(
        db_session,
        entity_type="material",
        entity_id=eid,
        field_name="material_type",
        original_value="pcb",
        corrected_value="paint",
        user_id=admin_user.id,
    )
    await db_session.commit()

    metrics = await get_metrics(db_session, entity_type="material")
    errors = metrics[0].common_errors
    assert len(errors) == 2


# ---------------------------------------------------------------------------
# Tests — summary + listing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_metrics_summary(db_session, admin_user):
    """Summary computes overall_accuracy across all fields."""
    eid = _entity_id()
    # 1 correction + 1 confirmation = 50% accuracy
    await record_feedback(
        db_session,
        entity_type="diagnostic",
        entity_id=eid,
        field_name="hazard_level",
        original_value="high",
        corrected_value="low",
        user_id=admin_user.id,
    )
    await record_feedback(
        db_session,
        entity_type="diagnostic",
        entity_id=eid,
        field_name="hazard_level",
        original_value="medium",
        corrected_value="medium",
        user_id=admin_user.id,
    )
    await db_session.commit()

    summary = await get_metrics_summary(db_session, entity_type="diagnostic")
    assert summary["overall_accuracy"] == 0.5
    assert summary["total_extractions"] == 2
    assert summary["total_corrections"] == 1


@pytest.mark.asyncio
async def test_list_feedback_returns_recent(db_session, admin_user):
    """list_feedback returns records ordered by most recent."""
    eid = _entity_id()
    await record_feedback(
        db_session,
        entity_type="material",
        entity_id=eid,
        field_name="material_type",
        original_value="a",
        corrected_value="b",
        user_id=admin_user.id,
    )
    await record_feedback(
        db_session,
        entity_type="material",
        entity_id=eid,
        field_name="material_type",
        original_value="c",
        corrected_value="d",
        user_id=admin_user.id,
    )
    await db_session.commit()

    results = await list_feedback(db_session, entity_type="material")
    assert len(results) == 2


@pytest.mark.asyncio
async def test_list_feedback_filter_by_entity_id(db_session, admin_user):
    """list_feedback can filter by specific entity_id."""
    eid1 = _entity_id()
    eid2 = _entity_id()
    await record_feedback(
        db_session,
        entity_type="material",
        entity_id=eid1,
        field_name="material_type",
        original_value="a",
        corrected_value="b",
        user_id=admin_user.id,
    )
    await record_feedback(
        db_session,
        entity_type="material",
        entity_id=eid2,
        field_name="material_type",
        original_value="c",
        corrected_value="d",
        user_id=admin_user.id,
    )
    await db_session.commit()

    results = await list_feedback(db_session, entity_id=eid1)
    assert len(results) == 1
    assert results[0].entity_id == eid1


@pytest.mark.asyncio
async def test_empty_metrics_summary(db_session):
    """Empty database returns 100% accuracy."""
    summary = await get_metrics_summary(db_session)
    assert summary["overall_accuracy"] == 1.0
    assert summary["total_extractions"] == 0
    assert summary["total_corrections"] == 0
    assert summary["metrics"] == []
