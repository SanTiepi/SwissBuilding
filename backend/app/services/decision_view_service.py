"""Decision View — aggregation service.

Assembles a unified decision-grade view for a building by reading from:
- Passport service (grade, trust, completeness)
- Readiness assessments
- Permit procedures (blockers)
- Obligations (overdue = blocker, due_soon = condition)
- Unknown issues (open = blocker)
- Audience packs (readiness per audience)
- Proof deliveries (proof chain)
- Diagnostic publications (proof chain)
- Artifact versions + custody events (custody posture)
- ROI calculator (inline ROI)

Pure read — never writes.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artifact_version import ArtifactVersion
from app.models.audience_pack import AudiencePack
from app.models.building import Building
from app.models.custody_event import CustodyEvent
from app.models.diagnostic_publication import DiagnosticReportPublication
from app.models.obligation import Obligation
from app.models.permit_procedure import PermitProcedure
from app.models.post_works_link import PostWorksLink
from app.models.proof_delivery import ProofDelivery
from app.models.unknown_issue import UnknownIssue
from app.schemas.decision_view import (
    AudienceReadiness,
    CustodyPosture,
    DecisionBlocker,
    DecisionClearItem,
    DecisionCondition,
    DecisionView,
    ProofChainItem,
    ROISummary,
)

logger = logging.getLogger(__name__)

_AUDIENCE_TYPES = ["authority", "insurer", "lender", "transaction"]


async def get_building_decision_view(
    db: AsyncSession,
    building_id: UUID,
) -> DecisionView | None:
    """Aggregate the full decision-grade view for a building.

    Returns None if the building does not exist.
    """
    # 0. Verify building exists
    building_result = await db.execute(select(Building).where(Building.id == building_id))
    building = building_result.scalar_one_or_none()
    if building is None:
        return None

    building_name = building.address or "Unknown"
    building_address = f"{building.address}, {building.postal_code} {building.city}" if building.address else None

    # 1. Passport summary (reuse service)
    passport_grade = "F"
    overall_trust = 0.0
    overall_completeness = 0.0
    readiness_status = "not_evaluated"
    try:
        from app.services.passport_service import get_passport_summary

        passport = await get_passport_summary(db, building_id)
        if passport:
            passport_grade = passport.get("passport_grade", "F")
            overall_trust = passport.get("knowledge_state", {}).get("overall_trust", 0.0)
            overall_completeness = passport.get("completeness", {}).get("overall", 0.0)
            # Best readiness status
            readiness_data = passport.get("readiness", {})
            for rtype in ["safe_to_start", "safe_to_tender", "safe_to_reopen", "safe_to_requalify"]:
                rs = readiness_data.get(rtype, {})
                if rs.get("status") not in (None, "not_evaluated"):
                    readiness_status = rs["status"]
                    break
    except Exception:
        logger.warning("Failed to load passport for decision view", exc_info=True)

    # 2. Blockers & conditions
    blockers: list[DecisionBlocker] = []
    conditions: list[DecisionCondition] = []
    clear_items: list[DecisionClearItem] = []

    # 2a. Blocked/rejected procedures → blocker
    proc_result = await db.execute(
        select(PermitProcedure).where(
            PermitProcedure.building_id == building_id,
            PermitProcedure.status.in_(["complement_requested", "rejected", "expired"]),
        )
    )
    for proc in proc_result.scalars().all():
        blockers.append(
            DecisionBlocker(
                id=str(proc.id),
                category="procedure_blocked",
                title=f"Procedure blocked: {proc.title}",
                description=f"Status: {proc.status}. Authority: {proc.authority_name or 'N/A'}",
                source_type="permit_procedure",
                source_id=str(proc.id),
                link_hint=f"/buildings/{building_id}/procedures/{proc.id}/authority-room",
            )
        )

    # 2b. Pending/under_review procedures → condition
    proc_pending_result = await db.execute(
        select(PermitProcedure).where(
            PermitProcedure.building_id == building_id,
            PermitProcedure.status.in_(["submitted", "under_review"]),
        )
    )
    for proc in proc_pending_result.scalars().all():
        conditions.append(
            DecisionCondition(
                id=str(proc.id),
                category="review_required",
                title=f"Procedure pending review: {proc.title}",
                description=f"Status: {proc.status}",
                source_type="permit_procedure",
                source_id=str(proc.id),
                link_hint=f"/buildings/{building_id}/procedures/{proc.id}/authority-room",
            )
        )

    # Approved procedures → clear
    proc_approved_result = await db.execute(
        select(PermitProcedure).where(
            PermitProcedure.building_id == building_id,
            PermitProcedure.status == "approved",
        )
    )
    for proc in proc_approved_result.scalars().all():
        clear_items.append(
            DecisionClearItem(
                id=str(proc.id),
                category="procedure_approved",
                title=f"Procedure approved: {proc.title}",
                description=f"Approved at: {proc.approved_at}",
            )
        )

    # 2c. Overdue obligations → blocker
    obl_result = await db.execute(
        select(Obligation).where(
            Obligation.building_id == building_id,
            Obligation.status == "overdue",
        )
    )
    for obl in obl_result.scalars().all():
        blockers.append(
            DecisionBlocker(
                id=str(obl.id),
                category="overdue_obligation",
                title=f"Overdue: {obl.title}",
                description=f"Due: {obl.due_date}, priority: {obl.priority}",
                source_type="obligation",
                source_id=str(obl.id),
            )
        )

    # Due soon obligations → condition
    obl_soon_result = await db.execute(
        select(Obligation).where(
            Obligation.building_id == building_id,
            Obligation.status == "due_soon",
        )
    )
    for obl in obl_soon_result.scalars().all():
        conditions.append(
            DecisionCondition(
                id=str(obl.id),
                category="aging_evidence",
                title=f"Due soon: {obl.title}",
                description=f"Due: {obl.due_date}",
                source_type="obligation",
                source_id=str(obl.id),
            )
        )

    # Completed obligations → clear
    obl_done_result = await db.execute(
        select(Obligation).where(
            Obligation.building_id == building_id,
            Obligation.status == "completed",
        )
    )
    for obl in obl_done_result.scalars().all():
        clear_items.append(
            DecisionClearItem(
                id=str(obl.id),
                category="obligation_completed",
                title=f"Completed: {obl.title}",
                description=f"Completed at: {obl.completed_at}",
            )
        )

    # 2d. Open unknowns → blocker
    unk_result = await db.execute(
        select(UnknownIssue).where(
            and_(
                UnknownIssue.building_id == building_id,
                UnknownIssue.status == "open",
                UnknownIssue.blocks_readiness.is_(True),
            )
        )
    )
    for unk in unk_result.scalars().all():
        blockers.append(
            DecisionBlocker(
                id=str(unk.id),
                category="unresolved_unknown",
                title=f"Unresolved: {unk.title}",
                description=unk.description or f"Unknown type: {unk.unknown_type}",
                source_type="unknown_issue",
                source_id=str(unk.id),
            )
        )

    # Non-blocking open unknowns → condition
    unk_nb_result = await db.execute(
        select(UnknownIssue).where(
            and_(
                UnknownIssue.building_id == building_id,
                UnknownIssue.status == "open",
                UnknownIssue.blocks_readiness.isnot(True),
            )
        )
    )
    for unk in unk_nb_result.scalars().all():
        conditions.append(
            DecisionCondition(
                id=str(unk.id),
                category="incomplete_coverage",
                title=f"Unknown: {unk.title}",
                description=unk.description or f"Unknown type: {unk.unknown_type}",
                source_type="unknown_issue",
                source_id=str(unk.id),
            )
        )

    # 3. Audience-specific readiness
    audience_readiness: list[AudienceReadiness] = []
    for audience in _AUDIENCE_TYPES:
        pack_result = await db.execute(
            select(AudiencePack)
            .where(
                AudiencePack.building_id == building_id,
                AudiencePack.pack_type == audience,
            )
            .order_by(AudiencePack.pack_version.desc())
            .limit(1)
        )
        pack = pack_result.scalar_one_or_none()

        ar = AudienceReadiness(audience=audience)
        if pack:
            ar.has_pack = True
            ar.latest_pack_version = pack.pack_version
            ar.latest_pack_status = pack.status
            ar.latest_pack_generated_at = pack.generated_at
            ar.included_sections = list((pack.sections or {}).keys()) if isinstance(pack.sections, dict) else []
            ar.excluded_sections = []  # redaction-removed sections not stored separately
            ar.unknowns_count = len(pack.unknowns_summary) if pack.unknowns_summary else 0
            ar.contradictions_count = len(pack.contradictions_summary) if pack.contradictions_summary else 0
            ar.residual_risks_count = len(pack.residual_risk_summary) if pack.residual_risk_summary else 0
            ar.trust_refs_count = len(pack.trust_refs) if pack.trust_refs else 0
            ar.proof_refs_count = len(pack.proof_refs) if pack.proof_refs else 0

            # Caveats from DecisionCaveatProfile (best-effort)
            try:
                from app.models.redaction_profile import DecisionCaveatProfile

                caveat_result = await db.execute(
                    select(DecisionCaveatProfile).where(
                        DecisionCaveatProfile.audience_type == audience,
                        DecisionCaveatProfile.is_active.is_(True),
                    )
                )
                caveat_profile = caveat_result.scalar_one_or_none()
                if caveat_profile and caveat_profile.caveats:
                    ar.caveats = [c.get("text", "") for c in caveat_profile.caveats if c.get("text")]
            except Exception:
                pass

        audience_readiness.append(ar)

    # 4. Proof chain
    proof_chain: list[ProofChainItem] = []

    # 4a. Latest diagnostic publication
    pub_result = await db.execute(
        select(DiagnosticReportPublication)
        .where(DiagnosticReportPublication.building_id == building_id)
        .order_by(DiagnosticReportPublication.published_at.desc())
        .limit(1)
    )
    pub = pub_result.scalar_one_or_none()
    if pub:
        proof_chain.append(
            ProofChainItem(
                label="Diagnostic Publication",
                entity_type="diagnostic_publication",
                entity_id=str(pub.id),
                version=pub.current_version,
                content_hash=pub.payload_hash,
                status=pub.match_state,
                occurred_at=pub.published_at,
            )
        )

    # 4b. Latest post-works link
    pw_result = await db.execute(
        select(PostWorksLink)
        .join(
            PostWorksLink.intervention,
        )
        .where(PostWorksLink.status == "finalized")
        .limit(1)
    )
    pw = pw_result.scalar_one_or_none()
    if pw:
        proof_chain.append(
            ProofChainItem(
                label="Post-Works Truth",
                entity_type="post_works_link",
                entity_id=str(pw.id),
                status=pw.status,
                occurred_at=pw.finalized_at,
            )
        )

    # 4c. Latest proof deliveries (by audience)
    for aud in ["authority", "insurer"]:
        pd_result = await db.execute(
            select(ProofDelivery)
            .where(
                ProofDelivery.building_id == building_id,
                ProofDelivery.audience == aud,
            )
            .order_by(ProofDelivery.created_at.desc())
            .limit(1)
        )
        pd = pd_result.scalar_one_or_none()
        if pd:
            proof_chain.append(
                ProofChainItem(
                    label=f"Proof Delivery ({aud})",
                    entity_type="proof_delivery",
                    entity_id=str(pd.id),
                    content_hash=pd.content_hash,
                    status=pd.status,
                    delivery_status=pd.status,
                    occurred_at=pd.sent_at or pd.created_at,
                )
            )

    # 4d. Latest audience packs
    for aud in _AUDIENCE_TYPES:
        ap_result = await db.execute(
            select(AudiencePack)
            .where(
                AudiencePack.building_id == building_id,
                AudiencePack.pack_type == aud,
            )
            .order_by(AudiencePack.pack_version.desc())
            .limit(1)
        )
        ap = ap_result.scalar_one_or_none()
        if ap:
            proof_chain.append(
                ProofChainItem(
                    label=f"Audience Pack ({aud})",
                    entity_type="audience_pack",
                    entity_id=str(ap.id),
                    version=ap.pack_version,
                    content_hash=ap.content_hash,
                    status=ap.status,
                    occurred_at=ap.generated_at,
                )
            )

    # 5. Custody posture
    av_count_result = await db.execute(select(func.count(ArtifactVersion.id)))
    total_av = av_count_result.scalar() or 0
    av_current_result = await db.execute(
        select(func.count(ArtifactVersion.id)).where(ArtifactVersion.status == "current")
    )
    current_av = av_current_result.scalar() or 0
    ce_count_result = await db.execute(select(func.count(CustodyEvent.id)))
    total_ce = ce_count_result.scalar() or 0
    ce_latest_result = await db.execute(select(func.max(CustodyEvent.occurred_at)))
    latest_ce = ce_latest_result.scalar()

    custody_posture = CustodyPosture(
        total_artifact_versions=total_av,
        current_versions=current_av,
        total_custody_events=total_ce,
        latest_custody_event_at=latest_ce,
    )

    # 6. ROI summary
    roi = ROISummary()
    try:
        from app.services.roi_calculator_service import calculate_building_roi

        roi_report = await calculate_building_roi(db, building_id)
        roi = ROISummary(
            time_saved_hours=roi_report.time_saved_hours,
            rework_avoided=roi_report.rework_avoided,
            blocker_days_saved=roi_report.blocker_days_saved,
            pack_reuse_count=roi_report.pack_reuse_count,
            evidence_sources=roi_report.evidence_sources,
        )
    except Exception:
        logger.warning("Failed to load ROI for decision view", exc_info=True)

    # 7. last_updated = most recent timestamp across key entities
    # Normalize all timestamps to naive UTC to avoid comparison errors
    def _to_naive(dt: datetime | None) -> datetime | None:
        if dt is None:
            return None
        if dt.tzinfo is not None:
            return dt.replace(tzinfo=None)
        return dt

    timestamps = [_to_naive(building.updated_at), _to_naive(building.created_at)]
    if pub:
        timestamps.append(_to_naive(pub.published_at))
    if latest_ce:
        timestamps.append(_to_naive(latest_ce))
    last_updated = max((t for t in timestamps if t is not None), default=datetime.now(UTC).replace(tzinfo=None))

    return DecisionView(
        building_id=building_id,
        building_name=building_name,
        building_address=building_address,
        passport_grade=passport_grade,
        overall_trust=overall_trust,
        overall_completeness=overall_completeness,
        readiness_status=readiness_status,
        last_updated=last_updated,
        custody_posture=custody_posture,
        blockers=blockers,
        conditions=conditions,
        clear_items=clear_items,
        audience_readiness=audience_readiness,
        proof_chain=proof_chain,
        roi=roi,
    )
