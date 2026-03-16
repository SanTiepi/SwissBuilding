"""Data provenance tracking API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.data_provenance import (
    DataLineageTree,
    IntegrityReport,
    ProvenanceRecord,
    ProvenanceStatistics,
)
from app.services.data_provenance_service import (
    get_building_data_lineage,
    get_data_provenance,
    get_provenance_statistics,
    verify_data_integrity,
)

router = APIRouter()

VALID_ENTITY_TYPES = {"building", "diagnostic", "sample", "document", "action"}


@router.get(
    "/provenance/{entity_type}/{entity_id}",
    response_model=ProvenanceRecord,
)
async def get_provenance_endpoint(
    entity_type: str,
    entity_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get provenance chain for a single entity."""
    if entity_type not in VALID_ENTITY_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid entity_type '{entity_type}'. Must be one of: {', '.join(sorted(VALID_ENTITY_TYPES))}",
        )
    record = await get_data_provenance(db, entity_type, entity_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"{entity_type} not found")
    return record


@router.get(
    "/buildings/{building_id}/lineage",
    response_model=DataLineageTree,
)
async def get_lineage_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get full data lineage tree for a building."""
    tree = await get_building_data_lineage(db, building_id)
    if not tree:
        raise HTTPException(status_code=404, detail="Building not found")
    return tree


@router.get(
    "/buildings/{building_id}/integrity",
    response_model=IntegrityReport,
)
async def verify_integrity_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Verify data integrity for a building."""
    report = await verify_data_integrity(db, building_id)
    if not report:
        raise HTTPException(status_code=404, detail="Building not found")
    return report


@router.get(
    "/provenance/statistics",
    response_model=ProvenanceStatistics,
)
async def get_statistics_endpoint(
    org_id: UUID | None = None,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get provenance statistics, optionally filtered by organization."""
    return await get_provenance_statistics(db, org_id)
