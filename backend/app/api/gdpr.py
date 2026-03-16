"""GDPR compliance endpoints — data access, export, and deletion rights."""

import uuid as uuid_mod
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.audit_log import AuditLog
from app.models.document import Document
from app.models.notification import Notification
from app.models.user import User
from app.services.audit_service import log_action

router = APIRouter()


def _serialize_user(user: User) -> dict:
    """Serialize user fields to a JSON-safe dict."""
    return {
        "id": str(user.id),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role,
        "organization_id": str(user.organization_id) if user.organization_id else None,
        "language": user.language,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }


def _serialize_audit_log(log: AuditLog) -> dict:
    """Serialize an audit log entry."""
    return {
        "id": str(log.id),
        "action": log.action,
        "entity_type": log.entity_type,
        "entity_id": str(log.entity_id) if log.entity_id else None,
        "details": log.details,
        "ip_address": log.ip_address,
        "timestamp": log.timestamp.isoformat() if log.timestamp else None,
    }


async def _collect_user_data(user: User, db: AsyncSession) -> dict:
    """Collect all data associated with a user for GDPR access/portability."""
    data: dict = {"user": _serialize_user(user)}

    # Audit logs created by this user
    result = await db.execute(
        select(AuditLog).where(AuditLog.user_id == user.id).order_by(AuditLog.timestamp.desc()).limit(1000)
    )
    data["audit_logs"] = [_serialize_audit_log(log) for log in result.scalars().all()]

    # Documents uploaded by this user
    result = await db.execute(select(Document).where(Document.uploaded_by == user.id))
    data["documents"] = [
        {
            "id": str(doc.id),
            "file_name": doc.file_name,
            "document_type": doc.document_type,
            "mime_type": doc.mime_type,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        }
        for doc in result.scalars().all()
    ]

    # Notifications for this user
    result = await db.execute(select(Notification).where(Notification.user_id == user.id))
    data["notifications"] = [
        {
            "id": str(n.id),
            "title": n.title,
            "body": n.body,
            "status": n.status,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in result.scalars().all()
    ]

    # Diagnostics performed by this user
    from app.models.diagnostic import Diagnostic

    result = await db.execute(select(Diagnostic).where(Diagnostic.diagnostician_id == user.id))
    data["diagnostics"] = [
        {
            "id": str(d.id),
            "building_id": str(d.building_id),
            "status": d.status,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in result.scalars().all()
    ]

    return data


@router.get("/gdpr/my-data")
async def get_my_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """GDPR Art. 15 — Right of access. Returns all data associated with the current user."""
    data = await _collect_user_data(current_user, db)

    await log_action(
        db=db,
        user_id=current_user.id,
        action="gdpr_data_access",
        entity_type="user",
        entity_id=current_user.id,
        details={"article": "Art. 15 — Right of access"},
    )

    return data


@router.get("/gdpr/my-data/export")
async def export_my_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """GDPR Art. 20 — Right to data portability. Export all user data as downloadable JSON."""
    data = await _collect_user_data(current_user, db)
    data["export_metadata"] = {
        "exported_at": datetime.now(UTC).isoformat(),
        "format": "JSON",
        "gdpr_article": "Art. 20 — Right to data portability",
    }

    await log_action(
        db=db,
        user_id=current_user.id,
        action="gdpr_data_export",
        entity_type="user",
        entity_id=current_user.id,
        details={"article": "Art. 20 — Right to data portability"},
    )

    return JSONResponse(
        content=data,
        headers={
            "Content-Disposition": f'attachment; filename="gdpr_export_{current_user.id}.json"',
        },
    )


@router.delete("/gdpr/my-data")
async def delete_my_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """GDPR Art. 17 — Right to erasure (right to be forgotten).

    Anonymizes user data. Does NOT delete buildings/diagnostics (they belong to the org).
    Anonymizes: name, email, personal identifiers. Keeps: audit trail (legal requirement).
    """
    if current_user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Les comptes administrateur ne peuvent pas etre supprimes via cette methode. Contactez le support.",
        )

    # Generate anonymized placeholder
    anon_id = uuid_mod.uuid4().hex[:8]
    original_email = current_user.email

    # Anonymize personal fields
    current_user.email = f"deleted_{anon_id}@anonymized.local"
    current_user.first_name = "Utilisateur"
    current_user.last_name = "Supprime"
    current_user.is_active = False
    current_user.password_hash = "ACCOUNT_DELETED"

    # Log the action BEFORE committing (audit trail is a legal requirement)
    await log_action(
        db=db,
        user_id=current_user.id,
        action="gdpr_data_erasure",
        entity_type="user",
        entity_id=current_user.id,
        details={
            "article": "Art. 17 — Right to erasure",
            "original_email_hash": str(hash(original_email)),
            "anonymized": True,
        },
    )

    await db.commit()

    return {
        "status": "anonymized",
        "message": "Vos donnees personnelles ont ete anonymisees conformement au RGPD Art. 17.",
        "details": {
            "email": "anonymized",
            "name": "anonymized",
            "account": "deactivated",
            "audit_trail": "preserved (legal requirement)",
            "buildings_diagnostics": "preserved (belong to organization)",
        },
    }
