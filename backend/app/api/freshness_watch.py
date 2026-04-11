"""BatiConnect -- Freshness Watch API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.freshness_watch import (
    FreshnessWatchCreate,
    FreshnessWatchDashboard,
    FreshnessWatchDismiss,
    FreshnessWatchImpact,
    FreshnessWatchRead,
)
from app.services.freshness_watch_service import (
    apply_reactions,
    assess_impact,
    dismiss_watch,
    get_pending_watches,
    get_watch_dashboard,
    record_change,
)

router = APIRouter()


@router.post(
    "/freshness-watch",
    response_model=FreshnessWatchRead,
    status_code=201,
)
async def create_watch_entry(
    payload: FreshnessWatchCreate,
    current_user: User = Depends(require_permission("jurisdictions", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Record an external change that may affect system truth."""
    entry = await record_change(
        db,
        delta_type=payload.delta_type,
        title=payload.title,
        description=payload.description,
        canton=payload.canton,
        jurisdiction_id=payload.jurisdiction_id,
        affected_work_families=payload.affected_work_families,
        affected_procedure_types=payload.affected_procedure_types,
        severity=payload.severity,
        reactions=[r.model_dump() for r in payload.reactions] if payload.reactions else None,
        source_registry_id=payload.source_registry_id,
        source_url=payload.source_url,
        effective_date=payload.effective_date,
    )
    await db.commit()
    return entry


@router.get(
    "/freshness-watch",
    response_model=list[FreshnessWatchRead],
)
async def list_watch_entries(
    status: str | None = Query("detected", description="Filter par statut"),
    severity: str | None = Query(None, description="Filter par severite"),
    canton: str | None = Query(None, description="Filter par canton"),
    delta_type: str | None = Query(None, description="Filter par type de changement"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_permission("jurisdictions", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List freshness watch entries with filters."""
    entries, _total = await get_pending_watches(
        db,
        status=status or "",
        severity=severity,
        canton=canton,
        delta_type=delta_type,
        limit=limit,
        offset=offset,
    )
    return entries


@router.get(
    "/freshness-watch/dashboard",
    response_model=FreshnessWatchDashboard,
)
async def watch_dashboard(
    current_user: User = Depends(require_permission("jurisdictions", "list")),
    db: AsyncSession = Depends(get_db),
):
    """Overview dashboard: total changes, by severity, by delta_type, by canton."""
    return await get_watch_dashboard(db)


@router.post(
    "/freshness-watch/{entry_id}/assess",
    response_model=FreshnessWatchImpact,
)
async def assess_watch_impact(
    entry_id: UUID,
    current_user: User = Depends(require_permission("jurisdictions", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Assess the impact of a freshness watch entry."""
    result = await assess_impact(db, entry_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    await db.commit()
    return result


@router.post(
    "/freshness-watch/{entry_id}/apply",
)
async def apply_watch_reactions(
    entry_id: UUID,
    current_user: User = Depends(require_permission("jurisdictions", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Apply the required reactions for a freshness watch entry."""
    result = await apply_reactions(db, entry_id, applied_by_id=current_user.id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    await db.commit()
    return result


@router.post(
    "/freshness-watch/{entry_id}/dismiss",
    response_model=FreshnessWatchRead,
)
async def dismiss_watch_entry(
    entry_id: UUID,
    payload: FreshnessWatchDismiss,
    current_user: User = Depends(require_permission("jurisdictions", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Dismiss a freshness watch entry as not impactful."""
    entry = await dismiss_watch(db, entry_id, dismissed_by_id=current_user.id, reason=payload.reason)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    await db.commit()
    return entry
