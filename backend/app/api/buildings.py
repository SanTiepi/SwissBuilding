import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.activity import ActivityItemRead
from app.schemas.building import BuildingCreate, BuildingListRead, BuildingRead, BuildingUpdate
from app.schemas.common import PaginatedResponse
from app.schemas.equipment import EquipmentTimelineResponse
from app.services.audit_service import log_action
from app.services.building_service import (
    create_building,
    delete_building,
    get_building,
    list_buildings,
    update_building,
)
from app.services.building_similarity_service import BuildingSimilarityService
from app.services.pollutant_prevalence_service import PollutantPrevalenceService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=PaginatedResponse[BuildingListRead])
async def list_buildings_endpoint(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    canton: str | None = None,
    city: str | None = None,
    postal_code: str | None = None,
    building_type: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    search: str | None = None,
    current_user: User = Depends(require_permission("buildings", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List buildings with filtering and pagination."""
    buildings_list, total = await list_buildings(
        db, page, size, canton, city, postal_code, building_type, year_from, year_to, search
    )
    pages = (total + size - 1) // size
    return {
        "items": buildings_list,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
    }


@router.post("", response_model=BuildingRead, status_code=201)
async def create_building_endpoint(
    data: BuildingCreate,
    current_user: User = Depends(require_permission("buildings", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new building."""
    building = await create_building(
        db,
        data,
        current_user.id,
        organization_id=current_user.organization_id,
    )
    await log_action(db, current_user.id, "create", "building", building.id)
    try:
        from app.services.search_service import index_building

        index_building(building)
    except Exception:
        logger.warning("Search index operation failed", exc_info=True)
    return building


@router.get("/{building_id}", response_model=BuildingRead)
async def get_building_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a single building by ID."""
    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


@router.put("/{building_id}", response_model=BuildingRead)
async def update_building_endpoint(
    building_id: UUID,
    data: BuildingUpdate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing building."""
    building = await update_building(db, building_id, data)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    await log_action(db, current_user.id, "update", "building", building_id)
    try:
        from app.services.search_service import index_building

        index_building(building)
    except Exception:
        logger.warning("Search index operation failed", exc_info=True)
    return building


@router.delete("/{building_id}", status_code=204)
async def delete_building_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "delete")),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a building."""
    success = await delete_building(db, building_id)
    if not success:
        raise HTTPException(status_code=404, detail="Building not found")
    await log_action(db, current_user.id, "delete", "building", building_id)
    try:
        from app.services.search_service import delete_building as search_delete_building

        search_delete_building(str(building_id))
    except Exception:
        logger.warning("Search index operation failed", exc_info=True)


@router.get("/{building_id}/activity", response_model=list[ActivityItemRead])
async def get_building_activity_endpoint(
    building_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated activity timeline for a building."""
    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    from app.services.activity_service import get_building_activity

    return await get_building_activity(db, building_id, limit=limit, offset=offset)


@router.get("/{building_id}/equipment/timeline", response_model=EquipmentTimelineResponse)
async def get_equipment_timeline_endpoint(
    building_id: UUID,
    years: int = Query(10, ge=1, le=50),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get equipment replacement timeline forecast."""
    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    from app.services.equipment_lifecycle_service import get_equipment_timeline

    return await get_equipment_timeline(db, building_id, years=years)


@router.get("/{building_id}/similar")
async def get_similar_buildings_endpoint(
    building_id: UUID,
    max_results: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Find buildings similar to the specified building.

    Similar buildings match on:
    - Construction year (±5 years)
    - Building type (exact match)
    - Canton (exact match)
    - Must have at least one diagnostic
    """
    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    similar = await BuildingSimilarityService.find_similar_buildings(db, building_id, max_results=max_results)

    similar_data = []
    for b in similar:
        score = await BuildingSimilarityService.similarity_score(db, building_id, b.id)
        similar_data.append(
            {
                "id": str(b.id),
                "address": b.address,
                "city": b.city,
                "postal_code": b.postal_code,
                "canton": b.canton,
                "construction_year": b.construction_year,
                "building_type": b.building_type,
                "similarity_score": score,
            }
        )

    return {
        "building_id": str(building_id),
        "similar_count": len(similar),
        "similar_buildings": similar_data,
    }


@router.get("/{building_id}/pollutant-predictions")
async def get_pollutant_predictions_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get pollutant predictions based on similar buildings.

    Returns top 5 pollutants by probability of occurrence based on
    diagnostic patterns observed in similar buildings.
    """
    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    predictions = await PollutantPrevalenceService.get_building_pollutant_predictions(db, building_id)

    return predictions


# ---------------------------------------------------------------------------
# Completeness Dashboard (16-dimension)
# ---------------------------------------------------------------------------


@router.get("/{building_id}/completeness/dashboard")
async def get_completeness_dashboard_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get 16-dimension completeness dashboard for a building."""
    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    from app.services.completeness_scorer import calculate_completeness

    return await calculate_completeness(db, building_id)


@router.get("/{building_id}/completeness/missing-items")
async def get_completeness_missing_items_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed checklist of missing items across all 16 dimensions."""
    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    from app.services.completeness_scorer import get_missing_items

    items = await get_missing_items(db, building_id)
    return {"building_id": str(building_id), "items": items, "total": len(items)}


@router.get("/{building_id}/completeness/recommended-actions")
async def get_completeness_actions_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get prioritized recommended actions to improve completeness."""
    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    from app.services.completeness_scorer import get_recommended_actions

    actions = await get_recommended_actions(db, building_id)
    return {"building_id": str(building_id), "actions": actions, "total": len(actions)}
