"""Public registry lookup and building enrichment API."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.registry import (
    AddressSearchResult,
    EnrichmentResult,
    NaturalHazardsResult,
    RegistryLookupResult,
)
from app.services.registry_connector_service import (
    enrich_building_from_registry,
    get_natural_hazards,
    lookup_by_address,
    lookup_by_egid,
)

router = APIRouter()


@router.get("/registry/lookup/egid/{egid}", response_model=RegistryLookupResult | None)
async def registry_lookup_egid(
    egid: int,
    current_user: User = Depends(require_permission("buildings", "read")),
):
    """Look up building data from the federal RegBL registry by EGID."""
    result = await lookup_by_egid(egid)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No RegBL record found for EGID {egid}")
    return result


@router.get("/registry/lookup/address", response_model=list[AddressSearchResult])
async def registry_lookup_address(
    q: str = Query(..., min_length=2, description="Address search query"),
    postal_code: str | None = Query(None, description="Optional postal code filter"),
    current_user: User = Depends(require_permission("buildings", "read")),
):
    """Search for buildings/locations via Swisstopo geocoding."""
    results = await lookup_by_address(q, postal_code=postal_code)
    return results


@router.get("/registry/hazards", response_model=NaturalHazardsResult)
async def registry_natural_hazards(
    lat: float = Query(..., description="Latitude (WGS84)"),
    lng: float = Query(..., description="Longitude (WGS84)"),
    current_user: User = Depends(require_permission("buildings", "read")),
):
    """Get natural hazard data at given coordinates."""
    result = await get_natural_hazards(lat, lng)
    return result


@router.post("/buildings/{building_id}/enrich", response_model=EnrichmentResult)
async def enrich_building(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Auto-enrich a building from Swiss public registries (RegBL, Swisstopo, hazards).

    Only fills empty fields — never overwrites user-entered data.
    """
    try:
        result = await enrich_building_from_registry(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return result
