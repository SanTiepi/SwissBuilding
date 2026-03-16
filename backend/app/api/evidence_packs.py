"""Evidence pack management API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.evidence_pack import EvidencePack
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.evidence_pack import (
    EvidencePackCreate,
    EvidencePackRead,
    EvidencePackUpdate,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


async def _get_pack_or_404(db: AsyncSession, building_id: UUID, pack_id: UUID) -> EvidencePack:
    result = await db.execute(
        select(EvidencePack).where(
            EvidencePack.id == pack_id,
            EvidencePack.building_id == building_id,
        )
    )
    pack = result.scalar_one_or_none()
    if not pack:
        raise HTTPException(status_code=404, detail="Evidence pack not found")
    return pack


@router.get(
    "/buildings/{building_id}/evidence-packs",
    response_model=PaginatedResponse[EvidencePackRead],
)
async def list_evidence_packs_endpoint(
    building_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    pack_type: str | None = None,
    status: str | None = None,
    current_user: User = Depends(require_permission("evidence_packs", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List evidence packs for a building."""
    await _get_building_or_404(db, building_id)

    query = select(EvidencePack).where(EvidencePack.building_id == building_id)
    count_query = select(func.count()).select_from(EvidencePack).where(EvidencePack.building_id == building_id)

    if pack_type:
        query = query.where(EvidencePack.pack_type == pack_type)
        count_query = count_query.where(EvidencePack.pack_type == pack_type)
    if status:
        query = query.where(EvidencePack.status == status)
        count_query = count_query.where(EvidencePack.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(EvidencePack.created_at.desc()).offset((page - 1) * size).limit(size)
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
    "/buildings/{building_id}/evidence-packs",
    response_model=EvidencePackRead,
    status_code=201,
)
async def create_evidence_pack_endpoint(
    building_id: UUID,
    data: EvidencePackCreate,
    current_user: User = Depends(require_permission("evidence_packs", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new evidence pack."""
    await _get_building_or_404(db, building_id)

    pack = EvidencePack(
        building_id=building_id,
        created_by=current_user.id,
        **data.model_dump(),
    )
    db.add(pack)
    await db.commit()
    await db.refresh(pack)
    return pack


@router.get(
    "/buildings/{building_id}/evidence-packs/{pack_id}",
    response_model=EvidencePackRead,
)
async def get_evidence_pack_endpoint(
    building_id: UUID,
    pack_id: UUID,
    current_user: User = Depends(require_permission("evidence_packs", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a single evidence pack."""
    await _get_building_or_404(db, building_id)
    return await _get_pack_or_404(db, building_id, pack_id)


@router.put(
    "/buildings/{building_id}/evidence-packs/{pack_id}",
    response_model=EvidencePackRead,
)
async def update_evidence_pack_endpoint(
    building_id: UUID,
    pack_id: UUID,
    data: EvidencePackUpdate,
    current_user: User = Depends(require_permission("evidence_packs", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update an evidence pack."""
    await _get_building_or_404(db, building_id)
    pack = await _get_pack_or_404(db, building_id, pack_id)

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(pack, key, value)

    await db.commit()
    await db.refresh(pack)
    return pack


@router.delete(
    "/buildings/{building_id}/evidence-packs/{pack_id}",
    status_code=204,
)
async def delete_evidence_pack_endpoint(
    building_id: UUID,
    pack_id: UUID,
    current_user: User = Depends(require_permission("evidence_packs", "delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete an evidence pack."""
    await _get_building_or_404(db, building_id)
    pack = await _get_pack_or_404(db, building_id, pack_id)
    await db.delete(pack)
    await db.commit()
