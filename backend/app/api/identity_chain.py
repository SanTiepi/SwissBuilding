"""Identity chain API — canonical building identity resolution."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.identity_chain import IdentityChainResponse, RdppfResponse

router = APIRouter()


@router.get("/buildings/{building_id}/identity-chain", response_model=IdentityChainResponse)
async def get_identity_chain(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get or resolve the canonical identity chain for a building."""
    from app.services.identity_chain_service import get_identity_chain as _get_chain

    try:
        result = await _get_chain(db, building_id)
    except Exception as e:
        logging.getLogger(__name__).exception("Identity chain resolution failed for building %s", building_id)
        raise HTTPException(status_code=500, detail="Identity chain resolution failed") from e

    if result.get("error") == "building_not_found":
        raise HTTPException(status_code=404, detail="Building not found")

    await db.commit()
    return result


@router.post("/buildings/{building_id}/identity-chain/resolve", response_model=IdentityChainResponse)
async def resolve_identity_chain(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Force re-resolve the identity chain for a building."""
    from app.services.identity_chain_service import resolve_full_chain

    try:
        result = await resolve_full_chain(db, building_id)
    except Exception as e:
        logging.getLogger(__name__).exception("Identity chain resolution failed for building %s", building_id)
        raise HTTPException(status_code=500, detail="Identity chain resolution failed") from e

    if result.get("error") == "building_not_found":
        raise HTTPException(status_code=404, detail="Building not found")

    result["cached"] = False
    await db.commit()
    return result


@router.get("/buildings/{building_id}/rdppf", response_model=RdppfResponse)
async def get_rdppf(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get RDPPF restrictions for a building's parcel."""
    from app.services.identity_chain_service import get_identity_chain as _get_chain

    try:
        chain = await _get_chain(db, building_id)
    except Exception as e:
        logging.getLogger(__name__).exception("RDPPF fetch failed for building %s", building_id)
        raise HTTPException(status_code=500, detail="RDPPF fetch failed") from e

    if chain.get("error") == "building_not_found":
        raise HTTPException(status_code=404, detail="Building not found")

    await db.commit()

    rdppf = chain.get("rdppf", {})
    return {
        "restrictions": rdppf.get("restrictions", []),
        "themes": rdppf.get("themes", []),
        "source": rdppf.get("source"),
        "resolved_at": rdppf.get("resolved_at"),
    }
