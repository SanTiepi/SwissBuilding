"""Expert review governance service — create, list, withdraw, query overrides."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expert_review import ExpertReview
from app.schemas.expert_review import ExpertReviewCreate


async def create_review(
    db: AsyncSession,
    data: ExpertReviewCreate,
    reviewed_by: UUID,
    reviewer_role: str | None = None,
) -> ExpertReview:
    """Create an expert review record."""
    review = ExpertReview(
        target_type=data.target_type,
        target_id=data.target_id,
        building_id=data.building_id,
        decision=data.decision,
        confidence_level=data.confidence_level,
        justification=data.justification,
        override_value=data.override_value,
        original_value=data.original_value,
        reviewed_by=reviewed_by,
        reviewer_role=reviewer_role,
        organization_id=data.organization_id,
        status="active",
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return review


async def list_reviews(
    db: AsyncSession,
    *,
    building_id: UUID | None = None,
    target_type: str | None = None,
    target_id: UUID | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[ExpertReview], int]:
    """List expert reviews with optional filters. Returns (items, total)."""
    conditions = [ExpertReview.status != "withdrawn"]
    if building_id is not None:
        conditions.append(ExpertReview.building_id == building_id)
    if target_type is not None:
        conditions.append(ExpertReview.target_type == target_type)
    if target_id is not None:
        conditions.append(ExpertReview.target_id == target_id)

    where = and_(*conditions)

    count_q = select(func.count()).select_from(ExpertReview).where(where)
    total = (await db.execute(count_q)).scalar() or 0

    q = select(ExpertReview).where(where).order_by(ExpertReview.created_at.desc()).limit(limit).offset(offset)
    rows = (await db.execute(q)).scalars().all()
    return list(rows), total


async def get_review(db: AsyncSession, review_id: UUID) -> ExpertReview | None:
    """Get a single expert review by ID."""
    return await db.get(ExpertReview, review_id)


async def withdraw_review(
    db: AsyncSession,
    review_id: UUID,
    user_id: UUID,
) -> ExpertReview | None:
    """Withdraw an expert review. Only the original reviewer can withdraw."""
    review = await db.get(ExpertReview, review_id)
    if review is None:
        return None
    if review.reviewed_by != user_id:
        return None
    review.status = "withdrawn"
    review.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(review)
    return review


async def get_active_overrides(
    db: AsyncSession,
    building_id: UUID,
) -> list[ExpertReview]:
    """Get all active override reviews for a building."""
    q = (
        select(ExpertReview)
        .where(
            and_(
                ExpertReview.building_id == building_id,
                ExpertReview.decision == "override",
                ExpertReview.status == "active",
            )
        )
        .order_by(ExpertReview.created_at.desc())
    )
    rows = (await db.execute(q)).scalars().all()
    return list(rows)


async def has_expert_override(
    db: AsyncSession,
    target_type: str,
    target_id: UUID,
) -> bool:
    """Check whether an active override exists for a specific target."""
    q = (
        select(func.count())
        .select_from(ExpertReview)
        .where(
            and_(
                ExpertReview.target_type == target_type,
                ExpertReview.target_id == target_id,
                ExpertReview.decision == "override",
                ExpertReview.status == "active",
            )
        )
    )
    count = (await db.execute(q)).scalar() or 0
    return count > 0
