"""BatiConnect — Owner Ops API routes.

Recurring services, warranty records, owner dashboard, and annual costs.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.recurring_service import (
    RecurringServiceCreate,
    RecurringServiceRead,
    RecurringServiceUpdate,
    ServicePerformedRequest,
)
from app.schemas.warranty_record import WarrantyRecordCreate, WarrantyRecordRead, WarrantyRecordUpdate
from app.services.owner_ops_service import (
    create_recurring_service,
    create_warranty,
    get_annual_cost_summary,
    get_expiring_warranties,
    get_owner_dashboard,
    get_recurring_service,
    get_upcoming_services,
    get_warranty,
    list_recurring_services,
    list_warranties,
    record_service_performed,
    update_recurring_service,
    update_warranty,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


# ---------------------------------------------------------------------------
# Owner Dashboard
# ---------------------------------------------------------------------------


@router.get("/buildings/{building_id}/owner-dashboard")
async def owner_dashboard_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Owner-level operational dashboard for a building."""
    result = await get_owner_dashboard(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


# ---------------------------------------------------------------------------
# Recurring Services
# ---------------------------------------------------------------------------


@router.get(
    "/buildings/{building_id}/recurring-services",
    response_model=list[RecurringServiceRead],
)
async def list_services_endpoint(
    building_id: UUID,
    status: str | None = None,
    service_type: str | None = None,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    return await list_recurring_services(db, building_id, status_filter=status, service_type=service_type)


@router.post(
    "/buildings/{building_id}/recurring-services",
    response_model=RecurringServiceRead,
    status_code=201,
)
async def create_service_endpoint(
    building_id: UUID,
    payload: RecurringServiceCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=400, detail="User has no organization")
    data = payload.model_dump(exclude_unset=True)
    service = await create_recurring_service(db, building_id, org_id, data)
    await db.commit()
    return service


@router.put(
    "/recurring-services/{service_id}",
    response_model=RecurringServiceRead,
)
async def update_service_endpoint(
    service_id: UUID,
    payload: RecurringServiceUpdate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    service = await get_recurring_service(db, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Recurring service not found")
    data = payload.model_dump(exclude_unset=True)
    updated = await update_recurring_service(db, service, data)
    await db.commit()
    return updated


@router.post(
    "/recurring-services/{service_id}/performed",
    response_model=RecurringServiceRead,
)
async def service_performed_endpoint(
    service_id: UUID,
    payload: ServicePerformedRequest,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Record that a recurring service was performed."""
    service = await get_recurring_service(db, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Recurring service not found")
    updated = await record_service_performed(db, service, payload.performed_date, payload.notes)
    await db.commit()
    return updated


@router.get(
    "/buildings/{building_id}/recurring-services/upcoming",
    response_model=list[RecurringServiceRead],
)
async def upcoming_services_endpoint(
    building_id: UUID,
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    return await get_upcoming_services(db, building_id, horizon_days=days)


# ---------------------------------------------------------------------------
# Warranty Records
# ---------------------------------------------------------------------------


@router.get(
    "/buildings/{building_id}/warranties",
    response_model=list[WarrantyRecordRead],
)
async def list_warranties_endpoint(
    building_id: UUID,
    status: str | None = None,
    warranty_type: str | None = None,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    return await list_warranties(db, building_id, status_filter=status, warranty_type=warranty_type)


@router.post(
    "/buildings/{building_id}/warranties",
    response_model=WarrantyRecordRead,
    status_code=201,
)
async def create_warranty_endpoint(
    building_id: UUID,
    payload: WarrantyRecordCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=400, detail="User has no organization")
    data = payload.model_dump(exclude_unset=True)
    warranty = await create_warranty(db, building_id, org_id, data)
    await db.commit()
    return warranty


@router.put(
    "/warranties/{warranty_id}",
    response_model=WarrantyRecordRead,
)
async def update_warranty_endpoint(
    warranty_id: UUID,
    payload: WarrantyRecordUpdate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    warranty = await get_warranty(db, warranty_id)
    if not warranty:
        raise HTTPException(status_code=404, detail="Warranty record not found")
    data = payload.model_dump(exclude_unset=True)
    updated = await update_warranty(db, warranty, data)
    await db.commit()
    return updated


@router.get(
    "/buildings/{building_id}/warranties/expiring",
    response_model=list[WarrantyRecordRead],
)
async def expiring_warranties_endpoint(
    building_id: UUID,
    days: int = Query(180, ge=1, le=730),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    return await get_expiring_warranties(db, building_id, horizon_days=days)


# ---------------------------------------------------------------------------
# Annual Costs
# ---------------------------------------------------------------------------


@router.get("/buildings/{building_id}/annual-costs")
async def annual_costs_endpoint(
    building_id: UUID,
    year: int | None = None,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Annual cost summary for a building."""
    result = await get_annual_cost_summary(db, building_id, year=year)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result
