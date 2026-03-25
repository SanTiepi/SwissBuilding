"""BatiConnect — Public Sector (municipality / committee / governance) service."""

import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.committee_decision import CommitteeDecisionPack, ReviewDecisionTrace
from app.models.governance_signal import PublicAssetGovernanceSignal
from app.models.municipality_review_pack import MunicipalityReviewPack
from app.models.public_owner_mode import PublicOwnerOperatingMode

# ---- Operating Mode ----


async def activate_public_mode(
    db: AsyncSession,
    org_id: UUID,
    mode_data: dict,
) -> PublicOwnerOperatingMode:
    """Set or update PublicOwnerOperatingMode for an organization."""
    result = await db.execute(
        select(PublicOwnerOperatingMode).where(PublicOwnerOperatingMode.organization_id == org_id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        for key, value in mode_data.items():
            setattr(existing, key, value)
        await db.flush()
        await db.refresh(existing)
        return existing
    mode = PublicOwnerOperatingMode(organization_id=org_id, **mode_data)
    db.add(mode)
    await db.flush()
    await db.refresh(mode)
    return mode


async def get_public_mode(db: AsyncSession, org_id: UUID) -> PublicOwnerOperatingMode | None:
    result = await db.execute(
        select(PublicOwnerOperatingMode).where(PublicOwnerOperatingMode.organization_id == org_id)
    )
    return result.scalar_one_or_none()


# ---- Review Pack ----


def _compute_hash(sections: dict | list | None) -> str:
    raw = json.dumps(sections, sort_keys=True, default=str) if sections else ""
    return hashlib.sha256(raw.encode()).hexdigest()


def _assemble_review_sections(building_id: UUID) -> list[dict]:
    """Assemble standard review pack sections from existing data references."""
    return [
        {"section_type": "building_identity", "title": "Identite du batiment", "content_summary": "Assembled"},
        {"section_type": "diagnostics_summary", "title": "Resume des diagnostics", "content_summary": "Assembled"},
        {"section_type": "procedure_state", "title": "Etat des procedures", "content_summary": "Assembled"},
        {"section_type": "proof_inventory", "title": "Inventaire des preuves", "content_summary": "Assembled"},
        {
            "section_type": "obligations_summary",
            "title": "Resume des obligations",
            "content_summary": "Assembled",
        },
        {"section_type": "commune_context", "title": "Contexte communal", "content_summary": "Assembled"},
    ]


async def generate_review_pack(
    db: AsyncSession,
    building_id: UUID,
    user_id: UUID | None,
    *,
    notes: str | None = None,
    review_deadline=None,
) -> MunicipalityReviewPack:
    sections = _assemble_review_sections(building_id)
    content_hash = _compute_hash(sections)
    pack = MunicipalityReviewPack(
        building_id=building_id,
        generated_by_user_id=user_id,
        status="ready",
        sections=sections,
        content_hash=content_hash,
        notes=notes,
        review_deadline=review_deadline,
        generated_at=datetime.now(UTC),
    )
    db.add(pack)
    await db.flush()
    await db.refresh(pack)
    return pack


async def circulate_review_pack(
    db: AsyncSession,
    pack_id: UUID,
    recipients: list[dict],
) -> MunicipalityReviewPack:
    result = await db.execute(select(MunicipalityReviewPack).where(MunicipalityReviewPack.id == pack_id))
    pack = result.scalar_one_or_none()
    if not pack:
        raise ValueError("Review pack not found")
    pack.circulated_to = recipients
    pack.status = "circulating"
    await db.flush()
    await db.refresh(pack)
    return pack


async def get_review_packs(db: AsyncSession, building_id: UUID) -> list[MunicipalityReviewPack]:
    result = await db.execute(
        select(MunicipalityReviewPack)
        .where(MunicipalityReviewPack.building_id == building_id)
        .order_by(MunicipalityReviewPack.created_at.desc())
    )
    return list(result.scalars().all())


async def get_review_pack(db: AsyncSession, pack_id: UUID) -> MunicipalityReviewPack | None:
    result = await db.execute(select(MunicipalityReviewPack).where(MunicipalityReviewPack.id == pack_id))
    return result.scalar_one_or_none()


# ---- Committee Pack ----


def _assemble_committee_sections(building_id: UUID) -> list[dict]:
    """Assemble standard committee decision pack sections."""
    return [
        {"section_type": "building_identity", "title": "Identite du batiment", "content_summary": "Assembled"},
        {"section_type": "diagnostics_summary", "title": "Resume des diagnostics", "content_summary": "Assembled"},
        {"section_type": "risk_assessment", "title": "Evaluation des risques", "content_summary": "Assembled"},
        {"section_type": "financial_impact", "title": "Impact financier", "content_summary": "Assembled"},
        {"section_type": "legal_obligations", "title": "Obligations legales", "content_summary": "Assembled"},
    ]


async def generate_committee_pack(
    db: AsyncSession,
    building_id: UUID,
    committee_data: dict,
) -> CommitteeDecisionPack:
    sections = _assemble_committee_sections(building_id)
    content_hash = _compute_hash(sections)
    pack = CommitteeDecisionPack(
        building_id=building_id,
        committee_name=committee_data["committee_name"],
        committee_type=committee_data["committee_type"],
        status="draft",
        sections=sections,
        procurement_clauses=committee_data.get("procurement_clauses"),
        content_hash=content_hash,
        decision_deadline=committee_data.get("decision_deadline"),
    )
    db.add(pack)
    await db.flush()
    await db.refresh(pack)
    return pack


async def get_committee_packs(db: AsyncSession, building_id: UUID) -> list[CommitteeDecisionPack]:
    result = await db.execute(
        select(CommitteeDecisionPack)
        .where(CommitteeDecisionPack.building_id == building_id)
        .order_by(CommitteeDecisionPack.created_at.desc())
    )
    return list(result.scalars().all())


async def get_committee_pack(db: AsyncSession, pack_id: UUID) -> CommitteeDecisionPack | None:
    result = await db.execute(select(CommitteeDecisionPack).where(CommitteeDecisionPack.id == pack_id))
    return result.scalar_one_or_none()


# ---- Decision Traces ----


async def record_decision(db: AsyncSession, trace_data: dict) -> ReviewDecisionTrace:
    trace = ReviewDecisionTrace(**trace_data)
    db.add(trace)
    await db.flush()
    await db.refresh(trace)
    return trace


async def get_decision_traces(
    db: AsyncSession,
    pack_type: str,
    pack_id: UUID,
) -> list[ReviewDecisionTrace]:
    result = await db.execute(
        select(ReviewDecisionTrace)
        .where(ReviewDecisionTrace.pack_type == pack_type, ReviewDecisionTrace.pack_id == pack_id)
        .order_by(ReviewDecisionTrace.decided_at.desc())
    )
    return list(result.scalars().all())


# ---- Governance Signals ----


async def emit_governance_signal(
    db: AsyncSession,
    signal_data: dict,
) -> PublicAssetGovernanceSignal:
    signal = PublicAssetGovernanceSignal(**signal_data)
    db.add(signal)
    await db.flush()
    await db.refresh(signal)
    return signal


async def get_governance_signals(
    db: AsyncSession,
    org_id: UUID,
    building_id: UUID | None = None,
) -> list[PublicAssetGovernanceSignal]:
    query = select(PublicAssetGovernanceSignal).where(PublicAssetGovernanceSignal.organization_id == org_id)
    if building_id:
        query = query.where(PublicAssetGovernanceSignal.building_id == building_id)
    query = query.order_by(PublicAssetGovernanceSignal.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def resolve_signal(db: AsyncSession, signal_id: UUID) -> PublicAssetGovernanceSignal:
    result = await db.execute(select(PublicAssetGovernanceSignal).where(PublicAssetGovernanceSignal.id == signal_id))
    signal = result.scalar_one_or_none()
    if not signal:
        raise ValueError("Governance signal not found")
    signal.resolved = True
    signal.resolved_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(signal)
    return signal
