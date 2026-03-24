"""Eco clause API routes for building pollutant contract clauses."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.services.eco_clause_template_service import generate_eco_clauses

router = APIRouter()


@router.get(
    "/buildings/{building_id}/eco-clauses",
    summary="Generate eco clause templates for a building",
)
async def get_eco_clauses(
    building_id: UUID,
    context: str = Query("renovation", pattern="^(renovation|demolition)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("buildings", "read")),
):
    """Return deterministic eco clause sections based on building pollutant data."""
    try:
        payload = await generate_eco_clauses(building_id, context, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None

    return {
        "building_id": str(payload.building_id),
        "context": payload.context,
        "generated_at": payload.generated_at.isoformat(),
        "total_clauses": payload.total_clauses,
        "detected_pollutants": payload.detected_pollutants,
        "sections": [
            {
                "section_id": s.section_id,
                "title": s.title,
                "clauses": [
                    {
                        "clause_id": c.clause_id,
                        "title": c.title,
                        "body": c.body,
                        "legal_references": c.legal_references,
                        "applicability": c.applicability,
                        "pollutants": c.pollutants,
                    }
                    for c in s.clauses
                ],
            }
            for s in payload.sections
        ],
    }
