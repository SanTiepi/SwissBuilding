"""Tests for the review queue service and API."""

import uuid

import pytest
from httpx import AsyncClient

from app.services import review_queue_service

# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_review_task(db_session):
    """Basic task creation."""
    building_id = uuid.uuid4()
    org_id = uuid.uuid4()
    target_id = uuid.uuid4()

    task = await review_queue_service.create_review_task(
        db_session,
        building_id=building_id,
        organization_id=org_id,
        task_type="extraction_review",
        target_type="extraction",
        target_id=target_id,
        title="Revoir extraction test",
        priority="high",
    )

    assert task is not None
    assert task.task_type == "extraction_review"
    assert task.priority == "high"
    assert task.status == "pending"


@pytest.mark.asyncio
async def test_create_review_task_idempotent(db_session):
    """Duplicate task for same target is skipped."""
    building_id = uuid.uuid4()
    org_id = uuid.uuid4()
    target_id = uuid.uuid4()

    task1 = await review_queue_service.create_review_task(
        db_session,
        building_id=building_id,
        organization_id=org_id,
        task_type="extraction_review",
        target_type="extraction",
        target_id=target_id,
        title="Revoir extraction test",
    )
    task2 = await review_queue_service.create_review_task(
        db_session,
        building_id=building_id,
        organization_id=org_id,
        task_type="extraction_review",
        target_type="extraction",
        target_id=target_id,
        title="Duplicate",
    )

    assert task1 is not None
    assert task2 is None  # duplicate skipped


@pytest.mark.asyncio
async def test_get_queue(db_session):
    """Queue retrieval with filtering."""
    org_id = uuid.uuid4()

    # Create tasks with different priorities
    for priority in ["critical", "low", "high"]:
        await review_queue_service.create_review_task(
            db_session,
            building_id=uuid.uuid4(),
            organization_id=org_id,
            task_type="extraction_review",
            target_type="extraction",
            target_id=uuid.uuid4(),
            title=f"Task {priority}",
            priority=priority,
        )

    tasks = await review_queue_service.get_queue(db_session, org_id)
    assert len(tasks) == 3
    # Should be ordered: critical, high, low
    assert tasks[0].priority == "critical"
    assert tasks[1].priority == "high"
    assert tasks[2].priority == "low"


@pytest.mark.asyncio
async def test_assign_task(db_session):
    """Assigning a task sets status to in_progress."""
    task = await review_queue_service.create_review_task(
        db_session,
        building_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        task_type="claim_verification",
        target_type="claim",
        target_id=uuid.uuid4(),
        title="Test assign",
    )

    user_id = uuid.uuid4()
    updated = await review_queue_service.assign_task(db_session, task.id, user_id)
    assert updated.status == "in_progress"
    assert updated.assigned_to_id == user_id


@pytest.mark.asyncio
async def test_complete_task(db_session):
    """Completing a task sets resolution and completed_at."""
    task = await review_queue_service.create_review_task(
        db_session,
        building_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        task_type="claim_verification",
        target_type="claim",
        target_id=uuid.uuid4(),
        title="Test complete",
    )

    user_id = uuid.uuid4()
    updated = await review_queue_service.complete_task(db_session, task.id, user_id, "approved", "Looks good")
    assert updated.status == "completed"
    assert updated.resolution == "approved"
    assert updated.resolution_note == "Looks good"
    assert updated.completed_at is not None


@pytest.mark.asyncio
async def test_escalate_task(db_session):
    """Escalating a task sets status and reason."""
    task = await review_queue_service.create_review_task(
        db_session,
        building_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        task_type="contradiction_resolution",
        target_type="contradiction",
        target_id=uuid.uuid4(),
        title="Test escalate",
    )

    updated = await review_queue_service.escalate_task(db_session, task.id, "Need expert opinion")
    assert updated.status == "escalated"
    assert updated.escalation_reason == "Need expert opinion"
    assert updated.escalated_at is not None


@pytest.mark.asyncio
async def test_get_queue_stats(db_session):
    """Queue stats computation."""
    org_id = uuid.uuid4()

    await review_queue_service.create_review_task(
        db_session,
        building_id=uuid.uuid4(),
        organization_id=org_id,
        task_type="extraction_review",
        target_type="extraction",
        target_id=uuid.uuid4(),
        title="Critical task",
        priority="critical",
    )
    await review_queue_service.create_review_task(
        db_session,
        building_id=uuid.uuid4(),
        organization_id=org_id,
        task_type="claim_verification",
        target_type="claim",
        target_id=uuid.uuid4(),
        title="Medium task",
        priority="medium",
    )

    stats = await review_queue_service.get_queue_stats(db_session, org_id)
    assert stats["total_pending"] == 2
    assert stats["critical"] == 1
    assert stats["medium"] == 1
    assert stats["by_type"]["extraction_review"] == 1
    assert stats["by_type"]["claim_verification"] == 1


@pytest.mark.asyncio
async def test_auto_create_from_extraction(db_session):
    """Auto-create review task for extraction with appropriate priority."""
    building_id = uuid.uuid4()
    org_id = uuid.uuid4()
    extraction_id = uuid.uuid4()

    # Low confidence -> high priority
    task = await review_queue_service.auto_create_from_extraction(
        db_session, extraction_id, building_id, org_id, confidence=0.3, report_type="asbestos"
    )
    assert task is not None
    assert task.priority == "high"
    assert task.task_type == "extraction_review"

    # High confidence -> low priority
    task2 = await review_queue_service.auto_create_from_extraction(
        db_session, uuid.uuid4(), building_id, org_id, confidence=0.9, report_type="pcb"
    )
    assert task2 is not None
    assert task2.priority == "low"


@pytest.mark.asyncio
async def test_auto_create_from_claim_high_confidence_skipped(db_session):
    """High confidence claims don't get review tasks."""
    task = await review_queue_service.auto_create_from_claim(
        db_session,
        building_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        claim_id=uuid.uuid4(),
        claim_subject="High confidence claim",
        confidence=0.9,
    )
    assert task is None  # skipped


@pytest.mark.asyncio
async def test_auto_create_from_claim_low_confidence(db_session):
    """Low confidence claims get review tasks."""
    task = await review_queue_service.auto_create_from_claim(
        db_session,
        building_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        claim_id=uuid.uuid4(),
        claim_subject="Low confidence claim",
        confidence=0.3,
    )
    assert task is not None
    assert task.priority == "high"
    assert task.task_type == "claim_verification"


@pytest.mark.asyncio
async def test_complete_already_completed_fails(db_session):
    """Cannot complete a task that is already completed."""
    task = await review_queue_service.create_review_task(
        db_session,
        building_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        task_type="extraction_review",
        target_type="extraction",
        target_id=uuid.uuid4(),
        title="Test",
    )

    await review_queue_service.complete_task(db_session, task.id, uuid.uuid4(), "approved")

    with pytest.raises(ValueError, match="terminal status"):
        await review_queue_service.complete_task(db_session, task.id, uuid.uuid4(), "rejected")


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_review_queue_api(client: AsyncClient, auth_headers: dict):
    """GET /review-queue returns list."""
    response = await client.get(
        "/api/v1/review-queue",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_review_queue_stats_api(client: AsyncClient, auth_headers: dict):
    """GET /review-queue/stats returns stats object."""
    response = await client.get(
        "/api/v1/review-queue/stats",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_pending" in data
    assert "critical" in data
    assert "by_type" in data
