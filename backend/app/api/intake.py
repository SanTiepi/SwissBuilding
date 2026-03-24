"""BatiConnect — Intake Request API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.limiter import limiter
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.intake import (
    IntakeConvertRequest,
    IntakeQualifyRequest,
    IntakeRejectRequest,
    IntakeRequestCreate,
    IntakeRequestRead,
)
from app.services.intake_service import (
    convert_request,
    get_request,
    list_requests,
    qualify_request,
    reject_request,
    submit_request,
)

router = APIRouter()


# ---- Public endpoint (no auth) ----


@router.post(
    "/public/intake",
    response_model=IntakeRequestRead,
    status_code=201,
)
@limiter.limit("10/minute")
async def submit_intake(
    request: Request,
    payload: IntakeRequestCreate,
    db: AsyncSession = Depends(get_db),
):
    """Public intake form submission — no authentication required."""
    data = payload.model_dump(exclude_unset=True)
    intake = await submit_request(db, data)
    await db.commit()
    return intake


# ---- Admin endpoints (auth required) ----


@router.get(
    "/intake-requests",
    response_model=PaginatedResponse[IntakeRequestRead],
)
async def list_intake_requests(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    current_user: User = Depends(require_permission("buildings", "list")),
    db: AsyncSession = Depends(get_db),
):
    items, total = await list_requests(db, page=page, size=size, status=status)
    pages = (total + size - 1) // size if total > 0 else 0
    return {"items": items, "total": total, "page": page, "size": size, "pages": pages}


@router.get(
    "/intake-requests/{intake_id}",
    response_model=IntakeRequestRead,
)
async def get_intake_request(
    intake_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    intake = await get_request(db, intake_id)
    if not intake:
        raise HTTPException(status_code=404, detail="Intake request not found")
    return intake


@router.post(
    "/intake-requests/{intake_id}/qualify",
    response_model=IntakeRequestRead,
)
async def qualify_intake_request(
    intake_id: UUID,
    payload: IntakeQualifyRequest,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    intake = await get_request(db, intake_id)
    if not intake:
        raise HTTPException(status_code=404, detail="Intake request not found")
    if intake.status != "new":
        raise HTTPException(status_code=400, detail=f"Cannot qualify intake with status '{intake.status}'")
    result = await qualify_request(db, intake, current_user.id, notes=payload.notes)
    await db.commit()
    return result


@router.post(
    "/intake-requests/{intake_id}/convert",
    response_model=IntakeRequestRead,
)
async def convert_intake_request(
    intake_id: UUID,
    payload: IntakeConvertRequest,
    current_user: User = Depends(require_permission("buildings", "create")),
    db: AsyncSession = Depends(get_db),
):
    intake = await get_request(db, intake_id)
    if not intake:
        raise HTTPException(status_code=404, detail="Intake request not found")
    if intake.status not in ("new", "qualified"):
        raise HTTPException(status_code=400, detail=f"Cannot convert intake with status '{intake.status}'")
    result = await convert_request(
        db, intake, current_user.id, organization_id=payload.organization_id, notes=payload.notes
    )
    await db.commit()
    return result


@router.post(
    "/intake-requests/{intake_id}/reject",
    response_model=IntakeRequestRead,
)
async def reject_intake_request(
    intake_id: UUID,
    payload: IntakeRejectRequest,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    intake = await get_request(db, intake_id)
    if not intake:
        raise HTTPException(status_code=404, detail="Intake request not found")
    if intake.status not in ("new", "qualified"):
        raise HTTPException(status_code=400, detail=f"Cannot reject intake with status '{intake.status}'")
    result = await reject_request(db, intake, current_user.id, reason=payload.reason)
    await db.commit()
    return result
