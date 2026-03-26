"""
BatiConnect — Defensibility Service

Measures how defensible decisions are WITH BatiConnect vs without.
Every action, obligation, and compliance artefact is only as strong as
the evidence chain behind it. Without BatiConnect, decisions become
opinions — with it, they become provable facts.
"""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_snapshot import BuildingSnapshot
from app.models.building_trust_score_v2 import BuildingTrustScore
from app.models.compliance_artefact import ComplianceArtefact
from app.models.data_quality_issue import DataQualityIssue
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.evidence_link import EvidenceLink
from app.models.readiness_assessment import ReadinessAssessment
from app.models.sample import Sample
from app.schemas.indispensability import (
    DecisionAuditTrail,
    DefensibilityResult,
    EvidenceDepth,
    TemporalDefensibility,
    WithoutUsScenario,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def compute_defensibility(
    db: AsyncSession,
    building_id: UUID,
) -> DefensibilityResult | None:
    """Compute how defensible decisions are for this building.

    Returns None if building does not exist.
    """
    # ── 0. Verify building ────────────────────────────────────────
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        return None

    # ── 1. Decision audit trail ───────────────────────────────────
    audit_trail = await _compute_decision_audit_trail(db, building_id)

    # ── 2. Evidence depth per decision type ───────────────────────
    evidence_depth = await _compute_evidence_depth(db, building_id)

    # ── 3. Without-us scenario ────────────────────────────────────
    without_us = await _compute_without_us_scenario(db, building_id, audit_trail, evidence_depth)

    # ── 4. Temporal defensibility ─────────────────────────────────
    temporal = await _compute_temporal_defensibility(db, building_id)

    return DefensibilityResult(
        building_id=building_id,
        decision_audit_trail=audit_trail,
        evidence_depth=evidence_depth,
        without_us_scenario=without_us,
        temporal_defensibility=temporal,
    )


# ---------------------------------------------------------------------------
# Decision audit trail
# ---------------------------------------------------------------------------


async def _compute_decision_audit_trail(
    db: AsyncSession,
    building_id: UUID,
) -> DecisionAuditTrail:
    """Count decisions/actions with full evidence backing."""
    # Actions with linked evidence
    action_ids_result = await db.execute(select(ActionItem.id).where(ActionItem.building_id == building_id))
    action_ids = [r[0] for r in action_ids_result.all()]

    actions_with_evidence = 0
    for aid in action_ids:
        link_count = (
            await db.execute(
                select(func.count())
                .select_from(EvidenceLink)
                .where((EvidenceLink.source_id == aid) | (EvidenceLink.target_id == aid))
            )
        ).scalar() or 0
        if link_count > 0:
            actions_with_evidence += 1

    # Obligations tracked (actions with due_date = tracked obligations)
    obligations_result = await db.execute(
        select(func.count())
        .select_from(ActionItem)
        .where(
            and_(
                ActionItem.building_id == building_id,
                ActionItem.due_date.isnot(None),
            )
        )
    )
    obligations_tracked = obligations_result.scalar() or 0

    # Procedures traced (compliance artefacts with submitted status)
    procedures_result = await db.execute(
        select(func.count())
        .select_from(ComplianceArtefact)
        .where(
            and_(
                ComplianceArtefact.building_id == building_id,
                ComplianceArtefact.status.in_(["submitted", "acknowledged"]),
            )
        )
    )
    procedures_traced = procedures_result.scalar() or 0

    # Packs with content hash (documents with integrity verification)
    packs_result = await db.execute(
        select(func.count())
        .select_from(Document)
        .where(
            and_(
                Document.building_id == building_id,
                Document.content_hash.isnot(None),
            )
        )
    )
    packs_with_hash = packs_result.scalar() or 0

    return DecisionAuditTrail(
        actions_with_evidence=actions_with_evidence,
        obligations_tracked=obligations_tracked,
        procedures_traced=procedures_traced,
        packs_with_hash=packs_with_hash,
    )


# ---------------------------------------------------------------------------
# Evidence depth per decision type
# ---------------------------------------------------------------------------


async def _compute_evidence_depth(
    db: AsyncSession,
    building_id: UUID,
) -> EvidenceDepth:
    """Count evidence sources supporting each major decision type."""
    # Safe-to-start: readiness assessments + diagnostics + samples
    readiness_count = (
        await db.execute(
            select(func.count()).select_from(ReadinessAssessment).where(ReadinessAssessment.building_id == building_id)
        )
    ).scalar() or 0

    diag_count = (
        await db.execute(select(func.count()).select_from(Diagnostic).where(Diagnostic.building_id == building_id))
    ).scalar() or 0

    sample_count = 0
    if diag_count > 0:
        sample_count = (
            await db.execute(
                select(func.count())
                .select_from(Sample)
                .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
                .where(Diagnostic.building_id == building_id)
            )
        ).scalar() or 0

    safe_to_start_sources = readiness_count + diag_count + sample_count

    # Risk assessment: data quality issues + trust scores + samples
    dqi_count = (
        await db.execute(
            select(func.count()).select_from(DataQualityIssue).where(DataQualityIssue.building_id == building_id)
        )
    ).scalar() or 0

    trust_count = (
        await db.execute(
            select(func.count()).select_from(BuildingTrustScore).where(BuildingTrustScore.building_id == building_id)
        )
    ).scalar() or 0

    risk_data_points = dqi_count + trust_count + sample_count

    # Compliance: artefacts count
    artefact_count = (
        await db.execute(
            select(func.count()).select_from(ComplianceArtefact).where(ComplianceArtefact.building_id == building_id)
        )
    ).scalar() or 0

    return EvidenceDepth(
        safe_to_start_sources=safe_to_start_sources,
        risk_assessment_data_points=risk_data_points,
        compliance_artefacts=artefact_count,
    )


# ---------------------------------------------------------------------------
# Without-us scenario
# ---------------------------------------------------------------------------


async def _compute_without_us_scenario(
    db: AsyncSession,
    building_id: UUID,
    audit_trail: DecisionAuditTrail,
    evidence_depth: EvidenceDepth,
) -> WithoutUsScenario:
    """Compute what would be missing without the platform."""
    # Total actions = all decisions made
    total_actions = (
        await db.execute(select(func.count()).select_from(ActionItem).where(ActionItem.building_id == building_id))
    ).scalar() or 0

    decisions_with_trace = audit_trail.actions_with_evidence + audit_trail.procedures_traced
    decisions_without_trace = max(0, total_actions - audit_trail.actions_with_evidence)

    total_decisions = decisions_with_trace + decisions_without_trace
    if total_decisions > 0:
        defensibility_score = round(decisions_with_trace / total_decisions, 4)
    else:
        # No decisions yet — platform provides structural defensibility
        defensibility_score = 0.0

    # Vulnerability points — concrete French descriptions
    vulnerabilities: list[str] = []

    if audit_trail.actions_with_evidence == 0 and total_actions > 0:
        vulnerabilities.append(
            f"{total_actions} action(s) sans preuve liée — en cas de litige, "
            "impossible de démontrer le fondement de ces décisions."
        )

    if evidence_depth.safe_to_start_sources == 0:
        vulnerabilities.append(
            "Aucune source ne soutient le verdict «safe to start». "
            "Un démarrage de chantier sans preuve de conformité expose "
            "le maître d'ouvrage à une responsabilité pénale (OTConst Art. 60a)."
        )

    if audit_trail.packs_with_hash == 0:
        vulnerabilities.append(
            "Aucun document avec empreinte d'intégrité. "
            "Sans hash SHA-256, il est impossible de prouver qu'un document "
            "n'a pas été modifié après coup."
        )

    if evidence_depth.compliance_artefacts == 0:
        vulnerabilities.append(
            "Aucun artefact de conformité enregistré. "
            "En cas de contrôle cantonal, aucune trace de soumission ou d'acquittement."
        )

    if audit_trail.obligations_tracked == 0 and total_actions > 0:
        vulnerabilities.append(
            "Aucune obligation avec échéance suivie. "
            "Sans suivi des délais, les prescriptions réglementaires risquent "
            "d'être manquées silencieusement."
        )

    if not vulnerabilities:
        vulnerabilities.append(
            "La couverture de preuve est solide. BatiConnect assure la continuité de cette défensibilité dans le temps."
        )

    return WithoutUsScenario(
        decisions_with_full_trace=decisions_with_trace,
        decisions_without_trace=decisions_without_trace,
        defensibility_score=defensibility_score,
        vulnerability_points=vulnerabilities,
    )


# ---------------------------------------------------------------------------
# Temporal defensibility
# ---------------------------------------------------------------------------


async def _compute_temporal_defensibility(
    db: AsyncSession,
    building_id: UUID,
) -> TemporalDefensibility:
    """Assess ability to prove state at any past point in time."""
    snapshots_result = await db.execute(
        select(BuildingSnapshot)
        .where(BuildingSnapshot.building_id == building_id)
        .order_by(BuildingSnapshot.captured_at.asc())
    )
    snapshots = list(snapshots_result.scalars().all())

    snapshots_count = len(snapshots)

    if snapshots_count == 0:
        return TemporalDefensibility(
            snapshots_count=0,
            time_coverage_days=0,
            temporal_gaps=[
                "Aucun snapshot historique. Sans mémoire temporelle, "
                "il est impossible de prouver l'état du bâtiment à une date passée — "
                "un handicap majeur en cas de contentieux ou de requalification."
            ],
        )

    # Time coverage
    earliest = snapshots[0].captured_at
    latest = snapshots[-1].captured_at
    now = datetime.utcnow()

    if earliest and latest:
        coverage_days = (now - earliest).days
    else:
        coverage_days = 0

    # Detect temporal gaps (periods > 90 days without snapshots)
    gaps: list[str] = []
    gap_threshold_days = 90

    for i in range(1, len(snapshots)):
        prev_date = snapshots[i - 1].captured_at
        curr_date = snapshots[i].captured_at
        if prev_date and curr_date:
            gap_days = (curr_date - prev_date).days
            if gap_days > gap_threshold_days:
                gaps.append(
                    f"Trou de {gap_days} jours entre "
                    f"{prev_date.strftime('%d.%m.%Y')} et {curr_date.strftime('%d.%m.%Y')} — "
                    "état du bâtiment non prouvable durant cette période."
                )

    # Check gap between last snapshot and now
    if latest:
        final_gap = (now - latest).days
        if final_gap > gap_threshold_days:
            gaps.append(
                f"Dernier snapshot il y a {final_gap} jours. "
                "L'état actuel n'est pas capturé — un snapshot récent est recommandé."
            )

    if not gaps:
        gaps.append(
            "Couverture temporelle continue. BatiConnect peut prouver l'état du bâtiment à chaque point dans le temps."
        )

    return TemporalDefensibility(
        snapshots_count=snapshots_count,
        time_coverage_days=coverage_days,
        temporal_gaps=gaps,
    )
