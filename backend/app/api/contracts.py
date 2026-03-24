"""BatiConnect — Contract Ops API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.contract import Contract
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.contract import ContractCreate, ContractListRead, ContractRead, ContractUpdate
from app.schemas.contract_summary import ContractOpsSummary
from app.services.contract_service import (
    create_contract,
    enrich_contract,
    enrich_contracts,
    get_contract,
    get_contract_summary,
    list_contracts,
    update_contract,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


async def _get_contract_or_404(db: AsyncSession, contract_id: UUID) -> Contract:
    contract = await get_contract(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract


@router.get(
    "/buildings/{building_id}/contracts",
    response_model=PaginatedResponse[ContractListRead],
)
async def list_contracts_endpoint(
    building_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    contract_type: str | None = None,
    current_user: User = Depends(require_permission("contracts", "list")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    items, total = await list_contracts(
        db, building_id, page=page, size=size, status=status, contract_type=contract_type
    )
    pages = (total + size - 1) // size if total > 0 else 0
    enriched = await enrich_contracts(db, items)
    return {"items": enriched, "total": total, "page": page, "size": size, "pages": pages}


@router.post(
    "/buildings/{building_id}/contracts",
    response_model=ContractRead,
    status_code=201,
)
async def create_contract_endpoint(
    building_id: UUID,
    payload: ContractCreate,
    current_user: User = Depends(require_permission("contracts", "create")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    data = payload.model_dump(exclude_unset=True)
    data.pop("building_id", None)  # use path param
    contract = await create_contract(db, building_id, data, created_by=current_user.id)
    await db.commit()
    return await enrich_contract(db, contract)


@router.get(
    "/contracts/{contract_id}",
    response_model=ContractRead,
)
async def get_contract_endpoint(
    contract_id: UUID,
    current_user: User = Depends(require_permission("contracts", "read")),
    db: AsyncSession = Depends(get_db),
):
    contract = await _get_contract_or_404(db, contract_id)
    return await enrich_contract(db, contract)


@router.put(
    "/contracts/{contract_id}",
    response_model=ContractRead,
)
async def update_contract_endpoint(
    contract_id: UUID,
    payload: ContractUpdate,
    current_user: User = Depends(require_permission("contracts", "update")),
    db: AsyncSession = Depends(get_db),
):
    contract = await _get_contract_or_404(db, contract_id)
    data = payload.model_dump(exclude_unset=True)
    updated = await update_contract(db, contract, data)
    await db.commit()
    return await enrich_contract(db, updated)


@router.get(
    "/buildings/{building_id}/contract-summary",
    response_model=ContractOpsSummary,
)
async def contract_summary_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("contracts", "list")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    return await get_contract_summary(db, building_id)
