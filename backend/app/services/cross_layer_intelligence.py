"""
BatiConnect - Cross-Layer Intelligence Engine

The moat: correlates signals BETWEEN the 14 Building Life OS layers to
discover insights no single layer can produce.

10 insight types:
  risk_cascade, silent_degradation, sampling_trust_gap,
  document_evidence_mismatch, pattern_match, cluster_risk,
  flywheel_insight, compliance_countdown, hidden_opportunity,
  contagion_structural
"""

from __future__ import annotations

import hashlib
import logging
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_trust_score_v2 import BuildingTrustScore
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.field_observation import FieldObservation
from app.models.sample import Sample
from app.models.unknown_issue import UnknownIssue
from app.services.completeness_engine import evaluate_completeness
from app.services.evidence_score_service import compute_evidence_score

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STALE_MONTHS = 6
TRUST_GAP_THRESHOLD = 0.3  # sampling quality < trust by this much = gap
HIGH_EVIDENCE_THRESHOLD = 75
LOW_EVIDENCE_THRESHOLD = 40
HIGH_COMPLETENESS_THRESHOLD = 0.90
COMPLIANCE_COUNTDOWN_DAYS = 90
DIAGNOSTIC_VALIDITY_DAYS = 3 * 365  # 3 years Swiss standard
MIN_PATTERN_OCCURRENCES = 3

SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2, "opportunity": 3}


def _insight_id(*parts: str) -> str:
    """Deterministic insight ID from components."""
    raw = ":".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _ensure_aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


# ---------------------------------------------------------------------------
# Individual detectors
# ---------------------------------------------------------------------------


async def _detect_risk_cascade(
    db: AsyncSession,
    building_id: UUID,
    evidence_score: dict | None,
) -> list[dict[str, Any]]:
    """Evidence score dropping + overdue actions + expiring diagnostic = systemic failure."""
    insights: list[dict[str, Any]] = []
    if evidence_score is None:
        return insights

    score = evidence_score.get("score", 100)
    if score >= LOW_EVIDENCE_THRESHOLD:
        return insights

    now = datetime.now(UTC)
    now_naive = now.replace(tzinfo=None)

    # Count overdue critical/high actions
    overdue_cutoff = now_naive - timedelta(days=30)
    overdue_result = await db.execute(
        select(func.count()).where(
            and_(
                ActionItem.building_id == building_id,
                ActionItem.status == "open",
                ActionItem.priority.in_(["critical", "high"]),
                ActionItem.created_at < overdue_cutoff,
            )
        )
    )
    overdue_count = overdue_result.scalar() or 0

    # Check for expiring diagnostics
    diag_result = await db.execute(
        select(Diagnostic).where(
            and_(
                Diagnostic.building_id == building_id,
                Diagnostic.status.in_(["completed", "validated"]),
            )
        )
    )
    diagnostics = list(diag_result.scalars().all())
    expiring_count = 0
    for d in diagnostics:
        if d.date_inspection:
            diag_date = datetime(d.date_inspection.year, d.date_inspection.month, d.date_inspection.day, tzinfo=UTC)
            expiry = diag_date + timedelta(days=DIAGNOSTIC_VALIDITY_DAYS)
            remaining = (expiry - now).days
            if 0 < remaining <= COMPLIANCE_COUNTDOWN_DAYS:
                expiring_count += 1

    if overdue_count > 0 or expiring_count > 0:
        signals = [{"layer": "evidence_score", "signal": "low_score", "value": score}]
        if overdue_count > 0:
            signals.append({"layer": "actions", "signal": "overdue_count", "value": overdue_count})
        if expiring_count > 0:
            signals.append({"layer": "diagnostics", "signal": "expiring_count", "value": expiring_count})

        days_est = COMPLIANCE_COUNTDOWN_DAYS
        if expiring_count > 0 and diagnostics:
            # Use nearest expiry
            for d in diagnostics:
                if d.date_inspection:
                    diag_date = datetime(
                        d.date_inspection.year, d.date_inspection.month, d.date_inspection.day, tzinfo=UTC
                    )
                    remaining = (diag_date + timedelta(days=DIAGNOSTIC_VALIDITY_DAYS) - now).days
                    if 0 < remaining < days_est:
                        days_est = remaining

        insights.append(
            {
                "insight_id": _insight_id("risk_cascade", str(building_id)),
                "insight_type": "risk_cascade",
                "severity": "critical",
                "title": f"Risque systemique: non-conformite dans ~{days_est} jours",
                "description": (
                    f"Score de preuve faible ({score}/100), "
                    f"{overdue_count} action(s) en retard, "
                    f"{expiring_count} diagnostic(s) expirant prochainement."
                ),
                "evidence": signals,
                "recommendation": "Lancer un plan d'urgence: traiter les actions critiques et renouveler les diagnostics",
                "confidence": min(0.95, 0.6 + overdue_count * 0.1 + expiring_count * 0.1),
                "estimated_impact": f"Risque de blocage reglementaire dans {days_est} jours",
            }
        )

    return insights


async def _detect_silent_degradation(
    db: AsyncSession,
    building_id: UUID,
    evidence_score: dict | None,
) -> list[dict[str, Any]]:
    """No activity in 6+ months + trust declining + documents aging."""
    now = datetime.now(UTC)
    stale_cutoff = now - timedelta(days=STALE_MONTHS * 30)

    # Check latest activity dates
    diag_result = await db.execute(select(func.max(Diagnostic.created_at)).where(Diagnostic.building_id == building_id))
    latest_diag = diag_result.scalar()

    doc_result = await db.execute(select(func.max(Document.created_at)).where(Document.building_id == building_id))
    latest_doc = doc_result.scalar()

    action_result = await db.execute(
        select(func.max(ActionItem.created_at)).where(ActionItem.building_id == building_id)
    )
    latest_action = action_result.scalar()

    dates = [_ensure_aware(d) for d in [latest_diag, latest_doc, latest_action] if d is not None]
    if not dates:
        # No activity at all
        return [
            {
                "insight_id": _insight_id("silent_degradation", str(building_id), "no_activity"),
                "insight_type": "silent_degradation",
                "severity": "warning",
                "title": "Batiment oublie: aucune activite enregistree",
                "description": "Ce batiment n'a aucune activite enregistree. Personne ne surveille son etat.",
                "evidence": [{"layer": "activity", "signal": "no_activity", "value": True}],
                "recommendation": "Planifier un audit initial et creer un dossier de base",
                "confidence": 0.8,
                "estimated_impact": "Risque reglementaire inconnu — diagnostic urgent recommande",
            }
        ]

    latest = max(dates)
    if latest and latest < stale_cutoff:
        days_since = (now - latest).days
        signals = [{"layer": "activity", "signal": "days_since_last", "value": days_since}]

        # Check if trust is declining
        trust_result = await db.execute(
            select(BuildingTrustScore)
            .where(BuildingTrustScore.building_id == building_id)
            .order_by(BuildingTrustScore.assessed_at.desc())
            .limit(1)
        )
        trust_record = trust_result.scalar_one_or_none()
        if trust_record and trust_record.trend == "declining":
            signals.append({"layer": "trust", "signal": "trend_declining", "value": True})

        if evidence_score:
            freshness = evidence_score.get("freshness", 1.0)
            if freshness < 0.5:
                signals.append({"layer": "evidence_score", "signal": "low_freshness", "value": freshness})

        return [
            {
                "insight_id": _insight_id("silent_degradation", str(building_id)),
                "insight_type": "silent_degradation",
                "severity": "warning",
                "title": f"Degradation silencieuse: inactif depuis {days_since} jours",
                "description": (
                    f"Aucune activite depuis {days_since} jours ({days_since // 30} mois). "
                    "Les donnees vieillissent et la confiance diminue."
                ),
                "evidence": signals,
                "recommendation": "Verifier l'etat du batiment et mettre a jour le dossier",
                "confidence": min(0.9, 0.5 + (days_since / 365) * 0.3),
                "estimated_impact": "Perte progressive de fiabilite des donnees",
            }
        ]

    return []


async def _detect_sampling_trust_gap(
    db: AsyncSession,
    building_id: UUID,
) -> list[dict[str, Any]]:
    """Low sampling quality + high trust score = false confidence."""
    # Get trust score
    trust_result = await db.execute(
        select(BuildingTrustScore)
        .where(BuildingTrustScore.building_id == building_id)
        .order_by(BuildingTrustScore.assessed_at.desc())
        .limit(1)
    )
    trust_record = trust_result.scalar_one_or_none()
    if not trust_record or trust_record.overall_score < 0.5:
        return []

    # Check sample count vs zone count as a proxy for sampling quality
    sample_count_result = await db.execute(
        select(func.count())
        .select_from(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(Diagnostic.building_id == building_id)
    )
    sample_count = sample_count_result.scalar() or 0

    diag_count_result = await db.execute(
        select(func.count()).where(
            and_(
                Diagnostic.building_id == building_id,
                Diagnostic.status.in_(["completed", "validated"]),
            )
        )
    )
    diag_count = diag_count_result.scalar() or 0

    if diag_count == 0:
        return []

    avg_samples_per_diag = sample_count / max(diag_count, 1)

    # Low sampling = fewer than 3 samples per diagnostic on average
    if avg_samples_per_diag < 3 and trust_record.overall_score >= 0.7:
        gap = trust_record.overall_score - (avg_samples_per_diag / 10)
        return [
            {
                "insight_id": _insight_id("sampling_trust_gap", str(building_id)),
                "insight_type": "sampling_trust_gap",
                "severity": "warning",
                "title": "Confiance potentiellement gonflee: echantillonnage faible",
                "description": (
                    f"Score de confiance eleve ({trust_record.overall_score:.0%}) "
                    f"mais seulement {avg_samples_per_diag:.1f} echantillons/diagnostic en moyenne. "
                    "Le protocole d'echantillonnage pourrait etre insuffisant."
                ),
                "evidence": [
                    {"layer": "trust", "signal": "high_trust", "value": round(trust_record.overall_score, 3)},
                    {"layer": "sampling", "signal": "low_avg_samples", "value": round(avg_samples_per_diag, 1)},
                ],
                "recommendation": "Renforcer le protocole d'echantillonnage pour valider le score de confiance",
                "confidence": min(0.85, 0.5 + gap),
                "estimated_impact": "Score de confiance potentiellement survalue de 10-30%",
            }
        ]

    return []


async def _detect_document_evidence_mismatch(
    db: AsyncSession,
    building_id: UUID,
    evidence_score: dict | None,
) -> list[dict[str, Any]]:
    """Documents present but evidence score still low = docs aren't useful."""
    if evidence_score is None:
        return []

    score = evidence_score.get("score", 100)
    if score >= 50:
        return []

    doc_count_result = await db.execute(select(func.count()).where(Document.building_id == building_id))
    doc_count = doc_count_result.scalar() or 0

    if doc_count >= 3 and score < 50:
        return [
            {
                "insight_id": _insight_id("document_evidence_mismatch", str(building_id)),
                "insight_type": "document_evidence_mismatch",
                "severity": "info",
                "title": "Documents presents mais preuve insuffisante",
                "description": (
                    f"{doc_count} document(s) telecharge(s) mais le score de preuve reste faible ({score}/100). "
                    "Les documents ne comblent pas les lacunes identifiees."
                ),
                "evidence": [
                    {"layer": "documents", "signal": "doc_count", "value": doc_count},
                    {"layer": "evidence_score", "signal": "low_score", "value": score},
                ],
                "recommendation": "Verifier la pertinence des documents: diagnostics manquants, rapports incomplets?",
                "confidence": 0.7,
                "estimated_impact": "Documents existants pourraient etre mieux exploites",
            }
        ]

    return []


async def _detect_pattern_match(
    db: AsyncSession,
    building_id: UUID,
) -> list[dict[str, Any]]:
    """Field memory patterns match this building's profile."""
    # Get building context
    bld_result = await db.execute(select(Building).where(Building.id == building_id))
    building = bld_result.scalar_one_or_none()
    if not building:
        return []

    # Look for field observations across all buildings with matching context
    obs_result = await db.execute(
        select(FieldObservation).where(
            FieldObservation.building_id != building_id,
        )
    )
    observations = list(obs_result.scalars().all())

    if len(observations) < MIN_PATTERN_OCCURRENCES:
        return []

    # Group observations by type and count
    type_counts: Counter[str] = Counter()
    for obs in observations:
        type_counts[obs.observation_type] = type_counts.get(obs.observation_type, 0) + 1

    insights: list[dict[str, Any]] = []
    for obs_type, count in type_counts.most_common(3):
        if count >= MIN_PATTERN_OCCURRENCES:
            insights.append(
                {
                    "insight_id": _insight_id("pattern_match", str(building_id), obs_type),
                    "insight_type": "pattern_match",
                    "severity": "info",
                    "title": f"Tendance detectee: {obs_type} ({count} batiments similaires)",
                    "description": (
                        f"{count} batiments similaires presentent des observations de type '{obs_type}'. "
                        "Ce batiment pourrait etre concerne."
                    ),
                    "evidence": [
                        {"layer": "field_memory", "signal": "pattern_count", "value": count},
                        {"layer": "field_memory", "signal": "observation_type", "value": obs_type},
                    ],
                    "recommendation": f"Verifier si ce batiment presente des signes de '{obs_type}'",
                    "confidence": min(0.8, 0.4 + count * 0.05),
                    "estimated_impact": "Investigation preventive recommandee",
                }
            )
            break  # Only the strongest pattern per building

    return insights


async def _detect_compliance_countdown(
    db: AsyncSession,
    building_id: UUID,
) -> list[dict[str, Any]]:
    """Readiness blockers + known regulatory deadlines = time pressure."""
    now = datetime.now(UTC)

    # Count open blocking unknowns
    blocker_result = await db.execute(
        select(func.count()).where(
            and_(
                UnknownIssue.building_id == building_id,
                UnknownIssue.status == "open",
                UnknownIssue.blocks_readiness.is_(True),
            )
        )
    )
    blocker_count = blocker_result.scalar() or 0

    if blocker_count == 0:
        return []

    # Check nearest expiring diagnostic
    diag_result = await db.execute(
        select(Diagnostic).where(
            and_(
                Diagnostic.building_id == building_id,
                Diagnostic.status.in_(["completed", "validated"]),
            )
        )
    )
    diagnostics = list(diag_result.scalars().all())

    nearest_expiry_days = None
    for d in diagnostics:
        if d.date_inspection:
            diag_date = datetime(d.date_inspection.year, d.date_inspection.month, d.date_inspection.day, tzinfo=UTC)
            expiry = diag_date + timedelta(days=DIAGNOSTIC_VALIDITY_DAYS)
            remaining = (expiry - now).days
            if remaining > 0 and (nearest_expiry_days is None or remaining < nearest_expiry_days):
                nearest_expiry_days = remaining

    if nearest_expiry_days is not None and nearest_expiry_days <= COMPLIANCE_COUNTDOWN_DAYS:
        return [
            {
                "insight_id": _insight_id("compliance_countdown", str(building_id)),
                "insight_type": "compliance_countdown",
                "severity": "critical" if nearest_expiry_days <= 30 else "warning",
                "title": f"{blocker_count} bloqueur(s), diagnostic expire dans {nearest_expiry_days} jours",
                "description": (
                    f"{blocker_count} probleme(s) bloquant(s) non resolu(s) et un diagnostic "
                    f"expire dans {nearest_expiry_days} jours. Action immediate requise."
                ),
                "evidence": [
                    {"layer": "unknowns", "signal": "blocking_count", "value": blocker_count},
                    {"layer": "diagnostics", "signal": "days_to_expiry", "value": nearest_expiry_days},
                ],
                "recommendation": "Traiter les bloqueurs en priorite et planifier le renouvellement du diagnostic",
                "confidence": 0.9,
                "estimated_impact": f"Non-conformite dans {nearest_expiry_days} jours si inaction",
            }
        ]

    return []


async def _detect_hidden_opportunity(
    db: AsyncSession,
    building_id: UUID,
    evidence_score: dict | None,
) -> list[dict[str, Any]]:
    """High evidence + complete dossier + good sampling = ready for certification."""
    if evidence_score is None:
        return []

    score = evidence_score.get("score", 0)
    if score < HIGH_EVIDENCE_THRESHOLD:
        return []

    completeness_result = await evaluate_completeness(db, building_id)
    if completeness_result.overall_score < HIGH_COMPLETENESS_THRESHOLD:
        return []

    # Count open unknowns
    unknown_result = await db.execute(
        select(func.count()).where(
            and_(
                UnknownIssue.building_id == building_id,
                UnknownIssue.status == "open",
            )
        )
    )
    open_unknowns = unknown_result.scalar() or 0

    if open_unknowns <= 2:
        return [
            {
                "insight_id": _insight_id("hidden_opportunity", str(building_id)),
                "insight_type": "hidden_opportunity",
                "severity": "opportunity",
                "title": "Eligible au Certificat BatiConnect",
                "description": (
                    f"Score de preuve eleve ({score}/100), "
                    f"completude a {completeness_result.overall_score:.0%}, "
                    f"seulement {open_unknowns} inconnue(s) ouverte(s). "
                    "Ce batiment est pret pour la certification."
                ),
                "evidence": [
                    {"layer": "evidence_score", "signal": "high_score", "value": score},
                    {
                        "layer": "completeness",
                        "signal": "high_completeness",
                        "value": round(completeness_result.overall_score, 3),
                    },
                    {"layer": "unknowns", "signal": "low_open_count", "value": open_unknowns},
                ],
                "recommendation": "Initier la demande de Certificat BatiConnect — avantages assurance et valeur",
                "confidence": 0.85,
                "estimated_impact": "Valorisation du batiment + reduction prime assurance potentielle",
            }
        ]

    return []


async def _detect_flywheel_insight(
    db: AsyncSession,
    building_id: UUID,
) -> list[dict[str, Any]]:
    """Correction patterns suggest systematic classification errors."""
    from app.models.ai_feedback import AIFeedback

    # Count corrections for documents linked to this building
    feedback_result = await db.execute(
        select(AIFeedback).where(
            and_(
                AIFeedback.entity_type == "classification",
                AIFeedback.feedback_type == "correct",
            )
        )
    )
    feedbacks = list(feedback_result.scalars().all())

    if len(feedbacks) < 5:
        return []

    # Count correction pairs
    pair_counts: Counter[str] = Counter()
    for fb in feedbacks:
        original = fb.original_output or {}
        corrected = fb.corrected_output or {}
        if isinstance(original, dict) and isinstance(corrected, dict):
            orig_type = original.get("document_type", "unknown")
            corr_type = corrected.get("document_type", "unknown")
            if orig_type != corr_type:
                pair_counts[f"{orig_type}->{corr_type}"] += 1

    if pair_counts:
        top_pair, top_count = pair_counts.most_common(1)[0]
        if top_count >= 3:
            return [
                {
                    "insight_id": _insight_id("flywheel_insight", top_pair),
                    "insight_type": "flywheel_insight",
                    "severity": "info",
                    "title": f"Erreur de classification recurrente: {top_pair}",
                    "description": (
                        f"La classification '{top_pair}' a ete corrigee {top_count} fois. "
                        "Envisager un reapprentissage du modele."
                    ),
                    "evidence": [
                        {"layer": "flywheel", "signal": "correction_pair", "value": top_pair},
                        {"layer": "flywheel", "signal": "correction_count", "value": top_count},
                    ],
                    "recommendation": "Mettre a jour les regles de classification pour ce type de document",
                    "confidence": min(0.9, 0.5 + top_count * 0.1),
                    "estimated_impact": f"~{top_count} classifications futures ameliorees",
                }
            ]

    return []


async def _detect_contagion_structural(
    db: AsyncSession,
    building_id: UUID,
) -> list[dict[str, Any]]:
    """One actor's inaction blocks others — detect from stale action chains."""
    now = datetime.now(UTC)
    now_naive = now.replace(tzinfo=None)

    # Find open actions that have been open for a long time
    stale_cutoff = now_naive - timedelta(days=60)
    stale_actions_result = await db.execute(
        select(ActionItem).where(
            and_(
                ActionItem.building_id == building_id,
                ActionItem.status == "open",
                ActionItem.created_at < stale_cutoff,
            )
        )
    )
    stale_actions = list(stale_actions_result.scalars().all())

    if len(stale_actions) < 2:
        return []

    # Group by source_type to find blocked chains
    by_source: dict[str, int] = defaultdict(int)
    for a in stale_actions:
        source = a.source_type or "manual"
        by_source[source] += 1

    # If multiple source types are blocked, it suggests contagion
    if len(by_source) >= 2:
        total_blocked = sum(by_source.values())
        return [
            {
                "insight_id": _insight_id("contagion_structural", str(building_id)),
                "insight_type": "contagion_structural",
                "severity": "warning",
                "title": f"{total_blocked} actions bloquees dans {len(by_source)} domaines",
                "description": (
                    f"{total_blocked} actions ouvertes depuis plus de 60 jours, "
                    f"reparties sur {len(by_source)} domaines differents. "
                    "L'inaction dans un domaine bloque les autres."
                ),
                "evidence": [
                    {"layer": "actions", "signal": "stale_count", "value": total_blocked},
                    {"layer": "actions", "signal": "blocked_domains", "value": len(by_source)},
                ],
                "recommendation": "Identifier l'acteur bloquant et relancer le suivi",
                "confidence": 0.7,
                "estimated_impact": f"{total_blocked} actions debloquees si le goulot est resolu",
            }
        ]

    return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def detect_cross_layer_insights(
    db: AsyncSession,
    building_id: UUID,
) -> list[dict[str, Any]]:
    """Run all cross-layer correlation detectors for a building.

    Returns list of insight dicts sorted by severity.
    """
    # Verify building exists
    bld_result = await db.execute(select(Building).where(Building.id == building_id))
    building = bld_result.scalar_one_or_none()
    if building is None:
        return []

    # Compute shared data once
    evidence_score = await compute_evidence_score(db, building_id)

    all_insights: list[dict[str, Any]] = []

    detectors = [
        _detect_risk_cascade(db, building_id, evidence_score),
        _detect_silent_degradation(db, building_id, evidence_score),
        _detect_sampling_trust_gap(db, building_id),
        _detect_document_evidence_mismatch(db, building_id, evidence_score),
        _detect_pattern_match(db, building_id),
        _detect_compliance_countdown(db, building_id),
        _detect_hidden_opportunity(db, building_id, evidence_score),
        _detect_flywheel_insight(db, building_id),
        _detect_contagion_structural(db, building_id),
    ]

    for detector_coro in detectors:
        try:
            results = await detector_coro
            all_insights.extend(results)
        except Exception:
            logger.warning("Cross-layer detector failed for building %s", building_id, exc_info=True)

    # Sort by severity
    all_insights.sort(key=lambda i: SEVERITY_ORDER.get(i.get("severity", "info"), 99))

    return all_insights


async def detect_portfolio_insights(
    db: AsyncSession,
    org_id: UUID,
) -> list[dict[str, Any]]:
    """Portfolio-level cross-layer analysis across all org buildings."""
    bld_result = await db.execute(
        select(Building).where(
            and_(
                Building.organization_id == org_id,
                Building.status == "active",
            )
        )
    )
    buildings = list(bld_result.scalars().all())

    if not buildings:
        return []

    insights: list[dict[str, Any]] = []

    # Gather per-building data
    scores: list[dict[str, Any]] = []
    low_score_buildings: list[str] = []
    common_doc_gaps: Counter[str] = Counter()
    total_overdue = 0

    for b in buildings:
        es = await compute_evidence_score(db, b.id)
        if es:
            scores.append(es)
            if es.get("score", 100) < LOW_EVIDENCE_THRESHOLD:
                low_score_buildings.append(str(b.id))

        # Count open unknowns by type
        unknown_result = await db.execute(
            select(UnknownIssue.unknown_type).where(
                and_(
                    UnknownIssue.building_id == b.id,
                    UnknownIssue.status == "open",
                )
            )
        )
        for row in unknown_result.all():
            if row[0]:
                common_doc_gaps[row[0]] += 1

        # Count overdue actions
        now_naive = datetime.now(UTC).replace(tzinfo=None)
        overdue_cutoff = now_naive - timedelta(days=30)
        overdue_result = await db.execute(
            select(func.count()).where(
                and_(
                    ActionItem.building_id == b.id,
                    ActionItem.status == "open",
                    ActionItem.created_at < overdue_cutoff,
                )
            )
        )
        total_overdue += overdue_result.scalar() or 0

    # Cluster detection: buildings with correlated low scores
    if len(low_score_buildings) >= 2:
        avg_score = sum(s.get("score", 0) for s in scores) / max(len(scores), 1)
        insights.append(
            {
                "insight_id": _insight_id("cluster_risk", str(org_id)),
                "insight_type": "cluster_risk",
                "severity": "warning" if len(low_score_buildings) < 5 else "critical",
                "title": (
                    f"{len(low_score_buildings)}/{len(buildings)} batiments avec score faible (moy: {avg_score:.0f})"
                ),
                "description": (
                    f"{len(low_score_buildings)} batiments de votre portfolio ont un score de preuve "
                    f"inferieur a {LOW_EVIDENCE_THRESHOLD}. Investiguer comme un groupe peut reduire les couts."
                ),
                "evidence": [
                    {"layer": "evidence_score", "signal": "low_score_count", "value": len(low_score_buildings)},
                    {"layer": "portfolio", "signal": "avg_score", "value": round(avg_score, 1)},
                ],
                "recommendation": "Lancer une campagne groupee de diagnostic pour les batiments faibles",
                "confidence": 0.8,
                "estimated_impact": "Economie estimee de 20-35% via campagne groupee",
            }
        )

    # Common document gaps
    if common_doc_gaps:
        top_gap, top_count = common_doc_gaps.most_common(1)[0]
        if top_count >= 2:
            insights.append(
                {
                    "insight_id": _insight_id("portfolio_pattern", str(org_id), top_gap),
                    "insight_type": "cluster_risk",
                    "severity": "info",
                    "title": f"Lacune commune: '{top_gap}' dans {top_count} batiments",
                    "description": (
                        f"La categorie '{top_gap}' est une lacune ouverte dans "
                        f"{top_count} batiment(s). Traitement groupe recommande."
                    ),
                    "evidence": [
                        {"layer": "unknowns", "signal": "common_gap_category", "value": top_gap},
                        {"layer": "unknowns", "signal": "affected_buildings", "value": top_count},
                    ],
                    "recommendation": f"Traiter la lacune '{top_gap}' pour tous les batiments concernes",
                    "confidence": 0.75,
                    "estimated_impact": f"{top_count} batiments ameliores simultanement",
                }
            )

    # Portfolio benchmark
    if scores:
        avg_portfolio = sum(s.get("score", 0) for s in scores) / len(scores)
        market_avg = 65  # Reference benchmark
        if avg_portfolio < market_avg:
            insights.append(
                {
                    "insight_id": _insight_id("benchmark", str(org_id)),
                    "insight_type": "cluster_risk",
                    "severity": "info",
                    "title": f"Portfolio sous la moyenne: {avg_portfolio:.0f} vs {market_avg} (marche)",
                    "description": (
                        f"Votre portfolio a un score moyen de {avg_portfolio:.0f}/100, "
                        f"en dessous de la moyenne du marche ({market_avg}/100)."
                    ),
                    "evidence": [
                        {"layer": "portfolio", "signal": "avg_score", "value": round(avg_portfolio, 1)},
                        {"layer": "benchmark", "signal": "market_avg", "value": market_avg},
                    ],
                    "recommendation": "Prioriser les batiments les plus faibles pour remonter la moyenne",
                    "confidence": 0.7,
                    "estimated_impact": f"Objectif: atteindre {market_avg}/100 en moyenne",
                }
            )

    # Efficiency opportunity: grouped campaigns
    if total_overdue >= 5:
        insights.append(
            {
                "insight_id": _insight_id("efficiency", str(org_id)),
                "insight_type": "cluster_risk",
                "severity": "warning",
                "title": f"{total_overdue} actions en retard dans le portfolio",
                "description": (
                    f"{total_overdue} actions en retard a travers {len(buildings)} batiments. "
                    "Une campagne groupee accelererait le traitement."
                ),
                "evidence": [
                    {"layer": "actions", "signal": "total_overdue", "value": total_overdue},
                    {"layer": "portfolio", "signal": "building_count", "value": len(buildings)},
                ],
                "recommendation": "Creer une campagne de remise a niveau du portfolio",
                "confidence": 0.85,
                "estimated_impact": f"Reduction du retard de {total_overdue} actions",
            }
        )

    insights.sort(key=lambda i: SEVERITY_ORDER.get(i.get("severity", "info"), 99))
    return insights


async def get_intelligence_summary(
    db: AsyncSession,
    building_id: UUID | None = None,
    org_id: UUID | None = None,
) -> dict[str, Any]:
    """Aggregated intelligence summary: counts by type/severity, top 5 critical."""
    all_insights: list[dict[str, Any]] = []

    if building_id:
        all_insights = await detect_cross_layer_insights(db, building_id)
    elif org_id:
        all_insights = await detect_portfolio_insights(db, org_id)

    by_type: dict[str, int] = defaultdict(int)
    by_severity: dict[str, int] = defaultdict(int)

    for insight in all_insights:
        by_type[insight.get("insight_type", "unknown")] += 1
        by_severity[insight.get("severity", "info")] += 1

    top_5 = all_insights[:5]

    return {
        "total_insights": len(all_insights),
        "by_type": dict(by_type),
        "by_severity": dict(by_severity),
        "top_critical": top_5,
        "computed_at": datetime.now(UTC).isoformat(),
    }
