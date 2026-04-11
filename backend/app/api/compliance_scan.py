"""Programme N — Auto Compliance Scan API endpoint."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.compliance_scan_output import ComplianceScanResult
from app.services.compliance_scan_service import run_compliance_scan

router = APIRouter()


@router.get(
    "/buildings/{building_id}/compliance-scan",
    response_model=ComplianceScanResult,
)
async def compliance_scan_endpoint(
    building_id: uuid.UUID,
    force: bool = Query(False, description="Force refresh (bypass 24h cache)"),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Execute full compliance scan (341+ checks) for a building.

    Cached 24h. Pass ?force=true to refresh.
    """
    try:
        return await run_compliance_scan(db, building_id, force=force)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
