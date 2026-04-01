"""Evidence Score API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.building import Building
from app.models.user import User
from app.schemas.evidence_score import EvidenceScoreRead
from app.services.evidence_score_service import compute_evidence_score

router = APIRouter()


@router.get(
    "/buildings/{building_id}/evidence-score",
    response_model=EvidenceScoreRead,
)
async def get_evidence_score(
    building_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compute and return the evidence score for a building."""
    result = await compute_evidence_score(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get(
    "/portfolio/evidence-scores",
    response_model=list[EvidenceScoreRead],
)
async def get_portfolio_evidence_scores(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compute evidence scores for all buildings in the user's organization."""
    # Load buildings for the user's org
    query = select(Building.id).where(Building.status == "active")
    if current_user.organization_id:
        query = query.where(Building.organization_id == current_user.organization_id)

    building_ids_result = await db.execute(query)
    building_ids = [row[0] for row in building_ids_result.all()]

    scores: list[dict] = []
    for bid in building_ids:
        score = await compute_evidence_score(db, bid)
        if score is not None:
            scores.append(score)

    return scores
