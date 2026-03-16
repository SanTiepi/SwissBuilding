from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.multi_org_dashboard import MultiOrgComparison, MultiOrgDashboard
from app.services.multi_org_dashboard_service import (
    compare_organizations,
    get_multi_org_dashboard,
)

router = APIRouter()


@router.get("/dashboard", response_model=MultiOrgDashboard)
async def multi_org_dashboard(
    org_ids: str | None = Query(None, description="Comma-separated organization UUIDs"),
    current_user: User = Depends(require_permission("organizations", "list")),
    db: AsyncSession = Depends(get_db),
):
    """Return aggregated metrics across multiple organizations."""
    parsed_ids: list[UUID] | None = None
    if org_ids:
        try:
            parsed_ids = [UUID(oid.strip()) for oid in org_ids.split(",") if oid.strip()]
        except ValueError as err:
            raise HTTPException(status_code=422, detail="Invalid UUID in org_ids parameter") from err

    return await get_multi_org_dashboard(db, org_ids=parsed_ids)


@router.get("/compare", response_model=MultiOrgComparison)
async def multi_org_compare(
    org_ids: str = Query(..., description="Comma-separated organization UUIDs (minimum 2)"),
    metrics: str | None = Query(None, description="Comma-separated metric names"),
    current_user: User = Depends(require_permission("organizations", "list")),
    db: AsyncSession = Depends(get_db),
):
    """Compare metrics across selected organizations (minimum 2)."""
    try:
        parsed_ids = [UUID(oid.strip()) for oid in org_ids.split(",") if oid.strip()]
    except ValueError as err:
        raise HTTPException(status_code=422, detail="Invalid UUID in org_ids parameter") from err

    if len(parsed_ids) < 2:
        raise HTTPException(status_code=422, detail="At least 2 organization IDs are required")

    parsed_metrics: list[str] | None = None
    if metrics:
        parsed_metrics = [m.strip() for m in metrics.split(",") if m.strip()]

    return await compare_organizations(db, org_ids=parsed_ids, metrics=parsed_metrics)
