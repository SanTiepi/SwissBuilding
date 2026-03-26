"""
BatiConnect — Counterfactual Service ("Sans BatiConnect" Simulator)

Produces a side-by-side comparison: what your building looks like WITH
the platform vs what it would look like WITHOUT it. Every delta is
a concrete loss — scattered sources, invisible contradictions, no proof
chains, unknown grade, zero trust, incomplete dossier.

The cost heuristic translates fragmentation into hours and CHF,
making the value proposition tangible for property managers.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.building_trust_score_v2 import BuildingTrustScore
from app.models.compliance_artefact import ComplianceArtefact
from app.models.data_quality_issue import DataQualityIssue
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.evidence_link import EvidenceLink
from app.models.readiness_assessment import ReadinessAssessment
from app.models.sample import Sample
from app.schemas.indispensability import (
    CounterfactualResult,
    FragmentationCost,
    PlatformState,
)
from app.services.fragmentation_score_service import compute_fragmentation_score

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cost heuristics (conservative estimates, CHF)
# ---------------------------------------------------------------------------

_HOURS_PER_SOURCE_UNIFICATION = 2.0
_HOURS_PER_CONTRADICTION_INVESTIGATION = 4.0
_HOURS_PER_PROOF_CHAIN = 1.0
_HOURLY_RATE_CHF = 150.0  # gérance administrative rate


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def simulate_without_platform(
    db: AsyncSession,
    building_id: UUID,
) -> CounterfactualResult | None:
    """Simulate what the building's data state would be without BatiConnect.

    Returns None if building does not exist.
    """
    # ── 0. Verify building ────────────────────────────────────────
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        return None

    # ── 1. Current state (WITH platform) ──────────────────────────
    with_platform = await _build_current_state(db, building_id)

    # ── 2. Degraded state (WITHOUT platform) ──────────────────────
    without_platform = _build_degraded_state(with_platform)

    # ── 3. Delta (what's lost) ────────────────────────────────────
    delta = _compute_delta(with_platform, without_platform)

    # ── 4. Cost of fragmentation ──────────────────────────────────
    fragmentation = await compute_fragmentation_score(db, building_id)
    cost = _compute_cost(with_platform, fragmentation)

    return CounterfactualResult(
        building_id=building_id,
        with_platform=with_platform,
        without_platform=without_platform,
        delta=delta,
        cost_of_fragmentation=cost,
    )


# ---------------------------------------------------------------------------
# Current state
# ---------------------------------------------------------------------------


async def _build_current_state(
    db: AsyncSession,
    building_id: UUID,
) -> PlatformState:
    """Build the current platform state metrics."""
    # Sources: count distinct data origins
    source_types: set[str] = set()

    diag_count = (
        await db.execute(select(func.count()).select_from(Diagnostic).where(Diagnostic.building_id == building_id))
    ).scalar() or 0
    if diag_count > 0:
        source_types.add("diagnostic")

    doc_count = (
        await db.execute(select(func.count()).select_from(Document).where(Document.building_id == building_id))
    ).scalar() or 0
    if doc_count > 0:
        source_types.add("document")

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
        if sample_count > 0:
            source_types.add("sample")

    artefact_count = (
        await db.execute(
            select(func.count()).select_from(ComplianceArtefact).where(ComplianceArtefact.building_id == building_id)
        )
    ).scalar() or 0
    if artefact_count > 0:
        source_types.add("compliance")

    # Contradictions resolved
    resolved_count = (
        await db.execute(
            select(func.count())
            .select_from(DataQualityIssue)
            .where(
                and_(
                    DataQualityIssue.building_id == building_id,
                    DataQualityIssue.issue_type == "contradiction",
                    DataQualityIssue.status == "resolved",
                )
            )
        )
    ).scalar() or 0

    # Proof chains
    diag_ids_result = await db.execute(select(Diagnostic.id).where(Diagnostic.building_id == building_id))
    diag_ids = [r[0] for r in diag_ids_result.all()]
    doc_ids_result = await db.execute(select(Document.id).where(Document.building_id == building_id))
    doc_ids = [r[0] for r in doc_ids_result.all()]

    entity_ids = set(diag_ids + doc_ids)
    entity_ids.add(building_id)

    proof_chains = 0
    for eid in entity_ids:
        link_count = (
            await db.execute(
                select(func.count())
                .select_from(EvidenceLink)
                .where((EvidenceLink.source_id == eid) | (EvidenceLink.target_id == eid))
            )
        ).scalar() or 0
        proof_chains += link_count

    # Trust score
    trust_result = await db.execute(
        select(BuildingTrustScore)
        .where(BuildingTrustScore.building_id == building_id)
        .order_by(BuildingTrustScore.assessed_at.desc())
        .limit(1)
    )
    trust_score = trust_result.scalar_one_or_none()
    overall_trust = trust_score.overall_score if trust_score else 0.0

    # Completeness from readiness
    readiness_result = await db.execute(
        select(ReadinessAssessment).where(ReadinessAssessment.building_id == building_id)
    )
    readiness_records = list(readiness_result.scalars().all())
    scored = [ra for ra in readiness_records if ra.score is not None]
    completeness = round(sum(ra.score for ra in scored) / len(scored), 4) if scored else 0.0

    # Passport grade (simplified)
    if overall_trust >= 0.8 and completeness >= 0.9:
        grade = "A"
    elif overall_trust >= 0.6 and completeness >= 0.7:
        grade = "B"
    elif overall_trust >= 0.4 and completeness >= 0.5:
        grade = "C"
    elif overall_trust >= 0.2 or completeness >= 0.3:
        grade = "D"
    else:
        grade = "F"

    return PlatformState(
        sources_unified=len(source_types),
        contradictions_resolved=resolved_count,
        proof_chains=proof_chains,
        passport_grade=grade,
        overall_trust=round(overall_trust, 4),
        completeness=completeness,
    )


# ---------------------------------------------------------------------------
# Degraded state (without platform)
# ---------------------------------------------------------------------------


def _build_degraded_state(current: PlatformState) -> PlatformState:
    """What the building looks like without BatiConnect: everything degrades."""
    return PlatformState(
        sources_unified=0,  # no unification — each source is isolated
        contradictions_resolved=0,  # no detection = no resolution
        proof_chains=0,  # no evidence linking
        passport_grade="?",  # unknown — no assessment capability
        overall_trust=0.0,  # no trust measurement
        completeness=0.0,  # no completeness tracking
    )


# ---------------------------------------------------------------------------
# Delta computation
# ---------------------------------------------------------------------------


def _compute_delta(
    with_p: PlatformState,
    without_p: PlatformState,
) -> list[str]:
    """Compute human-readable French descriptions of what's lost."""
    delta: list[str] = []

    if with_p.sources_unified > 0:
        delta.append(
            f"{with_p.sources_unified} source(s) de données actuellement unifiées "
            "seraient dispersées dans autant de systèmes différents — "
            "Excel, classeurs, emails, portails cantonaux."
        )

    if with_p.contradictions_resolved > 0:
        delta.append(
            f"{with_p.contradictions_resolved} contradiction(s) résolue(s) par la plateforme "
            "redeviendraient invisibles. Chacune est un risque latent "
            "de décision erronée ou de non-conformité."
        )

    if with_p.proof_chains > 0:
        delta.append(
            f"{with_p.proof_chains} lien(s) de preuve seraient perdus. "
            "Sans chaîne de preuve, chaque document est un fichier isolé "
            "sans contexte ni traçabilité."
        )

    if with_p.passport_grade not in ("?", "F"):
        delta.append(
            f"Le grade passeport «{with_p.passport_grade}» deviendrait inconnu. "
            "Sans évaluation continue, impossible de connaître l'état réel "
            "du bâtiment ni sa progression."
        )

    if with_p.overall_trust > 0:
        delta.append(
            f"Le score de confiance ({with_p.overall_trust:.0%}) tomberait à zéro. "
            "Sans classification des données (prouvé/inféré/déclaré/obsolète), "
            "toutes les informations ont le même poids — y compris les obsolètes."
        )

    if with_p.completeness > 0:
        delta.append(
            f"La complétude ({with_p.completeness:.0%}) ne serait plus mesurée. "
            "Sans suivi, les lacunes du dossier restent invisibles jusqu'au "
            "jour du contrôle ou de la transaction."
        )

    if not delta:
        delta.append(
            "Le bâtiment n'a pas encore de données enrichies. BatiConnect est prêt à les unifier dès le premier import."
        )

    return delta


# ---------------------------------------------------------------------------
# Cost of fragmentation
# ---------------------------------------------------------------------------


def _compute_cost(
    current: PlatformState,
    fragmentation: object | None,
) -> FragmentationCost:
    """Estimate hours and CHF to manually reconstruct what BatiConnect provides."""
    source_hours = current.sources_unified * _HOURS_PER_SOURCE_UNIFICATION
    contradiction_hours = current.contradictions_resolved * _HOURS_PER_CONTRADICTION_INVESTIGATION
    proof_hours = current.proof_chains * _HOURS_PER_PROOF_CHAIN

    total_hours = source_hours + contradiction_hours + proof_hours
    total_chf = total_hours * _HOURLY_RATE_CHF

    breakdown = {
        "unification_sources": round(source_hours * _HOURLY_RATE_CHF, 2),
        "investigation_contradictions": round(contradiction_hours * _HOURLY_RATE_CHF, 2),
        "reconstitution_preuves": round(proof_hours * _HOURLY_RATE_CHF, 2),
    }

    return FragmentationCost(
        hours_to_reconstruct=round(total_hours, 1),
        cost_chf=round(total_chf, 2),
        breakdown=breakdown,
    )
