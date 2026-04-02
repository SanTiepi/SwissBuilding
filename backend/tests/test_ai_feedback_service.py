"""Test suite for AI Feedback Service — correction recording, metrics aggregation, accuracy tracking."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_feedback_service import (
    get_metrics,
    get_metrics_summary,
    list_feedback,
    record_feedback,
)


@pytest.mark.asyncio
async def test_record_feedback_correction_creates_feedback_record(db: AsyncSession):
    """Test that recording a correction creates an AIFeedback record with correct_type."""
    user_id = uuid4()
    entity_id = uuid4()

    feedback = await record_feedback(
        db,
        entity_type="diagnostic",
        entity_id=entity_id,
        field_name="hazard_level",
        original_value="low",
        corrected_value="high",
        user_id=user_id,
        model_version="claude-3-sonnet",
        notes="User identified higher contamination risk",
    )

    assert feedback.id is not None
    assert feedback.entity_type == "diagnostic"
    assert feedback.entity_id == entity_id
    assert feedback.field_name == "hazard_level"
    assert feedback.original_value == "low"
    assert feedback.corrected_value == "high"
    assert feedback.feedback_type == "correct"
    assert feedback.user_id == user_id
    assert feedback.model_version == "claude-3-sonnet"
    assert feedback.notes == "User identified higher contamination risk"


@pytest.mark.asyncio
async def test_record_feedback_confirmation_creates_confirm_type(db: AsyncSession):
    """Test that identical original/corrected values create a 'confirm' feedback type."""
    user_id = uuid4()
    entity_id = uuid4()

    feedback = await record_feedback(
        db,
        entity_type="material",
        entity_id=entity_id,
        field_name="material_type",
        original_value="asbestos",
        corrected_value="asbestos",
        user_id=user_id,
    )

    assert feedback.feedback_type == "confirm"
    assert feedback.original_value == "asbestos"
    assert feedback.corrected_value == "asbestos"


@pytest.mark.asyncio
async def test_record_feedback_sets_confidence_delta(db: AsyncSession):
    """Test that corrections set confidence_delta to -0.15."""
    user_id = uuid4()
    entity_id = uuid4()

    feedback = await record_feedback(
        db,
        entity_type="diagnostic",
        entity_id=entity_id,
        field_name="status",
        original_value="compliant",
        corrected_value="non-compliant",
        user_id=user_id,
    )

    assert feedback.confidence_delta == -0.15


@pytest.mark.asyncio
async def test_record_feedback_creates_and_updates_metrics(db: AsyncSession):
    """Test that feedback recording updates AIMetrics aggregates."""
    user_id = uuid4()
    entity_id = uuid4()

    # First correction
    await record_feedback(
        db,
        entity_type="diagnostic",
        entity_id=entity_id,
        field_name="hazard_level",
        original_value="low",
        corrected_value="high",
        user_id=user_id,
    )

    metrics = await get_metrics(db, entity_type="diagnostic")
    assert len(metrics) == 1
    assert metrics[0].entity_type == "diagnostic"
    assert metrics[0].field_name == "hazard_level"
    assert metrics[0].total_extractions == 1
    assert metrics[0].total_corrections == 1
    assert metrics[0].error_rate == 1.0


@pytest.mark.asyncio
async def test_record_feedback_tracks_common_errors(db: AsyncSession):
    """Test that metrics track and rank common errors by frequency."""
    user_id = uuid4()

    # Record same error 3 times
    for _ in range(3):
        await record_feedback(
            db,
            entity_type="material",
            entity_id=uuid4(),
            field_name="hazard_type",
            original_value="low",
            corrected_value="high",
            user_id=user_id,
        )

    # Record different error once
    await record_feedback(
        db,
        entity_type="material",
        entity_id=uuid4(),
        field_name="hazard_type",
        original_value="medium",
        corrected_value="critical",
        user_id=user_id,
    )

    metrics = await get_metrics(db, entity_type="material")
    assert len(metrics) == 1
    assert metrics[0].total_corrections == 4
    common_errors = metrics[0].common_errors
    assert len(common_errors) == 2
    # First should be most frequent
    assert common_errors[0]["count"] == 3
    assert common_errors[0]["original"] == "low"


@pytest.mark.asyncio
async def test_get_metrics_summary_calculates_overall_accuracy(db: AsyncSession):
    """Test that metrics summary correctly calculates overall accuracy."""
    user_id = uuid4()

    # 10 total extractions, 2 corrections → 80% accuracy
    for i in range(10):
        await record_feedback(
            db,
            entity_type="diagnostic",
            entity_id=uuid4(),
            field_name=f"field_{i}",
            original_value="incorrect" if i < 2 else "correct",
            corrected_value="correct",
            user_id=user_id,
        )

    summary = await get_metrics_summary(db)
    assert summary["total_extractions"] == 10
    assert summary["total_corrections"] == 2
    assert summary["overall_accuracy"] == 0.8


@pytest.mark.asyncio
async def test_list_feedback_filters_by_entity_type(db: AsyncSession):
    """Test that list_feedback correctly filters by entity_type."""
    user_id = uuid4()

    # Record diagnostics
    for _ in range(3):
        await record_feedback(
            db,
            entity_type="diagnostic",
            entity_id=uuid4(),
            field_name="status",
            original_value="a",
            corrected_value="b",
            user_id=user_id,
        )

    # Record materials
    for _ in range(2):
        await record_feedback(
            db,
            entity_type="material",
            entity_id=uuid4(),
            field_name="type",
            original_value="x",
            corrected_value="y",
            user_id=user_id,
        )

    diagnostic_feedback = await list_feedback(db, entity_type="diagnostic")
    assert len(diagnostic_feedback) == 3
    for fb in diagnostic_feedback:
        assert fb.entity_type == "diagnostic"

    material_feedback = await list_feedback(db, entity_type="material")
    assert len(material_feedback) == 2
    for fb in material_feedback:
        assert fb.entity_type == "material"


@pytest.mark.asyncio
async def test_list_feedback_respects_limit(db: AsyncSession):
    """Test that list_feedback respects the limit parameter."""
    user_id = uuid4()

    # Create 15 feedback records
    for _ in range(15):
        await record_feedback(
            db,
            entity_type="diagnostic",
            entity_id=uuid4(),
            field_name="status",
            original_value="a",
            corrected_value="b",
            user_id=user_id,
        )

    limited = await list_feedback(db, limit=5)
    assert len(limited) == 5

    unlimited = await list_feedback(db, limit=100)
    assert len(unlimited) == 15
