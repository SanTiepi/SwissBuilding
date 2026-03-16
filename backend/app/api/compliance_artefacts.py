from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.compliance_artefact import ComplianceArtefact
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.compliance_artefact import (
    ComplianceArtefactCreate,
    ComplianceArtefactRead,
    ComplianceArtefactUpdate,
)
from app.services.compliance_artefact_service import (
    acknowledge_artefact,
    check_required_artefacts,
    create_artefact,
    get_building_compliance_summary,
    submit_artefact,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


async def _get_artefact_or_404(db: AsyncSession, building_id: UUID, artefact_id: UUID) -> ComplianceArtefact:
    result = await db.execute(
        select(ComplianceArtefact).where(
            ComplianceArtefact.id == artefact_id,
            ComplianceArtefact.building_id == building_id,
        )
    )
    artefact = result.scalar_one_or_none()
    if not artefact:
        raise HTTPException(status_code=404, detail="Compliance artefact not found")
    return artefact


@router.get(
    "/buildings/{building_id}/compliance-artefacts",
    response_model=PaginatedResponse[ComplianceArtefactRead],
)
async def list_artefacts_endpoint(
    building_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    artefact_type: str | None = None,
    status: str | None = None,
    current_user: User = Depends(require_permission("compliance_artefacts", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List compliance artefacts for a building with optional filters."""
    await _get_building_or_404(db, building_id)

    query = select(ComplianceArtefact).where(ComplianceArtefact.building_id == building_id)
    count_query = (
        select(func.count()).select_from(ComplianceArtefact).where(ComplianceArtefact.building_id == building_id)
    )

    if artefact_type:
        query = query.where(ComplianceArtefact.artefact_type == artefact_type)
        count_query = count_query.where(ComplianceArtefact.artefact_type == artefact_type)
    if status:
        query = query.where(ComplianceArtefact.status == status)
        count_query = count_query.where(ComplianceArtefact.status == status)

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
    "/buildings/{building_id}/compliance-artefacts",
    response_model=ComplianceArtefactRead,
    status_code=201,
)
async def create_artefact_endpoint(
    building_id: UUID,
    data: ComplianceArtefactCreate,
    current_user: User = Depends(require_permission("compliance_artefacts", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new compliance artefact for a building."""
    await _get_building_or_404(db, building_id)
    artefact = await create_artefact(db, building_id, data, current_user.id)
    await db.commit()
    await db.refresh(artefact)
    return artefact


@router.get(
    "/buildings/{building_id}/compliance-artefacts/{artefact_id}",
    response_model=ComplianceArtefactRead,
)
async def get_artefact_endpoint(
    building_id: UUID,
    artefact_id: UUID,
    current_user: User = Depends(require_permission("compliance_artefacts", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a single compliance artefact."""
    await _get_building_or_404(db, building_id)
    return await _get_artefact_or_404(db, building_id, artefact_id)


@router.put(
    "/buildings/{building_id}/compliance-artefacts/{artefact_id}",
    response_model=ComplianceArtefactRead,
)
async def update_artefact_endpoint(
    building_id: UUID,
    artefact_id: UUID,
    data: ComplianceArtefactUpdate,
    current_user: User = Depends(require_permission("compliance_artefacts", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing compliance artefact."""
    await _get_building_or_404(db, building_id)
    artefact = await _get_artefact_or_404(db, building_id, artefact_id)

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(artefact, key, value)

    await db.commit()
    await db.refresh(artefact)
    return artefact


@router.delete(
    "/buildings/{building_id}/compliance-artefacts/{artefact_id}",
    status_code=204,
)
async def delete_artefact_endpoint(
    building_id: UUID,
    artefact_id: UUID,
    current_user: User = Depends(require_permission("compliance_artefacts", "delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a compliance artefact."""
    await _get_building_or_404(db, building_id)
    artefact = await _get_artefact_or_404(db, building_id, artefact_id)
    await db.delete(artefact)
    await db.commit()


@router.post(
    "/buildings/{building_id}/compliance-artefacts/{artefact_id}/submit",
    response_model=ComplianceArtefactRead,
)
async def submit_artefact_endpoint(
    building_id: UUID,
    artefact_id: UUID,
    current_user: User = Depends(require_permission("compliance_artefacts", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Submit a compliance artefact (draft -> submitted)."""
    await _get_building_or_404(db, building_id)
    await _get_artefact_or_404(db, building_id, artefact_id)
    try:
        artefact = await submit_artefact(db, artefact_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(artefact)
    return artefact


@router.post(
    "/buildings/{building_id}/compliance-artefacts/{artefact_id}/acknowledge",
    response_model=ComplianceArtefactRead,
)
async def acknowledge_artefact_endpoint(
    building_id: UUID,
    artefact_id: UUID,
    reference_number: str | None = None,
    current_user: User = Depends(require_permission("compliance_artefacts", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Acknowledge a compliance artefact (submitted -> acknowledged)."""
    await _get_building_or_404(db, building_id)
    await _get_artefact_or_404(db, building_id, artefact_id)
    try:
        artefact = await acknowledge_artefact(db, artefact_id, reference_number)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(artefact)
    return artefact


@router.get(
    "/buildings/{building_id}/compliance-summary",
    response_model=dict,
)
async def compliance_summary_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("compliance_artefacts", "list")),
    db: AsyncSession = Depends(get_db),
):
    """Get compliance summary for a building."""
    await _get_building_or_404(db, building_id)
    return await get_building_compliance_summary(db, building_id)


@router.get(
    "/buildings/{building_id}/compliance-required",
    response_model=list[dict],
)
async def required_artefacts_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("compliance_artefacts", "list")),
    db: AsyncSession = Depends(get_db),
):
    """Check which compliance artefacts are required but missing."""
    await _get_building_or_404(db, building_id)
    return await check_required_artefacts(db, building_id)
