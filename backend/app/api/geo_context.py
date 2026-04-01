"""Geo context overlay API — exposes geo.admin public data for buildings."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.geo_context import GeoContextRefreshResponse, GeoContextResponse
from app.services.geo_context_service import enrich_building_context, get_building_context

router = APIRouter()


@router.get("/buildings/{building_id}/geo-context", response_model=GeoContextResponse)
async def get_geo_context(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get geo.admin context overlays for a building (cached or fresh)."""
    try:
        result = await get_building_context(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return result


@router.post("/buildings/{building_id}/geo-context/refresh", response_model=GeoContextRefreshResponse)
async def refresh_geo_context(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Force refresh geo.admin context overlays for a building."""
    try:
        context_data = await enrich_building_context(db, building_id, force=True)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    if "error" in context_data:
        raise HTTPException(status_code=400, detail=context_data.get("detail", "Cannot fetch geo context"))

    return GeoContextRefreshResponse(
        context=context_data,
        fetched_at=datetime.now(UTC),
        source_version="geo.admin-v1",
        layers_count=len(context_data),
    )
