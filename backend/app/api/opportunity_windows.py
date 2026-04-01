"""Opportunity Window API endpoints.

Provides per-building and portfolio-level access to detected opportunity windows.
"""

from __future__ import annotations

from collections import Counter
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.opportunity_window import (
    OpportunityWindowDetectResponse,
    OpportunityWindowListResponse,
    OpportunityWindowResponse,
    PortfolioWindowListResponse,
    WindowTypeSummary,
)
from app.services.opportunity_window_service import (
    detect_windows,
    list_building_windows,
    list_portfolio_windows,
)

router = APIRouter()


def _summarize_by_type(windows: list) -> list[WindowTypeSummary]:
    """Build per-type summary from a list of window objects."""
    counts: Counter[str] = Counter()
    for w in windows:
        wtype = w.window_type if hasattr(w, "window_type") else w.get("window_type", "unknown")
        counts[wtype] += 1
    return [WindowTypeSummary(window_type=k, count=v) for k, v in sorted(counts.items())]


@router.get(
    "/opportunity-windows/portfolio",
    response_model=PortfolioWindowListResponse,
    tags=["Opportunity Windows"],
)
async def api_list_portfolio_windows(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List all active opportunity windows across portfolio (org-scoped)."""
    windows = await list_portfolio_windows(db, org_id)
    resp_windows = [OpportunityWindowResponse.model_validate(w) for w in windows]
    building_ids = {w.building_id for w in windows}
    return PortfolioWindowListResponse(
        organization_id=org_id,
        windows=resp_windows,
        total=len(resp_windows),
        by_type=_summarize_by_type(windows),
        buildings_with_windows=len(building_ids),
    )


@router.get(
    "/opportunity-windows/{building_id}",
    response_model=OpportunityWindowListResponse,
    tags=["Opportunity Windows"],
)
async def api_list_building_windows(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List all active (non-expired) windows for a building."""
    windows = await list_building_windows(db, building_id)
    resp_windows = [OpportunityWindowResponse.model_validate(w) for w in windows]
    return OpportunityWindowListResponse(
        windows=resp_windows,
        total=len(resp_windows),
        by_type=_summarize_by_type(windows),
    )


@router.post(
    "/opportunity-windows/{building_id}/detect",
    response_model=OpportunityWindowDetectResponse,
    tags=["Opportunity Windows"],
)
async def api_detect_windows(
    building_id: UUID,
    horizon_days: int = 365,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Trigger detection of opportunity windows for a building."""
    try:
        created = await detect_windows(db, building_id, horizon_days=horizon_days)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    # Re-fetch all active windows to include previously detected ones
    all_active = await list_building_windows(db, building_id)
    resp_windows = [OpportunityWindowResponse.model_validate(w) for w in all_active]
    return OpportunityWindowDetectResponse(
        detected=len(all_active),
        new=len(created),
        windows=resp_windows,
        by_type=_summarize_by_type(all_active),
    )
