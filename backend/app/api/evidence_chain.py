"""Evidence Chain API — chain validation, provenance gaps, timeline, strength."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.evidence_chain import (
    ChainValidationResult,
    EvidenceStrengthResult,
    EvidenceTimelineResult,
    ProvenanceGapsResult,
)
from app.services.evidence_chain_service import (
    assess_evidence_strength,
    build_evidence_timeline,
    get_provenance_gaps,
    validate_evidence_chain,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/evidence-chain/validate",
    response_model=ChainValidationResult,
    tags=["Evidence Chain"],
)
async def api_validate_evidence_chain(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Validate evidence chain integrity for a building."""
    return await validate_evidence_chain(db, building_id)


@router.get(
    "/buildings/{building_id}/evidence-chain/provenance-gaps",
    response_model=ProvenanceGapsResult,
    tags=["Evidence Chain"],
)
async def api_get_provenance_gaps(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get provenance gaps for a building."""
    return await get_provenance_gaps(db, building_id)


@router.get(
    "/buildings/{building_id}/evidence-chain/timeline",
    response_model=EvidenceTimelineResult,
    tags=["Evidence Chain"],
)
async def api_build_evidence_timeline(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Build chronological evidence timeline for a building."""
    return await build_evidence_timeline(db, building_id)


@router.get(
    "/buildings/{building_id}/evidence-chain/strength",
    response_model=EvidenceStrengthResult,
    tags=["Evidence Chain"],
)
async def api_assess_evidence_strength(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Assess per-pollutant evidence strength for a building."""
    return await assess_evidence_strength(db, building_id)
