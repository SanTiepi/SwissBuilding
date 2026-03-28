"""Unknowns Ledger API routes -- first-class unknown tracking."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.unknowns_ledger import (
    AcceptRiskRequest,
    CoverageMapRead,
    ResolveUnknownRequest,
    ScanResultRead,
    UnknownEntryRead,
    UnknownsImpactRead,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


@router.get(
    "/buildings/{building_id}/unknowns-ledger",
    response_model=list[UnknownEntryRead],
)
async def get_unknowns_ledger(
    building_id: UUID,
    status: str | None = Query("open"),
    severity: str | None = Query(None),
    case_id: UUID | None = Query(None),
    current_user: User = Depends(require_permission("unknowns", "list")),
    db: AsyncSession = Depends(get_db),
):
    """Get the unknowns ledger for a building."""
    await _get_building_or_404(db, building_id)

    from app.services.unknowns_ledger_service import get_ledger

    return await get_ledger(db, building_id, status=status, severity=severity, case_id=case_id)


@router.post(
    "/buildings/{building_id}/unknowns-ledger/scan",
    response_model=ScanResultRead,
)
async def scan_unknowns(
    building_id: UUID,
    current_user: User = Depends(require_permission("unknowns", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Run comprehensive scan for all unknowns on a building."""
    await _get_building_or_404(db, building_id)

    from app.services.unknowns_ledger_service import scan_building

    result = await scan_building(db, building_id)
    await db.commit()
    return result


@router.post(
    "/unknowns-ledger/{unknown_id}/resolve",
    response_model=UnknownEntryRead,
)
async def resolve_unknown_endpoint(
    unknown_id: UUID,
    data: ResolveUnknownRequest,
    current_user: User = Depends(require_permission("unknowns", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Resolve an unknown entry."""
    from app.services.unknowns_ledger_service import resolve_unknown

    try:
        entry = await resolve_unknown(
            db,
            unknown_id,
            resolved_by_id=current_user.id,
            method=data.method,
            note=data.note,
        )
        await db.commit()
        await db.refresh(entry)
        return entry
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.post(
    "/unknowns-ledger/{unknown_id}/accept-risk",
    response_model=UnknownEntryRead,
)
async def accept_risk_endpoint(
    unknown_id: UUID,
    data: AcceptRiskRequest,
    current_user: User = Depends(require_permission("unknowns", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Accept the risk of an unknown. Requires a note."""
    from app.services.unknowns_ledger_service import accept_risk

    try:
        entry = await accept_risk(
            db,
            unknown_id,
            accepted_by_id=current_user.id,
            note=data.note,
        )
        await db.commit()
        await db.refresh(entry)
        return entry
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.get(
    "/buildings/{building_id}/unknowns-ledger/coverage",
    response_model=CoverageMapRead,
)
async def get_coverage_map_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("unknowns", "list")),
    db: AsyncSession = Depends(get_db),
):
    """Get spatial coverage map for a building."""
    await _get_building_or_404(db, building_id)

    from app.services.unknowns_ledger_service import get_coverage_map

    return await get_coverage_map(db, building_id)


@router.get(
    "/buildings/{building_id}/unknowns-ledger/impact",
    response_model=UnknownsImpactRead,
)
async def get_unknowns_impact_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("unknowns", "list")),
    db: AsyncSession = Depends(get_db),
):
    """Get impact summary: blocked safe-to-x and packs."""
    await _get_building_or_404(db, building_id)

    from app.services.unknowns_ledger_service import get_unknowns_impact

    return await get_unknowns_impact(db, building_id)
