from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import require_permission
from app.models.jurisdiction import Jurisdiction
from app.models.regulatory_pack import RegulatoryPack
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.jurisdiction import (
    JurisdictionCreate,
    JurisdictionRead,
    JurisdictionReadWithPacks,
    JurisdictionUpdate,
    RegulatoryPackCreate,
    RegulatoryPackRead,
    RegulatoryPackUpdate,
)

router = APIRouter()


async def _get_jurisdiction_or_404(db: AsyncSession, jurisdiction_id: UUID) -> Jurisdiction:
    result = await db.execute(select(Jurisdiction).where(Jurisdiction.id == jurisdiction_id))
    jurisdiction = result.scalar_one_or_none()
    if not jurisdiction:
        raise HTTPException(status_code=404, detail="Jurisdiction not found")
    return jurisdiction


@router.get("/jurisdictions", response_model=PaginatedResponse[JurisdictionRead])
async def list_jurisdictions(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    parent_id: str | None = None,
    level: str | None = None,
    is_active: bool | None = None,
    current_user: User = Depends(require_permission("jurisdictions", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List all jurisdictions with optional filters."""
    query = select(Jurisdiction)
    count_query = select(func.count()).select_from(Jurisdiction)

    if parent_id is not None:
        pid = UUID(parent_id)
        query = query.where(Jurisdiction.parent_id == pid)
        count_query = count_query.where(Jurisdiction.parent_id == pid)

    if level is not None:
        query = query.where(Jurisdiction.level == level)
        count_query = count_query.where(Jurisdiction.level == level)

    if is_active is not None:
        query = query.where(Jurisdiction.is_active == is_active)
        count_query = count_query.where(Jurisdiction.is_active == is_active)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    pages = (total + size - 1) // size if total > 0 else 0

    query = query.order_by(Jurisdiction.code).offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {"items": items, "total": total, "page": page, "size": size, "pages": pages}


@router.get("/jurisdictions/{jurisdiction_id}", response_model=JurisdictionReadWithPacks)
async def get_jurisdiction(
    jurisdiction_id: UUID,
    current_user: User = Depends(require_permission("jurisdictions", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single jurisdiction with its regulatory packs."""
    result = await db.execute(
        select(Jurisdiction)
        .where(Jurisdiction.id == jurisdiction_id)
        .options(selectinload(Jurisdiction.regulatory_packs))
    )
    jurisdiction = result.scalar_one_or_none()
    if not jurisdiction:
        raise HTTPException(status_code=404, detail="Jurisdiction not found")
    return jurisdiction


@router.post("/jurisdictions", response_model=JurisdictionRead, status_code=201)
async def create_jurisdiction(
    data: JurisdictionCreate,
    current_user: User = Depends(require_permission("jurisdictions", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new jurisdiction (admin only)."""
    jurisdiction = Jurisdiction(**data.model_dump())
    db.add(jurisdiction)
    await db.commit()
    await db.refresh(jurisdiction)
    return jurisdiction


@router.put("/jurisdictions/{jurisdiction_id}", response_model=JurisdictionRead)
async def update_jurisdiction(
    jurisdiction_id: UUID,
    data: JurisdictionUpdate,
    current_user: User = Depends(require_permission("jurisdictions", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a jurisdiction (admin only)."""
    jurisdiction = await _get_jurisdiction_or_404(db, jurisdiction_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(jurisdiction, field, value)
    await db.commit()
    await db.refresh(jurisdiction)
    return jurisdiction


@router.delete("/jurisdictions/{jurisdiction_id}", status_code=204)
async def delete_jurisdiction(
    jurisdiction_id: UUID,
    current_user: User = Depends(require_permission("jurisdictions", "delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a jurisdiction (admin only). Refuses if it has children or packs."""
    jurisdiction = await _get_jurisdiction_or_404(db, jurisdiction_id)

    # Check for children
    children_result = await db.execute(
        select(func.count()).select_from(Jurisdiction).where(Jurisdiction.parent_id == jurisdiction_id)
    )
    if (children_result.scalar() or 0) > 0:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete jurisdiction with child jurisdictions. Remove children first.",
        )

    # Check for regulatory packs
    packs_result = await db.execute(
        select(func.count()).select_from(RegulatoryPack).where(RegulatoryPack.jurisdiction_id == jurisdiction_id)
    )
    if (packs_result.scalar() or 0) > 0:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete jurisdiction with regulatory packs. Remove packs first.",
        )

    await db.delete(jurisdiction)
    await db.commit()


# ---------------------------------------------------------------------------
# RegulatoryPack endpoints (nested under jurisdictions)
# ---------------------------------------------------------------------------


@router.get(
    "/jurisdictions/{jurisdiction_id}/regulatory-packs",
    response_model=list[RegulatoryPackRead],
)
async def list_regulatory_packs(
    jurisdiction_id: UUID,
    pollutant_type: str | None = None,
    is_active: bool | None = None,
    current_user: User = Depends(require_permission("jurisdictions", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List regulatory packs for a jurisdiction."""
    await _get_jurisdiction_or_404(db, jurisdiction_id)

    query = select(RegulatoryPack).where(RegulatoryPack.jurisdiction_id == jurisdiction_id)

    if pollutant_type is not None:
        query = query.where(RegulatoryPack.pollutant_type == pollutant_type)

    if is_active is not None:
        query = query.where(RegulatoryPack.is_active == is_active)

    query = query.order_by(RegulatoryPack.pollutant_type)
    result = await db.execute(query)
    return result.scalars().all()


@router.post(
    "/jurisdictions/{jurisdiction_id}/regulatory-packs",
    response_model=RegulatoryPackRead,
    status_code=201,
)
async def create_regulatory_pack(
    jurisdiction_id: UUID,
    data: RegulatoryPackCreate,
    current_user: User = Depends(require_permission("jurisdictions", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a regulatory pack for a jurisdiction (admin only)."""
    await _get_jurisdiction_or_404(db, jurisdiction_id)

    pack = RegulatoryPack(jurisdiction_id=jurisdiction_id, **data.model_dump())
    db.add(pack)
    await db.commit()
    await db.refresh(pack)
    return pack


@router.put(
    "/jurisdictions/{jurisdiction_id}/regulatory-packs/{pack_id}",
    response_model=RegulatoryPackRead,
)
async def update_regulatory_pack(
    jurisdiction_id: UUID,
    pack_id: UUID,
    data: RegulatoryPackUpdate,
    current_user: User = Depends(require_permission("jurisdictions", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a regulatory pack (admin only)."""
    await _get_jurisdiction_or_404(db, jurisdiction_id)

    result = await db.execute(
        select(RegulatoryPack).where(
            RegulatoryPack.id == pack_id,
            RegulatoryPack.jurisdiction_id == jurisdiction_id,
        )
    )
    pack = result.scalar_one_or_none()
    if not pack:
        raise HTTPException(status_code=404, detail="Regulatory pack not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(pack, field, value)
    await db.commit()
    await db.refresh(pack)
    return pack


@router.delete(
    "/jurisdictions/{jurisdiction_id}/regulatory-packs/{pack_id}",
    status_code=204,
)
async def delete_regulatory_pack(
    jurisdiction_id: UUID,
    pack_id: UUID,
    current_user: User = Depends(require_permission("jurisdictions", "delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a regulatory pack (admin only)."""
    await _get_jurisdiction_or_404(db, jurisdiction_id)

    result = await db.execute(
        select(RegulatoryPack).where(
            RegulatoryPack.id == pack_id,
            RegulatoryPack.jurisdiction_id == jurisdiction_id,
        )
    )
    pack = result.scalar_one_or_none()
    if not pack:
        raise HTTPException(status_code=404, detail="Regulatory pack not found")

    await db.delete(pack)
    await db.commit()
