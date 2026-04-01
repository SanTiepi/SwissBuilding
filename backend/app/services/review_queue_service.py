"""BatiConnect -- Review Queue Service.

Manages human review/validation tasks across the system.
Every important truth change that needs human confirmation flows through here.
Idempotent: won't create duplicate tasks for the same target.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review_queue import ReviewTask

logger = logging.getLogger(__name__)

# Priority ordering for sorting
PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


async def create_review_task(
    db: AsyncSession,
    building_id: UUID,
    organization_id: UUID,
    task_type: str,
    target_type: str,
    target_id: UUID,
    title: str,
    priority: str = "medium",
    description: str | None = None,
    case_id: UUID | None = None,
    assigned_to_id: UUID | None = None,
) -> ReviewTask | None:
    """Create a new review task. Idempotent -- won't create duplicates for same target.

    Returns the task if created, None if a duplicate already exists (pending/in_progress).
    """
    # Check for existing active task on same target
    existing = await db.execute(
        select(ReviewTask).where(
            ReviewTask.target_type == target_type,
            ReviewTask.target_id == target_id,
            ReviewTask.task_type == task_type,
            ReviewTask.status.in_(["pending", "in_progress"]),
        )
    )
    if existing.scalar_one_or_none() is not None:
        logger.debug("review_queue: duplicate task skipped for %s/%s", target_type, target_id)
        return None

    task = ReviewTask(
        building_id=building_id,
        organization_id=organization_id,
        task_type=task_type,
        target_type=target_type,
        target_id=target_id,
        title=title,
        priority=priority,
        description=description,
        case_id=case_id,
        assigned_to_id=assigned_to_id,
    )
    db.add(task)
    await db.flush()

    logger.info(
        "review_queue: task created type=%s target=%s/%s priority=%s",
        task_type,
        target_type,
        target_id,
        priority,
    )
    return task


async def get_queue(
    db: AsyncSession,
    organization_id: UUID,
    status: str | None = "pending",
    priority: str | None = None,
    task_type: str | None = None,
    building_id: UUID | None = None,
    assigned_to_id: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ReviewTask]:
    """Get the review queue with filters. Sorted by priority then created_at."""
    conditions = [ReviewTask.organization_id == organization_id]

    if status is not None:
        conditions.append(ReviewTask.status == status)
    if priority is not None:
        conditions.append(ReviewTask.priority == priority)
    if task_type is not None:
        conditions.append(ReviewTask.task_type == task_type)
    if building_id is not None:
        conditions.append(ReviewTask.building_id == building_id)
    if assigned_to_id is not None:
        conditions.append(ReviewTask.assigned_to_id == assigned_to_id)

    # Sort: critical > high > medium > low, then oldest first
    # Use CASE for priority ordering
    from sqlalchemy import case

    priority_sort = case(
        {"critical": 0, "high": 1, "medium": 2, "low": 3},
        value=ReviewTask.priority,
        else_=4,
    )

    result = await db.execute(
        select(ReviewTask)
        .where(and_(*conditions))
        .order_by(priority_sort, ReviewTask.created_at.asc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def assign_task(
    db: AsyncSession,
    task_id: UUID,
    assigned_to_id: UUID,
) -> ReviewTask:
    """Assign a task to a reviewer."""
    result = await db.execute(select(ReviewTask).where(ReviewTask.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise ValueError("Review task not found")
    if task.status not in ("pending", "in_progress"):
        raise ValueError(f"Cannot assign task in status '{task.status}'")

    task.assigned_to_id = assigned_to_id
    task.status = "in_progress"
    await db.flush()
    return task


async def complete_task(
    db: AsyncSession,
    task_id: UUID,
    completed_by_id: UUID,
    resolution: str,
    resolution_note: str | None = None,
) -> ReviewTask:
    """Complete a review task."""
    result = await db.execute(select(ReviewTask).where(ReviewTask.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise ValueError("Review task not found")
    if task.status in ("completed", "skipped"):
        raise ValueError(f"Task already in terminal status '{task.status}'")

    task.status = "completed"
    task.completed_at = datetime.now(UTC)
    task.completed_by_id = completed_by_id
    task.resolution = resolution
    task.resolution_note = resolution_note
    await db.flush()

    logger.info("review_queue: task %s completed resolution=%s", task_id, resolution)
    return task


async def escalate_task(
    db: AsyncSession,
    task_id: UUID,
    escalation_reason: str,
) -> ReviewTask:
    """Escalate a task that can't be resolved at current level."""
    result = await db.execute(select(ReviewTask).where(ReviewTask.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise ValueError("Review task not found")
    if task.status in ("completed", "skipped"):
        raise ValueError(f"Cannot escalate task in status '{task.status}'")

    task.status = "escalated"
    task.escalation_reason = escalation_reason
    task.escalated_at = datetime.now(UTC)
    await db.flush()

    logger.info("review_queue: task %s escalated", task_id)
    return task


async def get_queue_stats(
    db: AsyncSession,
    organization_id: UUID,
) -> dict:
    """Get queue statistics: total pending, by priority, by type, overdue."""
    pending_filter = and_(
        ReviewTask.organization_id == organization_id,
        ReviewTask.status.in_(["pending", "in_progress"]),
    )

    # Total pending
    total_result = await db.execute(select(func.count(ReviewTask.id)).where(pending_filter))
    total_pending = total_result.scalar() or 0

    # By priority
    priority_result = await db.execute(
        select(ReviewTask.priority, func.count(ReviewTask.id)).where(pending_filter).group_by(ReviewTask.priority)
    )
    by_priority = dict(priority_result.all())

    # By type
    type_result = await db.execute(
        select(ReviewTask.task_type, func.count(ReviewTask.id)).where(pending_filter).group_by(ReviewTask.task_type)
    )
    by_type = dict(type_result.all())

    # Overdue (pending for > 7 days)
    seven_days_ago = datetime.now(UTC) - timedelta(days=7)
    overdue_result = await db.execute(
        select(func.count(ReviewTask.id)).where(
            pending_filter,
            ReviewTask.created_at < seven_days_ago,
        )
    )
    overdue_7d = overdue_result.scalar() or 0

    return {
        "total_pending": total_pending,
        "critical": by_priority.get("critical", 0),
        "high": by_priority.get("high", 0),
        "medium": by_priority.get("medium", 0),
        "low": by_priority.get("low", 0),
        "by_type": by_type,
        "overdue_7d": overdue_7d,
    }


async def auto_create_from_extraction(
    db: AsyncSession,
    extraction_id: UUID,
    building_id: UUID,
    organization_id: UUID,
    confidence: float,
    report_type: str = "unknown",
) -> ReviewTask | None:
    """Auto-create a review task when a new extraction is created."""
    # Higher priority for low-confidence extractions
    if confidence < 0.5:
        priority = "high"
    elif confidence < 0.7:
        priority = "medium"
    else:
        priority = "low"

    return await create_review_task(
        db,
        building_id=building_id,
        organization_id=organization_id,
        task_type="extraction_review",
        target_type="extraction",
        target_id=extraction_id,
        title=f"Revoir extraction diagnostic ({report_type})",
        priority=priority,
        description=f"Confiance: {confidence:.0%}. Verifier les donnees extraites avant application.",
    )


async def auto_create_from_contradiction(
    db: AsyncSession,
    building_id: UUID,
    organization_id: UUID,
    contradiction_id: UUID,
    contradiction_detail: str,
) -> ReviewTask | None:
    """Auto-create a review task when a contradiction is detected."""
    return await create_review_task(
        db,
        building_id=building_id,
        organization_id=organization_id,
        task_type="contradiction_resolution",
        target_type="contradiction",
        target_id=contradiction_id,
        title="Resoudre une contradiction detectee",
        priority="high",
        description=contradiction_detail,
    )


async def auto_create_from_claim(
    db: AsyncSession,
    building_id: UUID,
    organization_id: UUID,
    claim_id: UUID,
    claim_subject: str,
    confidence: float | None,
) -> ReviewTask | None:
    """Auto-create a review task when a claim with low confidence is created."""
    if confidence is not None and confidence >= 0.7:
        return None  # high-confidence claims don't need review

    priority = "high" if (confidence is not None and confidence < 0.4) else "medium"

    return await create_review_task(
        db,
        building_id=building_id,
        organization_id=organization_id,
        task_type="claim_verification",
        target_type="claim",
        target_id=claim_id,
        title=f"Verifier: {claim_subject[:200]}",
        priority=priority,
        description=f"Confiance: {confidence:.0%}. Assertion a valider par un expert."
        if confidence is not None
        else "Assertion sans indice de confiance. Validation requise.",
    )


async def auto_create_from_invalidation(
    db: AsyncSession,
    building_id: UUID,
    organization_id: UUID,
    invalidation_id: UUID,
    detail: str,
) -> ReviewTask | None:
    """Auto-create a review task when an invalidation event requires review."""
    return await create_review_task(
        db,
        building_id=building_id,
        organization_id=organization_id,
        task_type="invalidation_review",
        target_type="invalidation",
        target_id=invalidation_id,
        title="Invalidation detectee — revue requise",
        priority="high",
        description=detail[:500] if detail else "Artefact invalide — action requise.",
    )
