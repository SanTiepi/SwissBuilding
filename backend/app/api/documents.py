import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.limiter import limiter
from app.models.user import User
from app.schemas.document import DocumentRead
from app.services.audit_service import log_action
from app.services.document_service import get_download_url, list_documents, upload_document

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/buildings/{building_id}/documents", response_model=DocumentRead, status_code=201)
@limiter.limit("20/hour")
async def upload_document_endpoint(
    request: Request,
    building_id: UUID,
    file: UploadFile = File(...),
    document_type: str = Form(...),
    description: str | None = Form(None),
    current_user: User = Depends(require_permission("documents", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document for a building via multipart form."""
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    try:
        document = await upload_document(
            db,
            building_id=building_id,
            file=file,
            document_type=document_type,
            description=description,
            uploaded_by=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    await log_action(db, current_user.id, "upload", "document", document.id)
    from app.services.action_service import sync_building_system_actions

    await sync_building_system_actions(db, building_id)
    try:
        from app.services.search_service import index_document

        index_document(document)
    except Exception:
        logger.warning("Search index operation failed", exc_info=True)
    return document


@router.get("/buildings/{building_id}/documents", response_model=list[DocumentRead])
async def list_documents_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("documents", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List all documents for a building."""
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    documents = await list_documents(db, building_id)
    return documents


@router.get("/documents/{document_id}/download")
async def download_document_endpoint(
    document_id: UUID,
    current_user: User = Depends(require_permission("documents", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return a presigned download URL for a document."""
    url = await get_download_url(db, document_id)
    if not url:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"url": url}
