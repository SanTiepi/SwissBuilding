"""BatiConnect — Partner Exchange Contracts API.

Governed partner interaction contracts: CRUD, submission validation,
exchange history. Every partner interaction is bounded by a contract.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.partner_exchange_contract import (
    PartnerAccessValidation,
    PartnerExchangeContractCreate,
    PartnerExchangeContractRead,
    PartnerExchangeContractUpdate,
    PartnerExchangeEventRead,
    PartnerSubmissionValidation,
)
from app.services.partner_gateway_service import (
    create_contract,
    get_contract,
    get_exchange_history,
    list_contracts,
    update_contract,
    validate_partner_access,
    validate_submission,
)

router = APIRouter()


@router.get(
    "/partner-contracts",
    response_model=list[PartnerExchangeContractRead],
)
async def list_partner_contracts(
    our_org_id: UUID | None = None,
    partner_org_id: UUID | None = None,
    status: str | None = Query(default=None),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List partner exchange contracts with optional filters."""
    contracts = await list_contracts(
        db,
        our_org_id=our_org_id,
        partner_org_id=partner_org_id,
        status_filter=status,
    )
    return contracts


@router.post(
    "/partner-contracts",
    response_model=PartnerExchangeContractRead,
    status_code=201,
)
async def create_partner_contract(
    payload: PartnerExchangeContractCreate,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new partner exchange contract."""
    data = payload.model_dump(exclude_unset=True)
    contract = await create_contract(db, data)
    await db.commit()
    return contract


@router.get(
    "/partner-contracts/{contract_id}",
    response_model=PartnerExchangeContractRead,
)
async def get_partner_contract(
    contract_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a partner exchange contract by ID."""
    contract = await get_contract(db, contract_id)
    if contract is None:
        raise HTTPException(status_code=404, detail="Partner exchange contract not found")
    return contract


@router.put(
    "/partner-contracts/{contract_id}",
    response_model=PartnerExchangeContractRead,
)
async def update_partner_contract(
    contract_id: UUID,
    payload: PartnerExchangeContractUpdate,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Update a partner exchange contract."""
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    contract = await update_contract(db, contract_id, updates)
    if contract is None:
        raise HTTPException(status_code=404, detail="Partner exchange contract not found")
    await db.commit()
    return contract


@router.post(
    "/partner-contracts/{contract_id}/validate-submission",
    response_model=PartnerSubmissionValidation,
)
async def validate_partner_submission(
    contract_id: UUID,
    submission_type: str = Query(...),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Validate a partner submission against their contract and conformance profile."""
    contract = await get_contract(db, contract_id)
    if contract is None:
        raise HTTPException(status_code=404, detail="Partner exchange contract not found")

    result = await validate_submission(
        db,
        partner_org_id=contract.partner_org_id,
        submission_type=submission_type,
        submission_data={"contract_id": str(contract_id)},
    )
    await db.commit()
    return PartnerSubmissionValidation(**result)


@router.get(
    "/partner-contracts/{contract_id}/exchange-history",
    response_model=list[PartnerExchangeEventRead],
)
async def get_contract_exchange_history(
    contract_id: UUID,
    limit: int = Query(default=50, le=200),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get exchange event history for a partner contract."""
    contract = await get_contract(db, contract_id)
    if contract is None:
        raise HTTPException(status_code=404, detail="Partner exchange contract not found")
    events = await get_exchange_history(db, contract_id, limit=limit)
    return events


@router.post(
    "/partner-contracts/validate-access",
    response_model=PartnerAccessValidation,
)
async def validate_access_endpoint(
    partner_org_id: UUID = Query(...),
    operation: str = Query(...),
    endpoint: str | None = Query(default=None),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Check if a partner is allowed to perform an operation."""
    result = await validate_partner_access(db, partner_org_id, operation, endpoint)
    await db.commit()
    return PartnerAccessValidation(**result)
