"""BatiConnect — Permit Procedure API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.permit_procedure import (
    AuthorityRequestCreate,
    AuthorityRequestRead,
    AuthorityRequestRespond,
    ProcedureBlockerRead,
    ProcedureCreate,
    ProcedureListRead,
    ProcedureRead,
    StepRead,
)
from app.services.permit_procedure_service import (
    advance_step,
    approve_procedure,
    create_procedure,
    get_procedural_blockers,
    get_procedure_detail,
    get_procedures,
    reject_procedure,
    request_complement,
    respond_to_request,
    submit_procedure,
    withdraw_procedure,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


async def _get_procedure_or_404(db: AsyncSession, procedure_id: UUID):
    procedure = await get_procedure_detail(db, procedure_id)
    if not procedure:
        raise HTTPException(status_code=404, detail="Procedure not found")
    return procedure


# 1. List procedures for a building
@router.get(
    "/buildings/{building_id}/permit-procedures",
    response_model=list[ProcedureListRead],
)
async def list_procedures_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("compliance_artefacts", "list")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    return await get_procedures(db, building_id)


# 2. Create a procedure
@router.post(
    "/buildings/{building_id}/permit-procedures",
    response_model=ProcedureRead,
    status_code=201,
)
async def create_procedure_endpoint(
    building_id: UUID,
    payload: ProcedureCreate,
    current_user: User = Depends(require_permission("compliance_artefacts", "create")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    data = payload.model_dump(exclude_unset=True)
    procedure = await create_procedure(db, building_id, data)
    await db.commit()
    return await get_procedure_detail(db, procedure.id)


# 3. Get procedure detail
@router.get(
    "/permit-procedures/{procedure_id}",
    response_model=ProcedureRead,
)
async def get_procedure_endpoint(
    procedure_id: UUID,
    current_user: User = Depends(require_permission("compliance_artefacts", "read")),
    db: AsyncSession = Depends(get_db),
):
    return await _get_procedure_or_404(db, procedure_id)


# 4. Submit procedure
@router.post(
    "/permit-procedures/{procedure_id}/submit",
    response_model=ProcedureRead,
)
async def submit_procedure_endpoint(
    procedure_id: UUID,
    current_user: User = Depends(require_permission("compliance_artefacts", "update")),
    db: AsyncSession = Depends(get_db),
):
    await _get_procedure_or_404(db, procedure_id)
    try:
        procedure = await submit_procedure(db, procedure_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    return await get_procedure_detail(db, procedure.id)


# 5. Advance step
@router.post(
    "/permit-procedures/{procedure_id}/steps/{step_id}/advance",
    response_model=StepRead,
)
async def advance_step_endpoint(
    procedure_id: UUID,
    step_id: UUID,
    current_user: User = Depends(require_permission("compliance_artefacts", "update")),
    db: AsyncSession = Depends(get_db),
):
    await _get_procedure_or_404(db, procedure_id)
    try:
        step = await advance_step(db, procedure_id, step_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    return step


# 6. Request complement
@router.post(
    "/permit-procedures/{procedure_id}/complement-request",
    response_model=AuthorityRequestRead,
    status_code=201,
)
async def request_complement_endpoint(
    procedure_id: UUID,
    payload: AuthorityRequestCreate,
    current_user: User = Depends(require_permission("compliance_artefacts", "update")),
    db: AsyncSession = Depends(get_db),
):
    await _get_procedure_or_404(db, procedure_id)
    data = payload.model_dump(exclude_unset=True)
    try:
        request = await request_complement(db, procedure_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    return request


# 7. Respond to authority request
@router.post(
    "/authority-requests/{request_id}/respond",
    response_model=AuthorityRequestRead,
)
async def respond_to_request_endpoint(
    request_id: UUID,
    payload: AuthorityRequestRespond,
    current_user: User = Depends(require_permission("compliance_artefacts", "update")),
    db: AsyncSession = Depends(get_db),
):
    try:
        request = await respond_to_request(db, request_id, payload.response_body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    return request


# 8. Approve procedure
@router.post(
    "/permit-procedures/{procedure_id}/approve",
    response_model=ProcedureRead,
)
async def approve_procedure_endpoint(
    procedure_id: UUID,
    reference_number: str | None = Query(None),
    current_user: User = Depends(require_permission("compliance_artefacts", "update")),
    db: AsyncSession = Depends(get_db),
):
    await _get_procedure_or_404(db, procedure_id)
    try:
        procedure = await approve_procedure(db, procedure_id, reference_number)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    return await get_procedure_detail(db, procedure.id)


# 9. Reject procedure
@router.post(
    "/permit-procedures/{procedure_id}/reject",
    response_model=ProcedureRead,
)
async def reject_procedure_endpoint(
    procedure_id: UUID,
    reason: str | None = Query(None),
    current_user: User = Depends(require_permission("compliance_artefacts", "update")),
    db: AsyncSession = Depends(get_db),
):
    await _get_procedure_or_404(db, procedure_id)
    try:
        procedure = await reject_procedure(db, procedure_id, reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    return await get_procedure_detail(db, procedure.id)


# 10. Withdraw procedure
@router.post(
    "/permit-procedures/{procedure_id}/withdraw",
    response_model=ProcedureRead,
)
async def withdraw_procedure_endpoint(
    procedure_id: UUID,
    current_user: User = Depends(require_permission("compliance_artefacts", "update")),
    db: AsyncSession = Depends(get_db),
):
    await _get_procedure_or_404(db, procedure_id)
    try:
        procedure = await withdraw_procedure(db, procedure_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    return await get_procedure_detail(db, procedure.id)


# 11. Get procedural blockers
@router.get(
    "/buildings/{building_id}/procedural-blockers",
    response_model=list[ProcedureBlockerRead],
)
async def get_blockers_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("compliance_artefacts", "list")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    return await get_procedural_blockers(db, building_id)
