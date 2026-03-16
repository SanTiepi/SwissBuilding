"""
SwissBuildingOS - Document Service

Handles document upload/download via MinIO (S3-compatible) and DB records.
"""

import uuid as uuid_mod
from uuid import UUID

import boto3
from botocore.config import Config as BotoConfig
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.document import Document


def get_s3_client():
    """Create and return a boto3 S3 client configured for MinIO."""
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        config=BotoConfig(signature_version="s3v4"),
        region_name="us-east-1",
    )


async def upload_document(
    db: AsyncSession,
    building_id: UUID,
    file,
    document_type: str,
    description: str | None,
    uploaded_by: UUID,
) -> Document:
    """
    Upload a file to MinIO (S3) and create a Document record in the database.

    Args:
        db: Async database session.
        building_id: The building this document belongs to.
        file: An UploadFile object (FastAPI) with .filename, .content_type, .read().
        document_type: Category of document (e.g. 'diagnostic_report', 'plan', 'photo').
        description: Optional description text.
        uploaded_by: The user ID who uploaded the document.

    Returns:
        The created Document model instance.
    """
    file_id = uuid_mod.uuid4()
    filename = file.filename or "unnamed"
    s3_key = f"buildings/{building_id}/documents/{file_id}_{filename}"

    # Read the file content
    content = await file.read()
    content_type = file.content_type or "application/octet-stream"

    # File processing pipeline: virus scan + OCR
    from app.services.file_processing_service import process_uploaded_file

    try:
        content, processing_metadata = await process_uploaded_file(
            file_bytes=content,
            filename=filename,
            content_type=content_type,
        )
    except ValueError:
        # Virus detected — re-raise for the API layer to handle
        raise

    file_size = len(content)

    # Upload to MinIO/S3
    s3 = get_s3_client()

    # Ensure bucket exists
    try:
        s3.head_bucket(Bucket=settings.S3_BUCKET)
    except Exception:
        s3.create_bucket(Bucket=settings.S3_BUCKET)

    from io import BytesIO

    s3.upload_fileobj(
        BytesIO(content),
        settings.S3_BUCKET,
        s3_key,
        ExtraArgs={"ContentType": content_type},
    )

    # Create database record
    document = Document(
        building_id=building_id,
        file_path=s3_key,
        file_name=filename,
        file_size_bytes=file_size,
        mime_type=content_type,
        document_type=document_type,
        description=description,
        uploaded_by=uploaded_by,
        processing_metadata=processing_metadata,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    return document


async def list_documents(db: AsyncSession, building_id: UUID) -> list[Document]:
    """List all documents for a given building."""
    stmt = select(Document).where(Document.building_id == building_id).order_by(Document.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_download_url(db: AsyncSession, document_id: UUID) -> str | None:
    """
    Generate a presigned download URL for a document (1 hour expiry).
    Returns None if the document is not found.
    """
    stmt = select(Document).where(Document.id == document_id)
    result = await db.execute(stmt)
    document = result.scalar_one_or_none()

    if document is None:
        return None

    s3 = get_s3_client()
    url = s3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.S3_BUCKET,
            "Key": document.file_path,
        },
        ExpiresIn=3600,  # 1 hour
    )

    return url
