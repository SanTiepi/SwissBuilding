"""Finance Surfaces — Audience Packs API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.audience_pack import (
    AudiencePackCreate,
    AudiencePackListRead,
    AudiencePackRead,
    CaveatEvaluation,
    PackComparisonView,
    RedactionProfileRead,
)
from app.services.audience_pack_service import (
    compare_packs,
    evaluate_caveats,
    generate_pack,
    get_pack,
    get_redaction_profile_by_code,
    list_packs,
    list_redaction_profiles,
    share_pack,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


@router.post(
    "/buildings/{building_id}/audience-packs",
    response_model=AudiencePackRead,
    status_code=201,
)
async def create_audience_pack(
    building_id: UUID,
    payload: AudiencePackCreate,
    current_user: User = Depends(require_permission("evidence_packs", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a new audience pack for a building."""
    await _get_building_or_404(db, building_id)
    if payload.pack_type not in ("insurer", "fiduciary", "transaction", "lender"):
        raise HTTPException(status_code=400, detail="Invalid pack_type")
    try:
        pack = await generate_pack(db, building_id, payload.pack_type, user_id=current_user.id)
        caveats = await evaluate_caveats(db, building_id, payload.pack_type)
        await db.commit()
        result = _pack_to_dict(pack)
        result["caveats"] = caveats
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.get(
    "/buildings/{building_id}/audience-packs",
    response_model=list[AudiencePackListRead],
)
async def list_audience_packs(
    building_id: UUID,
    type: str | None = Query(None, alias="type"),
    current_user: User = Depends(require_permission("evidence_packs", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List audience packs for a building, optionally filtered by type."""
    await _get_building_or_404(db, building_id)
    packs = await list_packs(db, building_id, pack_type=type)
    return packs


@router.get(
    "/audience-packs/{pack_id}",
    response_model=AudiencePackRead,
)
async def get_audience_pack(
    pack_id: UUID,
    current_user: User = Depends(require_permission("evidence_packs", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single audience pack by ID."""
    pack = await get_pack(db, pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail="Audience pack not found")
    caveats = await evaluate_caveats(db, pack.building_id, pack.pack_type)
    result = _pack_to_dict(pack)
    result["caveats"] = caveats
    return result


@router.post(
    "/audience-packs/{pack_id}/share",
    response_model=AudiencePackRead,
)
async def share_audience_pack(
    pack_id: UUID,
    current_user: User = Depends(require_permission("evidence_packs", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Mark an audience pack as shared and create a proof delivery."""
    try:
        pack = await share_pack(db, pack_id, user_id=current_user.id)
        await db.commit()
        caveats = await evaluate_caveats(db, pack.building_id, pack.pack_type)
        result = _pack_to_dict(pack)
        result["caveats"] = caveats
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.get(
    "/audience-packs/compare",
    response_model=PackComparisonView,
)
async def compare_audience_packs(
    pack1: UUID = Query(...),
    pack2: UUID = Query(...),
    current_user: User = Depends(require_permission("evidence_packs", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Compare two audience packs side by side."""
    try:
        result = await compare_packs(db, pack1, pack2)
        # Convert packs to dicts for response
        result["pack_1"] = _pack_to_dict(result["pack_1"])
        result["pack_2"] = _pack_to_dict(result["pack_2"])
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.get(
    "/redaction-profiles",
    response_model=list[RedactionProfileRead],
)
async def list_redaction_profiles_endpoint(
    current_user: User = Depends(require_permission("evidence_packs", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List all active redaction profiles."""
    return await list_redaction_profiles(db)


@router.get(
    "/redaction-profiles/{code}",
    response_model=RedactionProfileRead,
)
async def get_redaction_profile(
    code: str,
    current_user: User = Depends(require_permission("evidence_packs", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a redaction profile by its code."""
    profile = await get_redaction_profile_by_code(db, code)
    if not profile:
        raise HTTPException(status_code=404, detail="Redaction profile not found")
    return profile


@router.get(
    "/buildings/{building_id}/caveats",
    response_model=list[CaveatEvaluation],
)
async def get_building_caveats(
    building_id: UUID,
    audience: str = Query(...),
    current_user: User = Depends(require_permission("evidence_packs", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Evaluate caveats for a building and audience type."""
    await _get_building_or_404(db, building_id)
    return await evaluate_caveats(db, building_id, audience)


def _pack_to_dict(pack) -> dict:
    """Convert AudiencePack ORM instance to dict for response serialization."""
    return {c.key: getattr(pack, c.key) for c in pack.__table__.columns}
