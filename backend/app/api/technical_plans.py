from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.plan_annotation import PlanAnnotation
from app.models.technical_plan import TechnicalPlan
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.plan_annotation import PlanAnnotationCreate, PlanAnnotationRead, PlanAnnotationUpdate
from app.schemas.plan_heatmap import CoverageGapReport, PlanHeatmap, ZoneHeatmapStats
from app.schemas.technical_plan import TechnicalPlanCreate, TechnicalPlanRead
from app.services.plan_heatmap_service import (
    detect_coverage_gaps,
    generate_plan_heatmap,
    get_heatmap_at_date,
    get_zone_heatmap_stats,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


async def _get_plan_or_404(db: AsyncSession, building_id: UUID, plan_id: UUID) -> TechnicalPlan:
    result = await db.execute(
        select(TechnicalPlan).where(
            TechnicalPlan.id == plan_id,
            TechnicalPlan.building_id == building_id,
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Technical plan not found")
    return plan


@router.get(
    "/buildings/{building_id}/plans",
    response_model=PaginatedResponse[TechnicalPlanRead],
)
async def list_plans_endpoint(
    building_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    plan_type: str | None = None,
    current_user: User = Depends(require_permission("plans", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List technical plans for a building with optional filter and pagination."""
    await _get_building_or_404(db, building_id)

    query = select(TechnicalPlan).where(TechnicalPlan.building_id == building_id)
    count_query = select(func.count()).select_from(TechnicalPlan).where(TechnicalPlan.building_id == building_id)

    if plan_type:
        query = query.where(TechnicalPlan.plan_type == plan_type)
        count_query = count_query.where(TechnicalPlan.plan_type == plan_type)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    items = result.scalars().all()

    pages = (total + size - 1) // size if total > 0 else 0
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
    }


@router.post(
    "/buildings/{building_id}/plans",
    response_model=TechnicalPlanRead,
    status_code=201,
)
async def create_plan_endpoint(
    building_id: UUID,
    data: TechnicalPlanCreate,
    current_user: User = Depends(require_permission("plans", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new technical plan for a building (JSON body, no file upload)."""
    await _get_building_or_404(db, building_id)

    plan = TechnicalPlan(
        building_id=building_id,
        uploaded_by=current_user.id,
        **data.model_dump(),
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


@router.get(
    "/buildings/{building_id}/plans/{plan_id}",
    response_model=TechnicalPlanRead,
)
async def get_plan_endpoint(
    building_id: UUID,
    plan_id: UUID,
    current_user: User = Depends(require_permission("plans", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a single technical plan."""
    await _get_building_or_404(db, building_id)
    return await _get_plan_or_404(db, building_id, plan_id)


@router.delete(
    "/buildings/{building_id}/plans/{plan_id}",
    status_code=204,
)
async def delete_plan_endpoint(
    building_id: UUID,
    plan_id: UUID,
    current_user: User = Depends(require_permission("plans", "delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a technical plan."""
    await _get_building_or_404(db, building_id)
    plan = await _get_plan_or_404(db, building_id, plan_id)
    await db.delete(plan)
    await db.commit()


# ---------------------------------------------------------------------------
# Plan Heatmap endpoint
# ---------------------------------------------------------------------------


@router.get(
    "/buildings/{building_id}/plans/{plan_id}/heatmap",
    response_model=PlanHeatmap,
)
async def get_plan_heatmap_endpoint(
    building_id: UUID,
    plan_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a proof heatmap overlay for a technical plan."""
    await _get_building_or_404(db, building_id)
    await _get_plan_or_404(db, building_id, plan_id)
    return await generate_plan_heatmap(db, plan_id, building_id)


@router.get(
    "/buildings/{building_id}/plans/{plan_id}/heatmap/at-date",
    response_model=PlanHeatmap,
)
async def get_plan_heatmap_at_date_endpoint(
    building_id: UUID,
    plan_id: UUID,
    target_date: str = Query(..., description="ISO date (YYYY-MM-DD)"),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a heatmap snapshot as it would have been at a given date."""
    from datetime import date

    await _get_building_or_404(db, building_id)
    await _get_plan_or_404(db, building_id, plan_id)
    parsed_date = date.fromisoformat(target_date)
    return await get_heatmap_at_date(db, plan_id, building_id, parsed_date)


@router.get(
    "/buildings/{building_id}/plans/{plan_id}/coverage-gaps",
    response_model=CoverageGapReport,
)
async def get_coverage_gaps_endpoint(
    building_id: UUID,
    plan_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Identify coverage gaps for zones on a technical plan."""
    await _get_building_or_404(db, building_id)
    await _get_plan_or_404(db, building_id, plan_id)
    return await detect_coverage_gaps(db, plan_id, building_id)


@router.get(
    "/buildings/{building_id}/zone-heatmap-stats",
    response_model=list[ZoneHeatmapStats],
)
async def get_zone_heatmap_stats_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return per-zone aggregated proof density and coverage stats."""
    await _get_building_or_404(db, building_id)
    return await get_zone_heatmap_stats(db, building_id)


# ---------------------------------------------------------------------------
# Plan Annotation helpers
# ---------------------------------------------------------------------------


async def _get_annotation_or_404(
    db: AsyncSession, building_id: UUID, plan_id: UUID, annotation_id: UUID
) -> PlanAnnotation:
    result = await db.execute(
        select(PlanAnnotation).where(
            PlanAnnotation.id == annotation_id,
            PlanAnnotation.plan_id == plan_id,
            PlanAnnotation.building_id == building_id,
        )
    )
    annotation = result.scalar_one_or_none()
    if not annotation:
        raise HTTPException(status_code=404, detail="Plan annotation not found")
    return annotation


# ---------------------------------------------------------------------------
# Plan Annotation endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/buildings/{building_id}/plans/{plan_id}/annotations",
    response_model=list[PlanAnnotationRead],
)
async def list_annotations_endpoint(
    building_id: UUID,
    plan_id: UUID,
    annotation_type: str | None = None,
    current_user: User = Depends(require_permission("plans", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List annotations for a technical plan."""
    await _get_building_or_404(db, building_id)
    await _get_plan_or_404(db, building_id, plan_id)

    query = select(PlanAnnotation).where(
        PlanAnnotation.plan_id == plan_id,
        PlanAnnotation.building_id == building_id,
    )
    if annotation_type:
        query = query.where(PlanAnnotation.annotation_type == annotation_type)

    result = await db.execute(query)
    return result.scalars().all()


@router.post(
    "/buildings/{building_id}/plans/{plan_id}/annotations",
    response_model=PlanAnnotationRead,
    status_code=201,
)
async def create_annotation_endpoint(
    building_id: UUID,
    plan_id: UUID,
    data: PlanAnnotationCreate,
    current_user: User = Depends(require_permission("plans", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new annotation on a technical plan."""
    await _get_building_or_404(db, building_id)
    await _get_plan_or_404(db, building_id, plan_id)

    annotation = PlanAnnotation(
        plan_id=plan_id,
        building_id=building_id,
        created_by=current_user.id,
        **data.model_dump(),
    )
    db.add(annotation)
    await db.commit()
    await db.refresh(annotation)
    return annotation


@router.get(
    "/buildings/{building_id}/plans/{plan_id}/annotations/{annotation_id}",
    response_model=PlanAnnotationRead,
)
async def get_annotation_endpoint(
    building_id: UUID,
    plan_id: UUID,
    annotation_id: UUID,
    current_user: User = Depends(require_permission("plans", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a single plan annotation."""
    await _get_building_or_404(db, building_id)
    await _get_plan_or_404(db, building_id, plan_id)
    return await _get_annotation_or_404(db, building_id, plan_id, annotation_id)


@router.put(
    "/buildings/{building_id}/plans/{plan_id}/annotations/{annotation_id}",
    response_model=PlanAnnotationRead,
)
async def update_annotation_endpoint(
    building_id: UUID,
    plan_id: UUID,
    annotation_id: UUID,
    data: PlanAnnotationUpdate,
    current_user: User = Depends(require_permission("plans", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a plan annotation."""
    await _get_building_or_404(db, building_id)
    await _get_plan_or_404(db, building_id, plan_id)
    annotation = await _get_annotation_or_404(db, building_id, plan_id, annotation_id)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(annotation, field, value)

    await db.commit()
    await db.refresh(annotation)
    return annotation


@router.delete(
    "/buildings/{building_id}/plans/{plan_id}/annotations/{annotation_id}",
    status_code=204,
)
async def delete_annotation_endpoint(
    building_id: UUID,
    plan_id: UUID,
    annotation_id: UUID,
    current_user: User = Depends(require_permission("plans", "delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a plan annotation."""
    await _get_building_or_404(db, building_id)
    await _get_plan_or_404(db, building_id, plan_id)
    annotation = await _get_annotation_or_404(db, building_id, plan_id, annotation_id)
    await db.delete(annotation)
    await db.commit()
