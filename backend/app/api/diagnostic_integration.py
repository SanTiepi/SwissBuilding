"""BatiConnect — Diagnostic integration API routes (publications & mission orders)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.diagnostic_publication import (
    DiagnosticMissionOrderCreate,
    DiagnosticMissionOrderRead,
    DiagnosticPublicationPackage,
    DiagnosticReportPublicationRead,
    PublicationMatchRequest,
)
from app.services.diagnostic_integration_service import (
    create_mission_order,
    get_mission_orders_for_building,
    get_publication_with_versions,
    get_publications_for_building,
    get_unmatched_publications,
    match_publication,
    receive_publication,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


# ---------------------------------------------------------------------------
# Publications
# ---------------------------------------------------------------------------


@router.post(
    "/diagnostic-publications",
    response_model=DiagnosticReportPublicationRead,
    status_code=201,
)
async def receive_publication_endpoint(
    payload: DiagnosticPublicationPackage,
    db: AsyncSession = Depends(get_db),
):
    """Webhook endpoint — receive a diagnostic report publication from Batiscan."""
    publication = await receive_publication(db, payload)
    await db.commit()
    return publication


@router.get(
    "/buildings/{building_id}/diagnostic-publications",
    response_model=list[DiagnosticReportPublicationRead],
)
async def list_building_publications_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    return await get_publications_for_building(db, building_id)


@router.get(
    "/diagnostic-publications/unmatched",
    response_model=list[DiagnosticReportPublicationRead],
)
async def list_unmatched_publications_endpoint(
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return await get_unmatched_publications(db)


@router.get(
    "/diagnostic-publications/{publication_id}",
    response_model=DiagnosticReportPublicationRead,
)
async def get_publication_endpoint(
    publication_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await get_publication_with_versions(db, publication_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Publication not found") from None


@router.post(
    "/diagnostic-publications/{publication_id}/match",
    response_model=DiagnosticReportPublicationRead,
)
async def match_publication_endpoint(
    publication_id: UUID,
    payload: PublicationMatchRequest,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    try:
        publication = await match_publication(db, publication_id, payload.building_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    await db.commit()
    return publication


# ---------------------------------------------------------------------------
# Mission Orders
# ---------------------------------------------------------------------------


@router.post(
    "/diagnostic-mission-orders",
    response_model=DiagnosticMissionOrderRead,
    status_code=201,
)
async def create_mission_order_endpoint(
    payload: DiagnosticMissionOrderCreate,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    try:
        order = await create_mission_order(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    await db.commit()
    return order


@router.get(
    "/buildings/{building_id}/mission-orders",
    response_model=list[DiagnosticMissionOrderRead],
)
async def list_building_mission_orders_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    return await get_mission_orders_for_building(db, building_id)
