"""Finance Surfaces — Audience Pack service.

Assembles audience-tailored intelligence packs from existing building data,
applying redaction profiles, computing summaries, and evaluating caveats.
"""

import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audience_pack import AudiencePack
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.obligation import Obligation
from app.models.proof_delivery import ProofDelivery
from app.models.redaction_profile import DecisionCaveatProfile, ExternalAudienceRedactionProfile
from app.models.unknown_issue import UnknownIssue

# ---------------------------------------------------------------------------
# Pack generation
# ---------------------------------------------------------------------------


async def generate_pack(
    db: AsyncSession,
    building_id: UUID,
    pack_type: str,
    user_id: UUID | None = None,
) -> AudiencePack:
    """Assemble an audience pack from existing building data."""

    # 1. Load building context
    building = (await db.execute(select(Building).where(Building.id == building_id))).scalar_one_or_none()
    if not building:
        raise ValueError(f"Building {building_id} not found")

    # 2. Gather raw sections
    sections = await _assemble_sections(db, building)

    # 3. Apply redaction
    profile = await _get_redaction_profile(db, pack_type)
    if profile:
        sections = _apply_redaction(sections, profile)

    # 4. Compute summaries
    unknowns_summary = await _compute_unknowns_summary(db, building_id)
    contradictions_summary = await _compute_contradictions_summary(db, building_id)
    residual_risk_summary = _compute_residual_risk_summary(sections)
    trust_refs = _compute_trust_refs(sections)
    proof_refs = await _compute_proof_refs(db, building_id)

    # 5. Determine version
    version = await _next_version(db, building_id, pack_type)

    # 6. Compute content hash
    content_hash = _compute_hash(sections, unknowns_summary, contradictions_summary)

    pack = AudiencePack(
        building_id=building_id,
        pack_type=pack_type,
        pack_version=version,
        status="draft",
        generated_by_user_id=user_id,
        sections=sections,
        unknowns_summary=unknowns_summary,
        contradictions_summary=contradictions_summary,
        residual_risk_summary=residual_risk_summary,
        trust_refs=trust_refs,
        proof_refs=proof_refs,
        content_hash=content_hash,
        generated_at=datetime.now(UTC),
    )
    db.add(pack)
    await db.flush()
    await db.refresh(pack)
    return pack


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------


async def list_packs(
    db: AsyncSession,
    building_id: UUID,
    pack_type: str | None = None,
) -> list[AudiencePack]:
    query = select(AudiencePack).where(AudiencePack.building_id == building_id)
    if pack_type:
        query = query.where(AudiencePack.pack_type == pack_type)
    query = query.order_by(AudiencePack.generated_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_pack(db: AsyncSession, pack_id: UUID) -> AudiencePack | None:
    result = await db.execute(select(AudiencePack).where(AudiencePack.id == pack_id))
    return result.scalar_one_or_none()


async def share_pack(db: AsyncSession, pack_id: UUID, user_id: UUID | None = None) -> AudiencePack:
    """Mark pack as shared and create a ProofDelivery record."""
    pack = (await db.execute(select(AudiencePack).where(AudiencePack.id == pack_id))).scalar_one_or_none()
    if not pack:
        raise ValueError(f"AudiencePack {pack_id} not found")
    if pack.status not in ("draft", "ready"):
        raise ValueError(f"Cannot share pack in status '{pack.status}'")

    pack.status = "shared"

    # Create proof delivery
    delivery = ProofDelivery(
        building_id=pack.building_id,
        target_type="audience_pack",
        target_id=pack.id,
        audience=pack.pack_type,
        delivery_method="download",
        status="delivered",
        content_hash=pack.content_hash,
        content_version=pack.pack_version,
        sent_at=datetime.now(UTC),
        delivered_at=datetime.now(UTC),
        created_by=user_id,
    )
    db.add(delivery)
    await db.flush()
    await db.refresh(pack)
    return pack


# ---------------------------------------------------------------------------
# Pack comparison
# ---------------------------------------------------------------------------


async def compare_packs(db: AsyncSession, pack_id_1: UUID, pack_id_2: UUID) -> dict:
    """Diff sections and caveats between two audience packs."""
    pack1 = await get_pack(db, pack_id_1)
    pack2 = await get_pack(db, pack_id_2)
    if not pack1 or not pack2:
        raise ValueError("One or both packs not found")

    sections_1 = set((pack1.sections or {}).keys())
    sections_2 = set((pack2.sections or {}).keys())

    section_diff = {
        "only_in_1": sorted(sections_1 - sections_2),
        "only_in_2": sorted(sections_2 - sections_1),
        "common": sorted(sections_1 & sections_2),
    }

    # Caveat diff
    caveats_1 = await evaluate_caveats(db, pack1.building_id, pack1.pack_type)
    caveats_2 = await evaluate_caveats(db, pack2.building_id, pack2.pack_type)
    caveat_types_1 = {c["caveat_type"] for c in caveats_1}
    caveat_types_2 = {c["caveat_type"] for c in caveats_2}

    caveat_diff = {
        "only_in_1": sorted(caveat_types_1 - caveat_types_2),
        "only_in_2": sorted(caveat_types_2 - caveat_types_1),
    }

    return {
        "pack_1": pack1,
        "pack_2": pack2,
        "section_diff": section_diff,
        "caveat_diff": caveat_diff,
    }


# ---------------------------------------------------------------------------
# Redaction profiles
# ---------------------------------------------------------------------------


async def list_redaction_profiles(db: AsyncSession) -> list[ExternalAudienceRedactionProfile]:
    result = await db.execute(
        select(ExternalAudienceRedactionProfile).where(ExternalAudienceRedactionProfile.is_active.is_(True))
    )
    return list(result.scalars().all())


async def get_redaction_profile_by_code(db: AsyncSession, code: str) -> ExternalAudienceRedactionProfile | None:
    result = await db.execute(
        select(ExternalAudienceRedactionProfile).where(ExternalAudienceRedactionProfile.profile_code == code)
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Caveat evaluation
# ---------------------------------------------------------------------------


async def evaluate_caveats(db: AsyncSession, building_id: UUID, audience_type: str) -> list[dict]:
    """Evaluate applicable caveats for a building + audience combination."""
    result = await db.execute(
        select(DecisionCaveatProfile).where(
            DecisionCaveatProfile.audience_type == audience_type,
            DecisionCaveatProfile.is_active.is_(True),
        )
    )
    profiles = result.scalars().all()

    # Gather building context for condition evaluation
    context = await _build_caveat_context(db, building_id)

    evaluated = []
    for profile in profiles:
        if _caveat_applies(profile.applies_when, context):
            evaluated.append(
                {
                    "caveat_type": profile.caveat_type,
                    "severity": profile.severity,
                    "message": profile.template_text,
                    "applies_when": profile.applies_when,
                }
            )
    return evaluated


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _assemble_sections(db: AsyncSession, building: Building) -> dict:
    """Assemble all available sections from building data."""
    sections = {}

    # Building identity
    sections["building_identity"] = {
        "address": building.address,
        "postal_code": building.postal_code,
        "city": building.city,
        "canton": building.canton,
        "building_type": building.building_type,
        "construction_year": building.construction_year,
        "floors_above": building.floors_above,
        "floors_below": building.floors_below,
        "surface_area_m2": float(building.surface_area_m2) if building.surface_area_m2 else None,
    }

    # Diagnostics summary
    diagnostics = (await db.execute(select(Diagnostic).where(Diagnostic.building_id == building.id))).scalars().all()
    if diagnostics:
        sections["diagnostics_summary"] = [
            {
                "id": str(d.id),
                "diagnostic_type": d.diagnostic_type,
                "status": d.status,
                "date": str(d.date) if d.date else None,
            }
            for d in diagnostics
        ]

    # Obligations
    obligations = (await db.execute(select(Obligation).where(Obligation.building_id == building.id))).scalars().all()
    if obligations:
        sections["obligations"] = [
            {
                "id": str(o.id),
                "obligation_type": o.obligation_type,
                "status": o.status,
                "description": o.description,
            }
            for o in obligations
        ]

    # Documents
    documents = (await db.execute(select(Document).where(Document.building_id == building.id))).scalars().all()
    if documents:
        sections["documents"] = [
            {
                "id": str(d.id),
                "file_name": d.file_name,
                "document_type": d.document_type,
            }
            for d in documents
        ]

    return sections


async def _get_redaction_profile(db: AsyncSession, pack_type: str) -> ExternalAudienceRedactionProfile | None:
    """Look up the redaction profile for an audience type."""
    result = await db.execute(
        select(ExternalAudienceRedactionProfile).where(
            ExternalAudienceRedactionProfile.audience_type == pack_type,
            ExternalAudienceRedactionProfile.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


def _apply_redaction(sections: dict, profile: ExternalAudienceRedactionProfile) -> dict:
    """Remove blocked sections and redacted fields from assembled data."""
    blocked = set(profile.blocked_sections or [])
    allowed = set(profile.allowed_sections or [])

    # If allowed list is specified, keep only those; also remove blocked
    if allowed:
        sections = {k: v for k, v in sections.items() if k in allowed and k not in blocked}
    else:
        sections = {k: v for k, v in sections.items() if k not in blocked}

    # Apply field-level redactions
    for redaction in profile.redacted_fields or []:
        section_name = redaction.get("section")
        field_name = redaction.get("field")
        if section_name in sections and isinstance(sections[section_name], dict):
            sections[section_name].pop(field_name, None)

    return sections


async def _compute_unknowns_summary(db: AsyncSession, building_id: UUID) -> list[dict]:
    """Summarize unresolved unknowns for the building."""
    result = await db.execute(
        select(UnknownIssue).where(
            UnknownIssue.building_id == building_id,
            UnknownIssue.status != "resolved",
        )
    )
    unknowns = result.scalars().all()
    return [
        {
            "type": u.unknown_type,
            "description": u.title,
            "impact": u.severity if u.severity else "unknown",
        }
        for u in unknowns
    ]


async def _compute_contradictions_summary(db: AsyncSession, building_id: UUID) -> list[dict]:
    """Summarize data quality issues that represent contradictions."""
    from app.models.data_quality_issue import DataQualityIssue

    result = await db.execute(
        select(DataQualityIssue).where(
            DataQualityIssue.building_id == building_id,
            DataQualityIssue.status != "resolved",
        )
    )
    issues = result.scalars().all()
    return [
        {
            "type": i.issue_type,
            "description": i.description,
            "severity": i.severity,
        }
        for i in issues
    ]


def _compute_residual_risk_summary(sections: dict) -> list[dict]:
    """Derive residual risks from assembled sections."""
    risks = []
    diagnostics = sections.get("diagnostics_summary", [])
    for diag in diagnostics:
        if diag.get("status") != "validated":
            risks.append(
                {
                    "risk_type": "unvalidated_diagnostic",
                    "description": f"Diagnostic {diag.get('diagnostic_type', 'unknown')} not yet validated",
                    "mitigation": "Request diagnostic validation before decision",
                }
            )
    return risks


def _compute_trust_refs(sections: dict) -> list[dict]:
    """Build trust references from sections."""
    refs = []
    for diag in sections.get("diagnostics_summary", []):
        refs.append(
            {
                "entity_type": "diagnostic",
                "entity_id": diag.get("id"),
                "confidence": "verified" if diag.get("status") == "validated" else "declared",
                "freshness": diag.get("date"),
            }
        )
    return refs


async def _compute_proof_refs(db: AsyncSession, building_id: UUID) -> list[dict]:
    """List proof documents attached to the building."""
    documents = (await db.execute(select(Document).where(Document.building_id == building_id))).scalars().all()
    return [
        {
            "document_id": str(d.id),
            "label": d.file_name,
            "version": 1,
            "freshness_state": "current",
        }
        for d in documents
    ]


async def _next_version(db: AsyncSession, building_id: UUID, pack_type: str) -> int:
    """Compute next version number for a building+pack_type combination."""
    result = await db.execute(
        select(func.max(AudiencePack.pack_version)).where(
            AudiencePack.building_id == building_id,
            AudiencePack.pack_type == pack_type,
        )
    )
    current = result.scalar()
    return (current or 0) + 1


def _compute_hash(sections: dict, unknowns: list, contradictions: list) -> str:
    """SHA-256 of assembled content for integrity tracking."""
    payload = json.dumps(
        {"sections": sections, "unknowns": unknowns, "contradictions": contradictions},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


async def _build_caveat_context(db: AsyncSession, building_id: UUID) -> dict:
    """Gather minimal context for caveat condition evaluation."""
    # Check for unknowns
    unknown_count = (
        await db.execute(
            select(func.count())
            .select_from(UnknownIssue)
            .where(
                UnknownIssue.building_id == building_id,
                UnknownIssue.status != "resolved",
            )
        )
    ).scalar() or 0

    # Check for data quality issues
    from app.models.data_quality_issue import DataQualityIssue

    dq_count = (
        await db.execute(
            select(func.count())
            .select_from(DataQualityIssue)
            .where(
                DataQualityIssue.building_id == building_id,
                DataQualityIssue.status != "resolved",
            )
        )
    ).scalar() or 0

    return {
        "has_unknowns": unknown_count > 0,
        "has_contradictions": dq_count > 0,
        "unknown_count": unknown_count,
        "contradiction_count": dq_count,
    }


def _caveat_applies(applies_when: dict, context: dict) -> bool:
    """Check if a caveat's conditions match the current context."""
    if not applies_when:
        return True

    for key, expected in applies_when.items():
        if key == "has_unknowns" and context.get("has_unknowns") != expected:
            return False
        if key == "has_contradictions" and context.get("has_contradictions") != expected:
            return False
        if key == "min_unknowns" and context.get("unknown_count", 0) < expected:
            return False
        if key == "min_contradictions" and context.get("contradiction_count", 0) < expected:
            return False

    return True
