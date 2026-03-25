"""SwissRules Watch — API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.swiss_rules_watch import (
    BuildingCommuneContext,
    CommunalAdapterRead,
    CommunalOverrideRead,
    ReviewPayload,
    RuleChangeEventRead,
    RuleSourceRead,
)
from app.services.swiss_rules_watch_service import (
    get_building_commune_context,
    get_commune_overrides,
    get_unreviewed_changes,
    list_change_events,
    list_communal_adapters,
    list_sources,
    refresh_source_freshness,
    review_change_event,
)

router = APIRouter()


@router.get(
    "/swiss-rules/sources",
    response_model=list[RuleSourceRead],
)
async def list_sources_endpoint(
    tier: str | None = Query(None, description="Filter by watch_tier"),
    current_user: User = Depends(require_permission("jurisdictions", "list")),
    db: AsyncSession = Depends(get_db),
):
    return await list_sources(db, tier_filter=tier)


@router.post(
    "/swiss-rules/sources/{source_id}/check",
    response_model=RuleSourceRead,
)
async def check_source_endpoint(
    source_id: UUID,
    current_user: User = Depends(require_permission("jurisdictions", "update")),
    db: AsyncSession = Depends(get_db),
):
    source = await refresh_source_freshness(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Rule source not found")
    await db.commit()
    return source


@router.get(
    "/swiss-rules/changes",
    response_model=list[RuleChangeEventRead],
)
async def list_changes_endpoint(
    source_id: UUID | None = Query(None),
    current_user: User = Depends(require_permission("jurisdictions", "list")),
    db: AsyncSession = Depends(get_db),
):
    return await list_change_events(db, source_id=source_id)


@router.get(
    "/swiss-rules/changes/unreviewed",
    response_model=list[RuleChangeEventRead],
)
async def unreviewed_changes_endpoint(
    current_user: User = Depends(require_permission("jurisdictions", "list")),
    db: AsyncSession = Depends(get_db),
):
    return await get_unreviewed_changes(db)


@router.post(
    "/swiss-rules/changes/{event_id}/review",
    response_model=RuleChangeEventRead,
)
async def review_change_endpoint(
    event_id: UUID,
    payload: ReviewPayload,
    current_user: User = Depends(require_permission("jurisdictions", "update")),
    db: AsyncSession = Depends(get_db),
):
    event = await review_change_event(db, event_id, current_user.id, payload.notes)
    if not event:
        raise HTTPException(status_code=404, detail="Change event not found")
    await db.commit()
    return event


@router.get(
    "/swiss-rules/communes",
    response_model=list[CommunalAdapterRead],
)
async def list_communes_endpoint(
    canton: str | None = Query(None),
    current_user: User = Depends(require_permission("jurisdictions", "list")),
    db: AsyncSession = Depends(get_db),
):
    return await list_communal_adapters(db, canton_filter=canton)


@router.get(
    "/swiss-rules/communes/{commune_code}/overrides",
    response_model=list[CommunalOverrideRead],
)
async def commune_overrides_endpoint(
    commune_code: str,
    current_user: User = Depends(require_permission("jurisdictions", "list")),
    db: AsyncSession = Depends(get_db),
):
    return await get_commune_overrides(db, commune_code)


@router.get(
    "/buildings/{building_id}/commune-context",
    response_model=BuildingCommuneContext,
)
async def building_commune_context_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_building_commune_context(db, building_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="Building not found")
    return ctx
