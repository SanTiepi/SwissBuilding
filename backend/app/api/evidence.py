"""Evidence link management API routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.action_item import ActionItem
from app.models.building_risk_score import BuildingRiskScore
from app.models.evidence_link import EvidenceLink
from app.models.user import User
from app.schemas.evidence_link import EvidenceLinkCreate, EvidenceLinkRead

router = APIRouter()


@router.get(
    "/buildings/{building_id}/evidence",
    response_model=list[EvidenceLinkRead],
)
async def list_building_evidence(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("evidence", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List all evidence links for a building (via its risk scores and action items)."""
    # Gather risk score IDs for this building
    risk_result = await db.execute(select(BuildingRiskScore.id).where(BuildingRiskScore.building_id == building_id))
    risk_score_ids = [row[0] for row in risk_result.all()]

    # Gather action item IDs for this building
    action_result = await db.execute(select(ActionItem.id).where(ActionItem.building_id == building_id))
    action_item_ids = [row[0] for row in action_result.all()]

    # Build a query for evidence links targeting these
    target_ids_by_type: list[tuple[str, list]] = []
    if risk_score_ids:
        target_ids_by_type.append(("risk_score", risk_score_ids))
    if action_item_ids:
        target_ids_by_type.append(("action_item", action_item_ids))

    if not target_ids_by_type:
        return []

    conditions = []
    for target_type, target_ids in target_ids_by_type:
        conditions.append((EvidenceLink.target_type == target_type) & (EvidenceLink.target_id.in_(target_ids)))

    query = select(EvidenceLink).where(or_(*conditions)).order_by(EvidenceLink.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get(
    "/evidence/{evidence_id}",
    response_model=EvidenceLinkRead,
)
async def get_evidence(
    evidence_id: uuid.UUID,
    current_user: User = Depends(require_permission("evidence", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single evidence link by ID."""
    result = await db.execute(select(EvidenceLink).where(EvidenceLink.id == evidence_id))
    evidence = result.scalar_one_or_none()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence link not found")
    return evidence


@router.post(
    "/evidence",
    response_model=EvidenceLinkRead,
    status_code=201,
)
async def create_evidence(
    data: EvidenceLinkCreate,
    current_user: User = Depends(require_permission("evidence", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new evidence link."""
    evidence = EvidenceLink(
        source_type=data.source_type,
        source_id=data.source_id,
        target_type=data.target_type,
        target_id=data.target_id,
        relationship=data.relationship,
        confidence=data.confidence,
        legal_reference=data.legal_reference,
        explanation=data.explanation,
        created_by=current_user.id,
    )
    db.add(evidence)
    await db.commit()
    await db.refresh(evidence)
    return evidence


@router.get(
    "/risk-scores/{score_id}/evidence",
    response_model=list[EvidenceLinkRead],
)
async def list_risk_score_evidence(
    score_id: uuid.UUID,
    current_user: User = Depends(require_permission("evidence", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List evidence links for a specific risk score."""
    query = (
        select(EvidenceLink)
        .where(EvidenceLink.target_type == "risk_score")
        .where(EvidenceLink.target_id == score_id)
        .order_by(EvidenceLink.created_at.desc())
    )
    result = await db.execute(query)
    return list(result.scalars().all())
