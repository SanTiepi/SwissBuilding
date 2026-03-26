"""BatiConnect - Ecosystem Engagement API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.ecosystem_engagement import (
    ActorEngagementProfile as ActorEngagementProfileSchema,
)
from app.schemas.ecosystem_engagement import (
    EcosystemEngagementCreate,
    EcosystemEngagementList,
    EcosystemEngagementRead,
    EngagementContestCreate,
    EngagementDepth,
    EngagementSummary,
    EngagementTimeline,
)
from app.services import ecosystem_engagement_service as svc

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


# ---------------------------------------------------------------------------
# POST /buildings/{building_id}/engagements
# ---------------------------------------------------------------------------
@router.post(
    "/buildings/{building_id}/engagements",
    response_model=EcosystemEngagementRead,
    status_code=201,
)
async def create_engagement_endpoint(
    building_id: UUID,
    data: EcosystemEngagementCreate,
    request: Request,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    try:
        engagement = await svc.create_engagement(
            db,
            building_id,
            data,
            user_id=current_user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        await db.commit()
        await db.refresh(engagement)
        return engagement
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# GET /buildings/{building_id}/engagements
# ---------------------------------------------------------------------------
@router.get(
    "/buildings/{building_id}/engagements",
    response_model=EcosystemEngagementList,
)
async def list_engagements_endpoint(
    building_id: UUID,
    actor_type: str | None = Query(None),
    subject_type: str | None = Query(None),
    engagement_type: str | None = Query(None),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    items = await svc.list_engagements(
        db, building_id, actor_type=actor_type, subject_type=subject_type, engagement_type=engagement_type
    )
    return EcosystemEngagementList(
        items=[EcosystemEngagementRead.model_validate(e) for e in items],
        count=len(items),
    )


# ---------------------------------------------------------------------------
# GET /buildings/{building_id}/engagement-summary
# ---------------------------------------------------------------------------
@router.get(
    "/buildings/{building_id}/engagement-summary",
    response_model=EngagementSummary,
)
async def get_engagement_summary_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    return await svc.get_engagement_summary(db, building_id)


# ---------------------------------------------------------------------------
# GET /buildings/{building_id}/engagement-timeline
# ---------------------------------------------------------------------------
@router.get(
    "/buildings/{building_id}/engagement-timeline",
    response_model=EngagementTimeline,
)
async def get_engagement_timeline_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    return await svc.get_engagement_timeline(db, building_id)


# ---------------------------------------------------------------------------
# GET /organizations/{org_id}/actor-engagements
# ---------------------------------------------------------------------------
@router.get(
    "/organizations/{org_id}/actor-engagements",
    response_model=ActorEngagementProfileSchema,
)
async def get_actor_engagements_endpoint(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_actor_engagements(db, org_id=org_id)


# ---------------------------------------------------------------------------
# POST /engagements/{engagement_id}/contest
# ---------------------------------------------------------------------------
@router.post(
    "/engagements/{engagement_id}/contest",
    response_model=EcosystemEngagementRead,
    status_code=201,
)
async def contest_engagement_endpoint(
    engagement_id: UUID,
    data: EngagementContestCreate,
    request: Request,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    try:
        engagement = await svc.contest_engagement(
            db,
            engagement_id,
            comment=data.comment,
            user_id=current_user.id,
            ip_address=request.client.host if request.client else None,
        )
        await db.commit()
        await db.refresh(engagement)
        return engagement
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# GET /buildings/{building_id}/engagement-depth
# ---------------------------------------------------------------------------
@router.get(
    "/buildings/{building_id}/engagement-depth",
    response_model=EngagementDepth,
)
async def get_engagement_depth_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    return await svc.compute_engagement_depth(db, building_id)
