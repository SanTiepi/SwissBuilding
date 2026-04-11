"""BatiConnect — Commitments & Caveats API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.commitment import (
    AutoGenerateCaveatsResult,
    CaveatCreate,
    CaveatRead,
    CommitmentCaveatSummary,
    CommitmentCreate,
    CommitmentRead,
    ExpiringCommitmentRead,
)
from app.services.commitment_service import (
    auto_generate_caveats,
    check_expiring_commitments,
    create_caveat,
    create_commitment,
    get_building_caveats,
    get_building_commitments,
    get_caveats_for_pack,
    get_commitment_caveat_summary,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


# ---------------------------------------------------------------------------
# Commitments
# ---------------------------------------------------------------------------


@router.post(
    "/buildings/{building_id}/commitments",
    response_model=CommitmentRead,
    status_code=201,
)
async def create_commitment_endpoint(
    building_id: UUID,
    payload: CommitmentCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Creer un engagement (garantie, promesse, condition)."""
    await _get_building_or_404(db, building_id)
    data = payload.model_dump(exclude_unset=True)
    commitment = await create_commitment(db, building_id, data)
    await db.commit()
    return commitment


@router.get(
    "/buildings/{building_id}/commitments",
    response_model=list[CommitmentRead],
)
async def list_commitments_endpoint(
    building_id: UUID,
    status: str | None = Query(
        None, description="Filtrer par statut (active, expired, fulfilled, breached, withdrawn)"
    ),
    current_user: User = Depends(require_permission("buildings", "list")),
    db: AsyncSession = Depends(get_db),
):
    """Lister les engagements d'un batiment."""
    await _get_building_or_404(db, building_id)
    return await get_building_commitments(db, building_id, status=status)


@router.get(
    "/buildings/{building_id}/commitments/expiring",
    response_model=list[ExpiringCommitmentRead],
)
async def expiring_commitments_endpoint(
    building_id: UUID,
    days: int = Query(90, ge=1, le=730, description="Horizon en jours"),
    current_user: User = Depends(require_permission("buildings", "list")),
    db: AsyncSession = Depends(get_db),
):
    """Engagements expirant dans l'horizon donne."""
    await _get_building_or_404(db, building_id)
    items = await check_expiring_commitments(db, building_id, horizon_days=days)
    results = []
    for item in items:
        c = item["commitment"]
        results.append(
            ExpiringCommitmentRead(
                id=c.id,
                building_id=c.building_id,
                case_id=c.case_id,
                organization_id=c.organization_id,
                commitment_type=c.commitment_type,
                committed_by_type=c.committed_by_type,
                committed_by_name=c.committed_by_name,
                committed_by_id=c.committed_by_id,
                subject=c.subject,
                description=c.description,
                start_date=c.start_date,
                end_date=c.end_date,
                duration_months=c.duration_months,
                status=c.status,
                source_document_id=c.source_document_id,
                source_extraction_id=c.source_extraction_id,
                created_at=c.created_at,
                updated_at=c.updated_at,
                days_until_expiry=item["days_until_expiry"],
            )
        )
    return results


# ---------------------------------------------------------------------------
# Caveats
# ---------------------------------------------------------------------------


@router.post(
    "/buildings/{building_id}/caveats",
    response_model=CaveatRead,
    status_code=201,
)
async def create_caveat_endpoint(
    building_id: UUID,
    payload: CaveatCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Creer une reserve (limitation, exclusion, avertissement)."""
    await _get_building_or_404(db, building_id)
    data = payload.model_dump(exclude_unset=True)
    caveat = await create_caveat(db, building_id, data)
    await db.commit()
    return caveat


@router.get(
    "/buildings/{building_id}/caveats",
    response_model=list[CaveatRead],
)
async def list_caveats_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "list")),
    db: AsyncSession = Depends(get_db),
):
    """Lister les reserves actives d'un batiment."""
    await _get_building_or_404(db, building_id)
    return await get_building_caveats(db, building_id, active_only=True)


@router.get(
    "/buildings/{building_id}/caveats/for-pack/{pack_type}",
    response_model=list[CaveatRead],
)
async def caveats_for_pack_endpoint(
    building_id: UUID,
    pack_type: str,
    current_user: User = Depends(require_permission("buildings", "list")),
    db: AsyncSession = Depends(get_db),
):
    """Reserves applicables a un type de pack specifique."""
    await _get_building_or_404(db, building_id)
    return await get_caveats_for_pack(db, building_id, pack_type)


@router.post(
    "/buildings/{building_id}/caveats/auto-generate",
    response_model=AutoGenerateCaveatsResult,
)
async def auto_generate_caveats_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Auto-generer des reserves a partir des inconnus, contradictions et affirmations faibles."""
    await _get_building_or_404(db, building_id)
    caveats = await auto_generate_caveats(db, building_id)
    await db.commit()
    return AutoGenerateCaveatsResult(
        generated=len(caveats),
        caveats=[CaveatRead.model_validate(c) for c in caveats],
    )


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


@router.get(
    "/buildings/{building_id}/commitment-summary",
    response_model=CommitmentCaveatSummary,
)
async def commitment_summary_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "list")),
    db: AsyncSession = Depends(get_db),
):
    """Resume des engagements et reserves d'un batiment."""
    await _get_building_or_404(db, building_id)
    return await get_commitment_caveat_summary(db, building_id)
