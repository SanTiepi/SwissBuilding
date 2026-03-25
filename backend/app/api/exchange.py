"""BatiConnect — Exchange contract and passport publication API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.exchange import (
    ExchangeContractRead,
    ImportReceiptCreate,
    ImportReceiptRead,
    PublicationCreate,
    PublicationRead,
)
from app.services.exchange_service import (
    get_active_contract,
    get_imports,
    get_publications,
    list_contracts,
    publish_passport,
    record_import,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


@router.get(
    "/exchange/contracts",
    response_model=list[ExchangeContractRead],
)
async def list_contracts_endpoint(
    audience: str | None = None,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    return await list_contracts(db, audience_filter=audience)


@router.get(
    "/exchange/contracts/{code}/active",
    response_model=ExchangeContractRead,
)
async def get_active_contract_endpoint(
    code: str,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    contract = await get_active_contract(db, code)
    if not contract:
        raise HTTPException(status_code=404, detail="No active contract found for this code")
    return contract


@router.post(
    "/buildings/{building_id}/passport-publications",
    response_model=PublicationRead,
    status_code=201,
)
async def publish_passport_endpoint(
    building_id: UUID,
    payload: PublicationCreate,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    data = payload.model_dump(exclude_unset=True)
    pub = await publish_passport(
        db,
        building_id,
        data,
        published_by_user_id=current_user.id,
        published_by_org_id=current_user.organization_id if hasattr(current_user, "organization_id") else None,
    )
    await db.commit()
    return pub


@router.get(
    "/buildings/{building_id}/passport-publications",
    response_model=list[PublicationRead],
)
async def list_publications_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    return await get_publications(db, building_id)


@router.post(
    "/passport-import-receipts",
    response_model=ImportReceiptRead,
    status_code=201,
)
async def record_import_endpoint(
    payload: ImportReceiptCreate,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    receipt = await record_import(db, data)
    await db.commit()
    return receipt


@router.get(
    "/buildings/{building_id}/import-receipts",
    response_model=list[ImportReceiptRead],
)
async def list_imports_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    return await get_imports(db, building_id)
