"""BatiConnect — Procedure OS API routes.

Endpoints for procedure templates and instances (applicability, lifecycle,
blockers).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.procedure import (
    ApplicableProcedureRead,
    ProcedureAdvanceStep,
    ProcedureBlockerRead,
    ProcedureComplement,
    ProcedureInstanceCreate,
    ProcedureInstanceRead,
    ProcedureResolve,
    ProcedureSubmit,
    ProcedureTemplateRead,
)
from app.services import procedure_service

router = APIRouter()


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


@router.get(
    "/procedure-templates",
    response_model=list[ProcedureTemplateRead],
)
async def list_templates(
    procedure_type: str | None = Query(None),
    scope: str | None = Query(None),
    canton: str | None = Query(None),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List all active procedure templates, with optional filters."""
    return await procedure_service.list_templates(
        db,
        procedure_type=procedure_type,
        scope=scope,
        canton=canton,
    )


@router.get(
    "/procedure-templates/{template_id}",
    response_model=ProcedureTemplateRead,
)
async def get_template(
    template_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single procedure template by ID."""
    tpl = await procedure_service.get_template(db, template_id)
    if tpl is None:
        raise HTTPException(status_code=404, detail="Procedure template not found")
    return tpl


# ---------------------------------------------------------------------------
# Applicable procedures
# ---------------------------------------------------------------------------


@router.get(
    "/buildings/{building_id}/procedures/applicable",
    response_model=list[ApplicableProcedureRead],
)
async def get_applicable_procedures(
    building_id: UUID,
    case_id: UUID | None = Query(None),
    work_type: str | None = Query(None),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Determine which procedures apply based on building, case, and work type."""
    results = await procedure_service.get_applicable_procedures(
        db,
        building_id,
        case_id=case_id,
        work_type=work_type,
    )
    return results


# ---------------------------------------------------------------------------
# Instances — CRUD + lifecycle
# ---------------------------------------------------------------------------


@router.post(
    "/buildings/{building_id}/procedures",
    response_model=ProcedureInstanceRead,
    status_code=201,
)
async def start_procedure(
    building_id: UUID,
    payload: ProcedureInstanceCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Start a procedure instance from a template."""
    try:
        instance = await procedure_service.start_procedure(
            db,
            template_id=payload.template_id,
            building_id=building_id,
            created_by_id=current_user.id,
            organization_id=current_user.organization_id,
            case_id=payload.case_id,
        )
        await db.commit()
        return instance
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.get(
    "/buildings/{building_id}/procedures",
    response_model=list[ProcedureInstanceRead],
)
async def list_instances(
    building_id: UUID,
    case_id: UUID | None = Query(None),
    status: str | None = Query(None),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List procedure instances for a building."""
    return await procedure_service.list_instances(db, building_id, case_id=case_id, status=status)


@router.get(
    "/procedures/{instance_id}",
    response_model=ProcedureInstanceRead,
)
async def get_instance(
    instance_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single procedure instance by ID."""
    instance = await procedure_service.get_instance(db, instance_id)
    if instance is None:
        raise HTTPException(status_code=404, detail="Procedure instance not found")
    return instance


@router.post(
    "/procedures/{instance_id}/advance",
    response_model=ProcedureInstanceRead,
)
async def advance_step(
    instance_id: UUID,
    payload: ProcedureAdvanceStep,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Mark a procedure step as completed."""
    try:
        instance = await procedure_service.advance_step(
            db,
            instance_id=instance_id,
            step_name=payload.step_name,
            completed_by_id=current_user.id,
        )
        await db.commit()
        return instance
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.post(
    "/procedures/{instance_id}/submit",
    response_model=ProcedureInstanceRead,
)
async def submit_procedure(
    instance_id: UUID,
    payload: ProcedureSubmit,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Submit the procedure to the authority."""
    try:
        instance = await procedure_service.submit_procedure(
            db,
            instance_id=instance_id,
            submission_reference=payload.submission_reference,
        )
        await db.commit()
        return instance
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.post(
    "/procedures/{instance_id}/complement",
    response_model=ProcedureInstanceRead,
)
async def handle_complement(
    instance_id: UUID,
    payload: ProcedureComplement,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Handle a complement request from authority."""
    try:
        instance = await procedure_service.handle_complement(
            db,
            instance_id=instance_id,
            complement_details=payload.complement_details,
        )
        await db.commit()
        return instance
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.post(
    "/procedures/{instance_id}/resolve",
    response_model=ProcedureInstanceRead,
)
async def resolve_procedure(
    instance_id: UUID,
    payload: ProcedureResolve,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Record authority decision (approved/rejected)."""
    try:
        instance = await procedure_service.resolve_procedure(
            db,
            instance_id=instance_id,
            resolution=payload.resolution,
            resolved_by_id=current_user.id,
        )
        await db.commit()
        return instance
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.get(
    "/procedures/{instance_id}/blockers",
    response_model=list[ProcedureBlockerRead],
)
async def get_blockers(
    instance_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get current blockers for the procedure."""
    blockers = await procedure_service.get_procedure_blockers(db, instance_id)
    return blockers
