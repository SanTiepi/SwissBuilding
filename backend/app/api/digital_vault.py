"""Digital vault API endpoints — document trust and integrity tracking."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.digital_vault import (
    BuildingVaultSummary,
    DocumentTrustVerification,
    PortfolioVaultStatus,
    VaultIntegrityReport,
)
from app.services.digital_vault_service import (
    generate_integrity_report,
    get_building_vault_summary,
    get_portfolio_vault_status,
    verify_document_trust,
)

router = APIRouter()


@router.get(
    "/digital-vault/buildings/{building_id}/summary",
    response_model=BuildingVaultSummary,
)
async def get_vault_summary(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get digital vault summary for a building."""
    result = await get_building_vault_summary(building_id, db)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get(
    "/digital-vault/documents/{document_id}/verify",
    response_model=DocumentTrustVerification,
)
async def verify_document(
    document_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Verify trust and integrity of a document."""
    result = await verify_document_trust(document_id, db)
    if result is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return result


@router.get(
    "/digital-vault/buildings/{building_id}/integrity-report",
    response_model=VaultIntegrityReport,
)
async def get_integrity_report(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate integrity report for a building's vault."""
    result = await generate_integrity_report(building_id, db)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get(
    "/digital-vault/organizations/{org_id}/status",
    response_model=PortfolioVaultStatus,
)
async def get_org_vault_status(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio vault status for an organization."""
    result = await get_portfolio_vault_status(org_id, db)
    if result is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return result
