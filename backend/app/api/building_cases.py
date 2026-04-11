"""BatiConnect — BuildingCase API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.building_case import (
    BuildingCaseAdvance,
    BuildingCaseCreate,
    BuildingCaseLinkIntervention,
    BuildingCaseLinkTender,
    BuildingCaseRead,
    BuildingCaseUpdate,
)
from app.services import building_case_service

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_case_or_404(db: AsyncSession, case_id: UUID):
    case = await building_case_service.get_case(db, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Building case not found")
    return case


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@router.post(
    "/buildings/{building_id}/cases",
    response_model=BuildingCaseRead,
    status_code=201,
)
async def create_case(
    building_id: UUID,
    payload: BuildingCaseCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new building case."""
    try:
        case = await building_case_service.create_case(
            db,
            building_id=building_id,
            organization_id=current_user.organization_id,
            created_by_id=current_user.id,
            case_type=payload.case_type,
            title=payload.title,
            description=payload.description,
            spatial_scope_ids=payload.spatial_scope_ids,
            pollutant_scope=payload.pollutant_scope,
            planned_start=payload.planned_start,
            planned_end=payload.planned_end,
            intervention_id=payload.intervention_id,
            tender_id=payload.tender_id,
            steps=payload.steps,
            canton=payload.canton,
            authority=payload.authority,
            priority=payload.priority,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return case


@router.get(
    "/buildings/{building_id}/cases",
    response_model=list[BuildingCaseRead],
)
async def list_cases_for_building(
    building_id: UUID,
    state: str | None = None,
    case_type: str | None = None,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List cases for a specific building."""
    return await building_case_service.list_cases(
        db,
        building_id=building_id,
        state=state,
        case_type=case_type,
    )


@router.get(
    "/cases",
    response_model=list[BuildingCaseRead],
)
async def list_org_cases(
    state: str | None = None,
    case_type: str | None = None,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List all cases for the current user's organization."""
    return await building_case_service.list_cases(
        db,
        organization_id=current_user.organization_id,
        state=state,
        case_type=case_type,
    )


@router.get(
    "/cases/{case_id}",
    response_model=BuildingCaseRead,
)
async def get_case(
    case_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single case by ID."""
    return await _get_case_or_404(db, case_id)


@router.put(
    "/cases/{case_id}",
    response_model=BuildingCaseRead,
)
async def update_case(
    case_id: UUID,
    payload: BuildingCaseUpdate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a building case."""
    case = await building_case_service.update_case(
        db,
        case_id,
        **payload.model_dump(exclude_unset=True),
    )
    if case is None:
        raise HTTPException(status_code=404, detail="Building case not found")
    return case


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------


@router.post(
    "/cases/{case_id}/advance",
    response_model=BuildingCaseRead,
)
async def advance_case(
    case_id: UUID,
    payload: BuildingCaseAdvance,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Advance the case to a new state (validated transitions)."""
    try:
        return await building_case_service.advance_case(db, case_id, payload.new_state)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------


@router.post(
    "/cases/{case_id}/steps/{step_name}/complete",
    response_model=BuildingCaseRead,
)
async def complete_step(
    case_id: UUID,
    step_name: str,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Mark a case step as completed."""
    try:
        return await building_case_service.complete_step(db, case_id, step_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


# ---------------------------------------------------------------------------
# Linking
# ---------------------------------------------------------------------------


@router.post(
    "/cases/{case_id}/link-intervention",
    response_model=BuildingCaseRead,
)
async def link_intervention(
    case_id: UUID,
    payload: BuildingCaseLinkIntervention,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Link an existing intervention to this case."""
    try:
        return await building_case_service.link_intervention(db, case_id, payload.intervention_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.post(
    "/cases/{case_id}/link-tender",
    response_model=BuildingCaseRead,
)
async def link_tender(
    case_id: UUID,
    payload: BuildingCaseLinkTender,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Link an existing tender request to this case."""
    try:
        return await building_case_service.link_tender(db, case_id, payload.tender_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


# ---------------------------------------------------------------------------
# Context & Timeline
# ---------------------------------------------------------------------------


@router.get("/cases/{case_id}/context")
async def get_case_context(
    case_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get full case context."""
    try:
        return await building_case_service.get_case_context(db, case_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@router.get("/cases/{case_id}/timeline")
async def get_case_timeline(
    case_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get chronological timeline for this case."""
    try:
        return await building_case_service.get_case_timeline(db, case_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
