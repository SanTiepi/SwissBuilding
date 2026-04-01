"""Spatial enrichment API — exposes swissBUILDINGS3D data for buildings."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.spatial_enrichment import SpatialEnrichmentRefreshResponse, SpatialEnrichmentResponse
from app.services.spatial_enrichment_service import SpatialEnrichmentService

router = APIRouter()


@router.get("/buildings/{building_id}/spatial-enrichment", response_model=SpatialEnrichmentResponse)
async def get_spatial_enrichment(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get swissBUILDINGS3D spatial enrichment data for a building (cached or fresh)."""
    try:
        result = await SpatialEnrichmentService.get_building_spatial(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return result


@router.post("/buildings/{building_id}/spatial-enrichment/refresh", response_model=SpatialEnrichmentRefreshResponse)
async def refresh_spatial_enrichment(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Force refresh swissBUILDINGS3D spatial enrichment data for a building."""
    try:
        result = await SpatialEnrichmentService.enrich_building_spatial(db, building_id, force=True)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    if "error" in result:
        raise HTTPException(
            status_code=400, detail=result.get("detail", "Impossible de recuperer les donnees spatiales")
        )

    return SpatialEnrichmentRefreshResponse(
        footprint_wkt=result.get("footprint_wkt"),
        height_m=result.get("height_m"),
        roof_type=result.get("roof_type"),
        volume_m3=result.get("volume_m3"),
        surface_m2=result.get("surface_m2"),
        floors=result.get("floors"),
        source=result.get("source"),
        source_version=result.get("source_version"),
        fetched_at=result.get("fetched_at"),
        raw_attributes=result.get("raw_attributes", {}),
        building_updated=True,
    )
