"""Document completeness assessment API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.document_completeness import (
    DocumentCompletenessResult,
    DocumentCurrencyResult,
    MissingDocumentDetail,
    PortfolioDocumentStatus,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


@router.get(
    "/buildings/{building_id}/document-completeness",
    response_model=DocumentCompletenessResult,
)
async def assess_document_completeness_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("documents", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Assess document completeness for a building (score 0-100)."""
    await _get_building_or_404(db, building_id)

    from app.services.document_completeness_service import assess_document_completeness

    return await assess_document_completeness(db, building_id)


@router.get(
    "/buildings/{building_id}/document-completeness/missing",
    response_model=list[MissingDocumentDetail],
)
async def get_missing_documents_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("documents", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get prioritized list of missing documents for a building."""
    await _get_building_or_404(db, building_id)

    from app.services.document_completeness_service import get_missing_documents

    return await get_missing_documents(db, building_id)


@router.get(
    "/buildings/{building_id}/document-completeness/currency",
    response_model=DocumentCurrencyResult,
)
async def validate_document_currency_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("documents", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Validate currency of existing documents for a building."""
    await _get_building_or_404(db, building_id)

    from app.services.document_completeness_service import validate_document_currency

    return await validate_document_currency(db, building_id)


@router.get(
    "/organizations/{org_id}/document-completeness",
    response_model=PortfolioDocumentStatus,
)
async def get_portfolio_document_status_endpoint(
    org_id: UUID,
    current_user: User = Depends(require_permission("documents", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get organization-level document completeness overview."""
    from app.services.document_completeness_service import get_portfolio_document_status

    return await get_portfolio_document_status(db, org_id)
