"""BatiConnect — Flywheel metrics service (admin-only, never used for ranking)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_extraction_log import AIExtractionLog
from app.models.building import Building
from app.models.completion_confirmation import CompletionConfirmation
from app.models.review import Review
from app.schemas.growth_stack import FlywheelMetrics


async def get_module_metrics(db: AsyncSession) -> FlywheelMetrics:
    """Compute flywheel metrics for the remediation module. Admin-only."""
    # Total extractions
    total_ext = (await db.execute(select(func.count()).select_from(AIExtractionLog))).scalar() or 0

    # Breakdown by status
    confirmed = (
        await db.execute(select(func.count()).select_from(AIExtractionLog).where(AIExtractionLog.status == "confirmed"))
    ).scalar() or 0

    corrected = (
        await db.execute(select(func.count()).select_from(AIExtractionLog).where(AIExtractionLog.status == "corrected"))
    ).scalar() or 0

    rejected = (
        await db.execute(select(func.count()).select_from(AIExtractionLog).where(AIExtractionLog.status == "rejected"))
    ).scalar() or 0

    denom = max(total_ext, 1)
    confirmation_rate = round(confirmed / denom, 3)
    correction_rate = round(corrected / denom, 3)
    rejection_rate = round(rejected / denom, 3)

    # Completed cycles (fully_confirmed completions)
    total_completed = (
        await db.execute(
            select(func.count())
            .select_from(CompletionConfirmation)
            .where(CompletionConfirmation.status == "fully_confirmed")
        )
    ).scalar() or 0

    # Reviews published
    total_reviews = (
        await db.execute(select(func.count()).select_from(Review).where(Review.status == "published"))
    ).scalar() or 0

    # Knowledge density = completed / total buildings (buildings with at least 1 record)
    total_buildings = (await db.execute(select(func.count()).select_from(Building))).scalar() or 1

    knowledge_density = round(total_completed / max(total_buildings, 1), 3)

    return FlywheelMetrics(
        total_extractions=total_ext,
        confirmation_rate=confirmation_rate,
        correction_rate=correction_rate,
        rejection_rate=rejection_rate,
        avg_cycle_time_days=None,  # Requires date arithmetic — deferred
        total_completed_cycles=total_completed,
        total_reviews_published=total_reviews,
        knowledge_density=knowledge_density,
    )
