"""BatiConnect — Lot 4: Remediation Post-Works API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.post_works_link import (
    AIFeedbackCreate,
    AIFeedbackRead,
    DomainEventRead,
    PostWorksLinkRead,
)
from app.services.domain_event_projector import replay_events
from app.services.remediation_post_works_service import (
    draft_post_works,
    finalize_post_works,
    get_building_remediation_outcomes,
    get_post_works_link,
    list_domain_events,
    record_ai_feedback,
    review_draft,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Post-works lifecycle
# ---------------------------------------------------------------------------


@router.post(
    "/marketplace/completions/{completion_id}/draft-post-works",
    response_model=PostWorksLinkRead,
    status_code=201,
)
async def draft_post_works_endpoint(
    completion_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Draft post-works analysis for a fully-confirmed completion."""
    try:
        link = await draft_post_works(db, completion_id, current_user.id)
        await db.commit()
        await db.refresh(link)
        return link
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/marketplace/completions/{completion_id}/review-post-works",
    response_model=PostWorksLinkRead,
)
async def review_post_works_endpoint(
    completion_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Mark drafted post-works as reviewed (human-in-the-loop)."""
    link = await get_post_works_link(db, completion_id)
    if link is None:
        raise HTTPException(status_code=404, detail="PostWorksLink not found for this completion")
    try:
        link = await review_draft(db, link.id, current_user.id)
        await db.commit()
        await db.refresh(link)
        return link
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/marketplace/completions/{completion_id}/finalize-post-works",
    response_model=PostWorksLinkRead,
)
async def finalize_post_works_endpoint(
    completion_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Finalize post-works analysis (admin/reviewer action)."""
    link = await get_post_works_link(db, completion_id)
    if link is None:
        raise HTTPException(status_code=404, detail="PostWorksLink not found for this completion")
    try:
        link = await finalize_post_works(db, link.id, current_user.id)
        await db.commit()
        await db.refresh(link)
        return link
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/marketplace/completions/{completion_id}/post-works",
    response_model=PostWorksLinkRead,
)
async def get_post_works_endpoint(
    completion_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get post-works link for a completion."""
    link = await get_post_works_link(db, completion_id)
    if link is None:
        raise HTTPException(status_code=404, detail="PostWorksLink not found for this completion")
    return link


# ---------------------------------------------------------------------------
# Building-level remediation outcomes
# ---------------------------------------------------------------------------


@router.get(
    "/buildings/{building_id}/remediation-outcomes",
    response_model=list[PostWorksLinkRead],
)
async def get_remediation_outcomes_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get all remediation outcomes for a building."""
    outcomes = await get_building_remediation_outcomes(db, building_id)
    return outcomes


# ---------------------------------------------------------------------------
# AI Feedback
# ---------------------------------------------------------------------------


@router.post(
    "/ai-feedback",
    response_model=AIFeedbackRead,
    status_code=201,
)
async def create_ai_feedback_endpoint(
    payload: AIFeedbackCreate,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Record human feedback on AI-generated output. Storage/provenance only."""
    fb = await record_ai_feedback(db, payload.model_dump(), current_user.id)
    await db.commit()
    await db.refresh(fb)
    return fb


# ---------------------------------------------------------------------------
# Domain events
# ---------------------------------------------------------------------------


@router.get(
    "/domain-events",
    response_model=list[DomainEventRead],
)
async def list_domain_events_endpoint(
    aggregate_type: str | None = Query(None),
    aggregate_id: UUID | None = Query(None),
    limit: int = Query(50, le=200),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List domain events, optionally filtered by aggregate."""
    events = await list_domain_events(db, aggregate_type, aggregate_id, limit)
    return events


@router.post(
    "/admin/domain-events/replay",
    status_code=200,
)
async def replay_domain_events_endpoint(
    aggregate_type: str = Query(...),
    aggregate_id: UUID = Query(...),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Replay all domain events for an aggregate (admin action)."""
    count = await replay_events(db, aggregate_type, aggregate_id)
    await db.commit()
    return {"replayed_events": count, "aggregate_type": aggregate_type, "aggregate_id": str(aggregate_id)}
