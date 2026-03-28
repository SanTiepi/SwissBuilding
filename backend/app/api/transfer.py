"""Building Memory Transfer Package API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.transfer_package import TransferPackageRequest, TransferPackageResponse
from app.services.transfer_package_service import generate_transfer_package

router = APIRouter()


@router.post(
    "/buildings/{building_id}/transfer-package",
    response_model=TransferPackageResponse,
)
async def create_transfer_package(
    building_id: UUID,
    body: TransferPackageRequest | None = None,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a building memory transfer package."""
    include_sections = body.include_sections if body else None
    redact_financials = body.redact_financials if body else False
    result = await generate_transfer_package(db, building_id, include_sections, redact_financials)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result
