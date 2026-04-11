"""Document checklist API routes (GED C).

GET /buildings/{building_id}/document-checklist — evaluate missing documents checklist
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.document_checklist import DocumentChecklistRead

router = APIRouter()


@router.get(
    "/buildings/{building_id}/document-checklist",
    response_model=DocumentChecklistRead,
    tags=["Document Checklist"],
)
async def get_document_checklist(
    building_id: UUID,
    current_user: User = Depends(require_permission("documents", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Evaluate the document checklist for a building.

    Returns required documents based on building context (construction year,
    type, etc.) and compares with present documents.
    """
    from app.services.document_checklist_service import evaluate_document_checklist

    try:
        result = await evaluate_document_checklist(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None

    return result
