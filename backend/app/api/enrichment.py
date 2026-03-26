"""Building enrichment API — endpoints for auto-enrichment pipeline."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.enrichment import (
    BatchEnrichmentRequest,
    BatchEnrichmentResult,
    EnrichmentRequest,
    EnrichmentResult,
    EnrichmentStatus,
)

router = APIRouter()


@router.post("/buildings/{building_id}/enrich", response_model=EnrichmentResult)
async def enrich_single_building(
    building_id: UUID,
    body: EnrichmentRequest | None = None,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Enrich a single building with data from Swiss public APIs and AI."""
    from app.services.building_enrichment_service import enrich_building

    skip_geocode = body.skip_geocode if body else False
    skip_regbl = body.skip_regbl if body else False
    skip_ai = body.skip_ai if body else False
    skip_cadastre = body.skip_cadastre if body else False
    skip_image = body.skip_image if body else False

    try:
        result = await enrich_building(
            db,
            building_id,
            skip_geocode=skip_geocode,
            skip_regbl=skip_regbl,
            skip_ai=skip_ai,
            skip_cadastre=skip_cadastre,
            skip_image=skip_image,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enrichment failed: {e}") from e

    if result.errors and not result.fields_updated:
        raise HTTPException(status_code=404, detail=result.errors[0])

    await db.commit()
    return result


@router.post("/buildings/enrich-all", response_model=BatchEnrichmentResult)
async def enrich_all_buildings_endpoint(
    body: BatchEnrichmentRequest | None = None,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Batch enrich all buildings (admin only via RBAC)."""
    from app.services.building_enrichment_service import enrich_all_buildings

    org_id = body.org_id if body else None
    skip_geocode = body.skip_geocode if body else False
    skip_regbl = body.skip_regbl if body else False
    skip_ai = body.skip_ai if body else False

    results = await enrich_all_buildings(
        db,
        org_id=org_id,
        skip_geocode=skip_geocode,
        skip_regbl=skip_regbl,
        skip_ai=skip_ai,
    )

    await db.commit()

    enriched = sum(1 for r in results if r.fields_updated)
    error_count = sum(1 for r in results if r.errors)

    return BatchEnrichmentResult(
        total=len(results),
        enriched=enriched,
        error_count=error_count,
        results=results,
    )


@router.get("/buildings/{building_id}/enrichment-status", response_model=EnrichmentStatus)
async def get_enrichment_status(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Check what data has been enriched for a building."""
    from sqlalchemy import select

    from app.models.building import Building

    stmt = select(Building).where(Building.id == building_id)
    row = await db.execute(stmt)
    building = row.scalar_one_or_none()

    if building is None:
        raise HTTPException(status_code=404, detail="Building not found")

    meta = building.source_metadata_json or {}

    return EnrichmentStatus(
        building_id=building_id,
        has_coordinates=building.latitude is not None and building.longitude is not None,
        has_egid=building.egid is not None,
        has_egrid=building.egrid is not None,
        has_construction_year=building.construction_year is not None,
        has_floors=building.floors_above is not None,
        has_image_url=bool(meta.get("image_url")),
        has_ai_description=bool(meta.get("ai_enrichment")),
        enrichment_metadata=meta if meta else None,
    )
