"""Contractor acknowledgment workflow service."""

import hashlib
import json
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contractor_acknowledgment import ContractorAcknowledgment
from app.models.intervention import Intervention
from app.schemas.contractor_acknowledgment import ContractorAcknowledgmentCreate

logger = logging.getLogger(__name__)


async def _build_eco_clause_summary(db: AsyncSession, building_id: UUID) -> dict | None:
    """Generate eco clause summary for a building if pollutant samples exist.

    Returns a dict with clause metadata or None when no pollutants are detected.
    """
    try:
        from app.services.eco_clause_template_service import generate_eco_clauses

        payload = await generate_eco_clauses(building_id, "renovation", db)
        if not payload.detected_pollutants:
            return None
        return {
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
                        }
                        for c in s.clauses
                    ],
                }
                for s in payload.sections
            ],
        }
    except Exception as e:
        logger.warning("Failed to generate eco clauses for building %s: %s", building_id, e)
        return None


async def create_acknowledgment(
    db: AsyncSession,
    building_id: UUID,
    data: ContractorAcknowledgmentCreate,
    created_by_id: UUID,
) -> ContractorAcknowledgment:
    """Create a pending contractor acknowledgment. Validates intervention exists and belongs to building.

    When the building has pollutant samples with threshold exceedances, eco clause
    sections are automatically appended to ``safety_requirements`` under the
    ``eco_clauses`` key.
    """
    result = await db.execute(
        select(Intervention).where(
            Intervention.id == data.intervention_id,
            Intervention.building_id == building_id,
        )
    )
    intervention = result.scalar_one_or_none()
    if not intervention:
        raise ValueError("Intervention not found or does not belong to this building")

    # Enrich safety_requirements with eco clauses when pollutants are detected
    safety_reqs = data.safety_requirements
    eco_summary = await _build_eco_clause_summary(db, building_id)
    if eco_summary is not None:
        # safety_requirements may be a list or dict; wrap in dict if needed
        if isinstance(safety_reqs, list):
            safety_reqs = {"items": safety_reqs, "eco_clauses": eco_summary}
        elif isinstance(safety_reqs, dict):
            safety_reqs = {**safety_reqs, "eco_clauses": eco_summary}

    ack = ContractorAcknowledgment(
        intervention_id=data.intervention_id,
        building_id=building_id,
        contractor_user_id=data.contractor_user_id,
        status="pending",
        safety_requirements=safety_reqs,
        expires_at=data.expires_at,
        created_by=created_by_id,
    )
    db.add(ack)
    return ack


async def send_acknowledgment(db: AsyncSession, ack_id: UUID) -> ContractorAcknowledgment:
    """Mark acknowledgment as sent."""
    ack = await _get_or_raise(db, ack_id)
    if ack.status != "pending":
        raise ValueError(f"Cannot send acknowledgment in status '{ack.status}'")
    ack.status = "sent"
    ack.sent_at = datetime.now(UTC)
    return ack


async def view_acknowledgment(db: AsyncSession, ack_id: UUID) -> ContractorAcknowledgment:
    """Mark acknowledgment as viewed (only if status=sent)."""
    ack = await _get_or_raise(db, ack_id)
    if ack.status != "sent":
        raise ValueError(f"Cannot view acknowledgment in status '{ack.status}'")
    ack.status = "viewed"
    ack.viewed_at = datetime.now(UTC)
    return ack


async def acknowledge(
    db: AsyncSession,
    ack_id: UUID,
    notes: str | None = None,
    ip_address: str | None = None,
) -> ContractorAcknowledgment:
    """Mark as acknowledged, compute SHA-256 hash of safety_requirements."""
    ack = await _get_or_raise(db, ack_id)
    if ack.status not in ("sent", "viewed"):
        raise ValueError(f"Cannot acknowledge in status '{ack.status}'")
    ack.status = "acknowledged"
    ack.acknowledged_at = datetime.now(UTC)
    ack.contractor_notes = notes
    ack.ip_address = ip_address
    ack.acknowledgment_hash = _compute_hash(ack.safety_requirements)
    return ack


async def refuse(
    db: AsyncSession,
    ack_id: UUID,
    reason: str,
) -> ContractorAcknowledgment:
    """Mark as refused with a reason."""
    ack = await _get_or_raise(db, ack_id)
    if ack.status not in ("sent", "viewed"):
        raise ValueError(f"Cannot refuse in status '{ack.status}'")
    ack.status = "refused"
    ack.refused_at = datetime.now(UTC)
    ack.refusal_reason = reason
    return ack


async def get_acknowledgment(db: AsyncSession, ack_id: UUID) -> ContractorAcknowledgment | None:
    """Get a single acknowledgment by ID."""
    result = await db.execute(select(ContractorAcknowledgment).where(ContractorAcknowledgment.id == ack_id))
    return result.scalar_one_or_none()


async def list_for_building(db: AsyncSession, building_id: UUID) -> list[ContractorAcknowledgment]:
    """List all acknowledgments for a building."""
    result = await db.execute(
        select(ContractorAcknowledgment).where(ContractorAcknowledgment.building_id == building_id)
    )
    return list(result.scalars().all())


async def list_for_contractor(db: AsyncSession, contractor_user_id: UUID) -> list[ContractorAcknowledgment]:
    """List all acknowledgments assigned to a contractor."""
    result = await db.execute(
        select(ContractorAcknowledgment).where(ContractorAcknowledgment.contractor_user_id == contractor_user_id)
    )
    return list(result.scalars().all())


async def check_expired(db: AsyncSession) -> list[ContractorAcknowledgment]:
    """Find and expire overdue pending/sent acknowledgments."""
    now = datetime.now(UTC)
    result = await db.execute(
        select(ContractorAcknowledgment).where(
            ContractorAcknowledgment.status.in_(["pending", "sent", "viewed"]),
            ContractorAcknowledgment.expires_at.isnot(None),
            ContractorAcknowledgment.expires_at < now,
        )
    )
    expired = list(result.scalars().all())
    for ack in expired:
        ack.status = "expired"
    return expired


async def get_intervention_ack_status(db: AsyncSession, intervention_id: UUID) -> dict:
    """Return whether all contractors have acknowledged for an intervention."""
    result = await db.execute(
        select(ContractorAcknowledgment).where(ContractorAcknowledgment.intervention_id == intervention_id)
    )
    acks = list(result.scalars().all())
    if not acks:
        return {"intervention_id": str(intervention_id), "total": 0, "acknowledged": 0, "all_acknowledged": True}
    acknowledged_count = sum(1 for a in acks if a.status == "acknowledged")
    return {
        "intervention_id": str(intervention_id),
        "total": len(acks),
        "acknowledged": acknowledged_count,
        "all_acknowledged": acknowledged_count == len(acks),
    }


def _compute_hash(safety_requirements: list | dict) -> str:
    """Compute SHA-256 hash of safety_requirements JSON."""
    canonical = json.dumps(safety_requirements, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def _get_or_raise(db: AsyncSession, ack_id: UUID) -> ContractorAcknowledgment:
    """Get acknowledgment or raise ValueError."""
    ack = await get_acknowledgment(db, ack_id)
    if not ack:
        raise ValueError("Contractor acknowledgment not found")
    return ack
