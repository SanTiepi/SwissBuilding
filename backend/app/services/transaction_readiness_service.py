"""
SwissBuildingOS - Transaction Readiness Service

Evaluates whether a building is ready for transactional milestones:
  - sell: can the building be sold with adequate documentation?
  - insure: can the building be insured against pollutant liability?
  - finance: can the building secure financing?
  - lease: can the building be leased safely to occupants?

Reuses passport grade, completeness engine, trust score, and contradiction
detection to produce a unified readiness assessment per transaction type.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.data_quality_issue import DataQualityIssue
from app.models.diagnostic import Diagnostic
from app.models.evidence_link import EvidenceLink
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.models.unknown_issue import UnknownIssue
from app.schemas.transaction_readiness import (
    BuildingReadinessRank,
    CheckSeverity,
    CheckStatus,
    ComparativeReadiness,
    FinancingScoreBreakdown,
    InsuranceRiskAssessment,
    InsuranceRiskTier,
    OverallStatus,
    ReadinessTrend,
    ReadinessTrendPoint,
    TransactionCheck,
    TransactionReadiness,
    TransactionType,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TRANSACTION_TYPES = tuple(t.value for t in TransactionType)

ALL_POLLUTANTS = {"asbestos", "pcb", "lead", "hap", "radon"}

# Thresholds per transaction type
SELL_MIN_GRADE = "C"
SELL_MIN_COMPLETENESS = 0.70

FINANCE_MIN_GRADE = "C"
FINANCE_MIN_COMPLETENESS = 0.80
FINANCE_MIN_TRUST = 0.60

INSURE_MIN_GRADE = "D"

# Grade ordering for comparison
_GRADE_ORDER = {"A": 1, "B": 2, "C": 3, "D": 4, "F": 5}


def _grade_meets_minimum(actual: str, minimum: str) -> bool:
    """Return True if actual grade is >= minimum (A is best)."""
    return _GRADE_ORDER.get(actual, 99) <= _GRADE_ORDER.get(minimum, 99)


# ---------------------------------------------------------------------------
# Check builder
# ---------------------------------------------------------------------------


def _check(
    check_id: str,
    category: str,
    label: str,
    status: CheckStatus,
    severity: CheckSeverity,
    detail: str | None = None,
) -> TransactionCheck:
    return TransactionCheck(
        check_id=check_id,
        category=category,
        label=label,
        status=status,
        severity=severity,
        detail=detail,
    )


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------


async def _get_passport_grade(db: AsyncSession, building_id: UUID) -> str | None:
    """Get passport grade, returning None if unavailable."""
    try:
        from app.services.passport_service import get_passport_summary

        passport = await get_passport_summary(db, building_id)
        if passport:
            return passport.get("passport_grade")
    except Exception as e:
        logger.warning(f"Failed to get passport grade for building {building_id}: {e}")
    return None


async def _get_completeness_score(db: AsyncSession, building_id: UUID) -> float | None:
    """Get completeness overall score, returning None if unavailable."""
    try:
        from app.services.completeness_engine import evaluate_completeness

        result = await evaluate_completeness(db, building_id)
        return result.overall_score
    except Exception as e:
        logger.warning(f"Failed to get completeness score for building {building_id}: {e}")
    return None


async def _get_trust_score(db: AsyncSession, building_id: UUID) -> float | None:
    """Get the latest trust score, returning None if unavailable."""
    try:
        from app.models.building_trust_score_v2 import BuildingTrustScore

        result = await db.execute(
            select(BuildingTrustScore)
            .where(BuildingTrustScore.building_id == building_id)
            .order_by(BuildingTrustScore.assessed_at.desc())
            .limit(1)
        )
        trust = result.scalar_one_or_none()
        if trust:
            return trust.overall_score
    except Exception as e:
        logger.warning(f"Failed to get trust score for building {building_id}: {e}")
    return None


async def _get_unresolved_contradictions(db: AsyncSession, building_id: UUID) -> int:
    """Count unresolved contradictions for a building."""
    result = await db.execute(
        select(DataQualityIssue).where(
            and_(
                DataQualityIssue.building_id == building_id,
                DataQualityIssue.issue_type == "contradiction",
                DataQualityIssue.status != "resolved",
            )
        )
    )
    return len(list(result.scalars().all()))


async def _get_critical_unknowns(db: AsyncSession, building_id: UUID) -> int:
    """Count open unknowns that block readiness."""
    result = await db.execute(
        select(UnknownIssue).where(
            and_(
                UnknownIssue.building_id == building_id,
                UnknownIssue.status == "open",
                UnknownIssue.blocks_readiness.is_(True),
            )
        )
    )
    return len(list(result.scalars().all()))


async def _get_diagnostics(db: AsyncSession, building_id: UUID) -> list[Diagnostic]:
    result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    return list(result.scalars().all())


async def _get_samples_for_diagnostics(db: AsyncSession, diag_ids: list[UUID]) -> list[Sample]:
    if not diag_ids:
        return []
    result = await db.execute(select(Sample).where(Sample.diagnostic_id.in_(diag_ids)))
    return list(result.scalars().all())


async def _get_interventions(db: AsyncSession, building_id: UUID) -> list[Intervention]:
    result = await db.execute(select(Intervention).where(Intervention.building_id == building_id))
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Per-type evaluators
# ---------------------------------------------------------------------------


async def _evaluate_sell(
    db: AsyncSession,
    building_id: UUID,
) -> tuple[list[TransactionCheck], list[str], list[str], list[str]]:
    """Evaluate readiness for building sale."""
    checks: list[TransactionCheck] = []
    blockers: list[str] = []
    conditions: list[str] = []
    recommendations: list[str] = []

    # 1. Passport grade >= C
    grade = await _get_passport_grade(db, building_id)
    if grade is None:
        checks.append(
            _check(
                "passport_grade",
                "passport",
                "Passport grade >= C",
                CheckStatus.unknown,
                CheckSeverity.blocker,
                "Passport grade not available",
            )
        )
        blockers.append("Passport grade not available")
        recommendations.append("Run passport evaluation to determine building grade")
    elif _grade_meets_minimum(grade, SELL_MIN_GRADE):
        checks.append(
            _check(
                "passport_grade",
                "passport",
                "Passport grade >= C",
                CheckStatus.met,
                CheckSeverity.info,
                f"Grade: {grade}",
            )
        )
    else:
        checks.append(
            _check(
                "passport_grade",
                "passport",
                "Passport grade >= C",
                CheckStatus.unmet,
                CheckSeverity.blocker,
                f"Grade: {grade} (minimum: {SELL_MIN_GRADE})",
            )
        )
        blockers.append(f"Passport grade {grade} is below minimum {SELL_MIN_GRADE}")
        recommendations.append("Improve building documentation to raise passport grade")

    # 2. Completeness >= 70%
    completeness = await _get_completeness_score(db, building_id)
    if completeness is None:
        checks.append(
            _check(
                "completeness",
                "dossier",
                "Dossier completeness >= 70%",
                CheckStatus.unknown,
                CheckSeverity.blocker,
                "Completeness score not available",
            )
        )
        blockers.append("Dossier completeness not available")
        recommendations.append("Run completeness evaluation")
    elif completeness >= SELL_MIN_COMPLETENESS:
        checks.append(
            _check(
                "completeness",
                "dossier",
                "Dossier completeness >= 70%",
                CheckStatus.met,
                CheckSeverity.info,
                f"Completeness: {completeness:.0%}",
            )
        )
    else:
        checks.append(
            _check(
                "completeness",
                "dossier",
                "Dossier completeness >= 70%",
                CheckStatus.unmet,
                CheckSeverity.blocker,
                f"Completeness: {completeness:.0%} (minimum: 70%)",
            )
        )
        blockers.append(f"Dossier completeness {completeness:.0%} is below 70%")
        recommendations.append("Complete missing dossier items to reach 70% completeness")

    # 3. No critical unknowns
    critical_unknowns = await _get_critical_unknowns(db, building_id)
    if critical_unknowns == 0:
        checks.append(
            _check(
                "no_critical_unknowns",
                "knowledge",
                "No critical unknowns",
                CheckStatus.met,
                CheckSeverity.info,
                "No blocking unknown issues",
            )
        )
    else:
        checks.append(
            _check(
                "no_critical_unknowns",
                "knowledge",
                "No critical unknowns",
                CheckStatus.unmet,
                CheckSeverity.blocker,
                f"{critical_unknowns} critical unknown(s)",
            )
        )
        blockers.append(f"{critical_unknowns} critical unknown issue(s) remain unresolved")
        recommendations.append("Resolve critical unknown issues before sale")

    # 4. No unresolved contradictions
    contradictions = await _get_unresolved_contradictions(db, building_id)
    if contradictions == 0:
        checks.append(
            _check(
                "no_contradictions",
                "quality",
                "No unresolved contradictions",
                CheckStatus.met,
                CheckSeverity.info,
                "No contradictions found",
            )
        )
    else:
        checks.append(
            _check(
                "no_contradictions",
                "quality",
                "No unresolved contradictions",
                CheckStatus.unmet,
                CheckSeverity.warning,
                f"{contradictions} unresolved contradiction(s)",
            )
        )
        conditions.append(f"{contradictions} unresolved contradiction(s) should be addressed")
        recommendations.append("Resolve data contradictions before sale")

    # 5. Transfer package generatable (proxy: has completed diagnostics)
    diagnostics = await _get_diagnostics(db, building_id)
    completed_diags = [d for d in diagnostics if d.status in ("completed", "validated")]
    if completed_diags:
        checks.append(
            _check(
                "transfer_ready",
                "documentation",
                "Transfer package generatable",
                CheckStatus.met,
                CheckSeverity.info,
                f"{len(completed_diags)} completed diagnostic(s)",
            )
        )
    else:
        checks.append(
            _check(
                "transfer_ready",
                "documentation",
                "Transfer package generatable",
                CheckStatus.unmet,
                CheckSeverity.warning,
                "No completed diagnostics for transfer package",
            )
        )
        conditions.append("No completed diagnostics — transfer package will be incomplete")
        recommendations.append("Complete at least one diagnostic before sale")

    return checks, blockers, conditions, recommendations


async def _evaluate_insure(
    db: AsyncSession,
    building_id: UUID,
) -> tuple[list[TransactionCheck], list[str], list[str], list[str]]:
    """Evaluate readiness for building insurance."""
    checks: list[TransactionCheck] = []
    blockers: list[str] = []
    conditions: list[str] = []
    recommendations: list[str] = []

    # 1. Passport grade >= D
    grade = await _get_passport_grade(db, building_id)
    if grade is None:
        checks.append(
            _check(
                "passport_grade",
                "passport",
                "Passport grade >= D",
                CheckStatus.unknown,
                CheckSeverity.blocker,
                "Passport grade not available",
            )
        )
        blockers.append("Passport grade not available")
        recommendations.append("Run passport evaluation to determine building grade")
    elif _grade_meets_minimum(grade, INSURE_MIN_GRADE):
        checks.append(
            _check(
                "passport_grade",
                "passport",
                "Passport grade >= D",
                CheckStatus.met,
                CheckSeverity.info,
                f"Grade: {grade}",
            )
        )
    else:
        checks.append(
            _check(
                "passport_grade",
                "passport",
                "Passport grade >= D",
                CheckStatus.unmet,
                CheckSeverity.blocker,
                f"Grade: {grade} (minimum: {INSURE_MIN_GRADE})",
            )
        )
        blockers.append(f"Passport grade {grade} is below minimum {INSURE_MIN_GRADE}")
        recommendations.append("Improve building documentation to raise passport grade")

    # 2. No hazard zones without interventions
    diagnostics = await _get_diagnostics(db, building_id)
    diag_ids = [d.id for d in diagnostics]
    samples = await _get_samples_for_diagnostics(db, diag_ids)
    interventions = await _get_interventions(db, building_id)

    hazard_samples = [
        s for s in samples if s.threshold_exceeded and (s.risk_level or "").lower() in ("critical", "high")
    ]
    completed_interventions = [i for i in interventions if i.status == "completed"]

    if hazard_samples and not completed_interventions:
        checks.append(
            _check(
                "hazard_interventions",
                "risk",
                "No hazard zones without interventions",
                CheckStatus.unmet,
                CheckSeverity.blocker,
                f"{len(hazard_samples)} high/critical sample(s) without completed interventions",
            )
        )
        blockers.append(f"{len(hazard_samples)} hazard sample(s) without completed interventions")
        recommendations.append("Complete interventions for all hazard zones")
    else:
        checks.append(
            _check(
                "hazard_interventions",
                "risk",
                "No hazard zones without interventions",
                CheckStatus.met,
                CheckSeverity.info,
                "Hazard zones addressed" if hazard_samples else "No hazard zones identified",
            )
        )

    # 3. Asbestos status documented
    asbestos_samples = [s for s in samples if (s.pollutant_type or "").lower() == "asbestos"]
    completed = [d for d in diagnostics if d.status in ("completed", "validated")]
    if asbestos_samples or completed:
        checks.append(
            _check(
                "asbestos_documented",
                "pollutant",
                "Asbestos status documented",
                CheckStatus.met,
                CheckSeverity.info,
                f"{len(asbestos_samples)} asbestos sample(s) documented",
            )
        )
    else:
        checks.append(
            _check(
                "asbestos_documented",
                "pollutant",
                "Asbestos status documented",
                CheckStatus.unmet,
                CheckSeverity.warning,
                "No asbestos assessment found",
            )
        )
        conditions.append("Asbestos status not documented")
        recommendations.append("Conduct asbestos assessment for insurance eligibility")

    # 4. Risk analysis complete
    if completed:
        checks.append(
            _check(
                "risk_analysis",
                "risk",
                "Risk analysis complete",
                CheckStatus.met,
                CheckSeverity.info,
                f"{len(completed)} completed diagnostic(s)",
            )
        )
    else:
        checks.append(
            _check(
                "risk_analysis",
                "risk",
                "Risk analysis complete",
                CheckStatus.unmet,
                CheckSeverity.blocker,
                "No completed risk analysis / diagnostic",
            )
        )
        blockers.append("No completed risk analysis")
        recommendations.append("Complete a full diagnostic / risk analysis")

    return checks, blockers, conditions, recommendations


async def _evaluate_finance(
    db: AsyncSession,
    building_id: UUID,
) -> tuple[list[TransactionCheck], list[str], list[str], list[str]]:
    """Evaluate readiness for building financing."""
    checks: list[TransactionCheck] = []
    blockers: list[str] = []
    conditions: list[str] = []
    recommendations: list[str] = []

    # 1. Passport grade >= C
    grade = await _get_passport_grade(db, building_id)
    if grade is None:
        checks.append(
            _check(
                "passport_grade",
                "passport",
                "Passport grade >= C",
                CheckStatus.unknown,
                CheckSeverity.blocker,
                "Passport grade not available",
            )
        )
        blockers.append("Passport grade not available")
        recommendations.append("Run passport evaluation to determine building grade")
    elif _grade_meets_minimum(grade, FINANCE_MIN_GRADE):
        checks.append(
            _check(
                "passport_grade",
                "passport",
                "Passport grade >= C",
                CheckStatus.met,
                CheckSeverity.info,
                f"Grade: {grade}",
            )
        )
    else:
        checks.append(
            _check(
                "passport_grade",
                "passport",
                "Passport grade >= C",
                CheckStatus.unmet,
                CheckSeverity.blocker,
                f"Grade: {grade} (minimum: {FINANCE_MIN_GRADE})",
            )
        )
        blockers.append(f"Passport grade {grade} is below minimum {FINANCE_MIN_GRADE}")
        recommendations.append("Improve building documentation to raise passport grade")

    # 2. Completeness >= 80%
    completeness = await _get_completeness_score(db, building_id)
    if completeness is None:
        checks.append(
            _check(
                "completeness",
                "dossier",
                "Dossier completeness >= 80%",
                CheckStatus.unknown,
                CheckSeverity.blocker,
                "Completeness score not available",
            )
        )
        blockers.append("Dossier completeness not available")
        recommendations.append("Run completeness evaluation")
    elif completeness >= FINANCE_MIN_COMPLETENESS:
        checks.append(
            _check(
                "completeness",
                "dossier",
                "Dossier completeness >= 80%",
                CheckStatus.met,
                CheckSeverity.info,
                f"Completeness: {completeness:.0%}",
            )
        )
    else:
        checks.append(
            _check(
                "completeness",
                "dossier",
                "Dossier completeness >= 80%",
                CheckStatus.unmet,
                CheckSeverity.blocker,
                f"Completeness: {completeness:.0%} (minimum: 80%)",
            )
        )
        blockers.append(f"Dossier completeness {completeness:.0%} is below 80%")
        recommendations.append("Complete missing dossier items to reach 80% completeness")

    # 3. Trust score >= 0.6
    trust = await _get_trust_score(db, building_id)
    if trust is None:
        checks.append(
            _check(
                "trust_score",
                "quality",
                "Trust score >= 0.6",
                CheckStatus.unknown,
                CheckSeverity.warning,
                "Trust score not available",
            )
        )
        conditions.append("Trust score not available — may affect financing terms")
        recommendations.append("Run trust score calculation")
    elif trust >= FINANCE_MIN_TRUST:
        checks.append(
            _check(
                "trust_score",
                "quality",
                "Trust score >= 0.6",
                CheckStatus.met,
                CheckSeverity.info,
                f"Trust score: {trust:.2f}",
            )
        )
    else:
        checks.append(
            _check(
                "trust_score",
                "quality",
                "Trust score >= 0.6",
                CheckStatus.unmet,
                CheckSeverity.warning,
                f"Trust score: {trust:.2f} (minimum: 0.6)",
            )
        )
        conditions.append(f"Trust score {trust:.2f} is below 0.6")
        recommendations.append("Improve data quality to raise trust score above 0.6")

    # 4. No critical blockers (unknowns)
    critical_unknowns = await _get_critical_unknowns(db, building_id)
    if critical_unknowns == 0:
        checks.append(
            _check(
                "no_critical_blockers",
                "knowledge",
                "No critical blockers",
                CheckStatus.met,
                CheckSeverity.info,
                "No critical blocking issues",
            )
        )
    else:
        checks.append(
            _check(
                "no_critical_blockers",
                "knowledge",
                "No critical blockers",
                CheckStatus.unmet,
                CheckSeverity.blocker,
                f"{critical_unknowns} critical blocker(s)",
            )
        )
        blockers.append(f"{critical_unknowns} critical blocker(s) remain unresolved")
        recommendations.append("Resolve critical blockers before seeking financing")

    return checks, blockers, conditions, recommendations


async def _evaluate_lease(
    db: AsyncSession,
    building_id: UUID,
) -> tuple[list[TransactionCheck], list[str], list[str], list[str]]:
    """Evaluate readiness for building lease."""
    checks: list[TransactionCheck] = []
    blockers: list[str] = []
    conditions: list[str] = []
    recommendations: list[str] = []

    diagnostics = await _get_diagnostics(db, building_id)
    diag_ids = [d.id for d in diagnostics]
    samples = await _get_samples_for_diagnostics(db, diag_ids)
    interventions = await _get_interventions(db, building_id)

    # 1. No active hazard zones for occupants
    hazard_samples = [
        s for s in samples if s.threshold_exceeded and (s.risk_level or "").lower() in ("critical", "high")
    ]
    completed_interventions = [i for i in interventions if i.status == "completed"]

    if hazard_samples and not completed_interventions:
        checks.append(
            _check(
                "no_active_hazards",
                "safety",
                "No active hazard zones for occupants",
                CheckStatus.unmet,
                CheckSeverity.blocker,
                f"{len(hazard_samples)} active hazard(s) without completed interventions",
            )
        )
        blockers.append(f"{len(hazard_samples)} active hazard zone(s) without remediation")
        recommendations.append("Complete interventions for all active hazard zones before leasing")
    elif hazard_samples and completed_interventions:
        checks.append(
            _check(
                "no_active_hazards",
                "safety",
                "No active hazard zones for occupants",
                CheckStatus.met,
                CheckSeverity.info,
                "Hazard zones have been remediated",
            )
        )
    else:
        checks.append(
            _check(
                "no_active_hazards",
                "safety",
                "No active hazard zones for occupants",
                CheckStatus.met,
                CheckSeverity.info,
                "No active hazard zones identified",
            )
        )

    # 2. Radon status documented
    radon_samples = [s for s in samples if (s.pollutant_type or "").lower() == "radon"]
    if radon_samples:
        checks.append(
            _check(
                "radon_documented",
                "pollutant",
                "Radon status documented",
                CheckStatus.met,
                CheckSeverity.info,
                f"{len(radon_samples)} radon measurement(s)",
            )
        )
    else:
        checks.append(
            _check(
                "radon_documented",
                "pollutant",
                "Radon status documented",
                CheckStatus.unmet,
                CheckSeverity.warning,
                "No radon measurements found",
            )
        )
        conditions.append("Radon status not documented — measurement recommended for lease")
        recommendations.append("Conduct radon measurement per ORaP Art. 110")

    # 3. Asbestos communicated if present
    asbestos_positive = [s for s in samples if (s.pollutant_type or "").lower() == "asbestos" and s.threshold_exceeded]
    if asbestos_positive:
        # Check if there's documentation (proxy for communication)
        completed = [d for d in diagnostics if d.status in ("completed", "validated")]
        if completed:
            checks.append(
                _check(
                    "asbestos_communicated",
                    "communication",
                    "Asbestos presence communicated",
                    CheckStatus.met,
                    CheckSeverity.info,
                    f"Asbestos documented in {len(completed)} completed diagnostic(s)",
                )
            )
        else:
            checks.append(
                _check(
                    "asbestos_communicated",
                    "communication",
                    "Asbestos presence communicated",
                    CheckStatus.unmet,
                    CheckSeverity.blocker,
                    "Asbestos present but no completed diagnostic to support communication",
                )
            )
            blockers.append("Asbestos found but not formally documented for tenant communication")
            recommendations.append("Complete diagnostic to formally document asbestos presence for tenants")
    else:
        checks.append(
            _check(
                "asbestos_communicated",
                "communication",
                "Asbestos presence communicated",
                CheckStatus.met,
                CheckSeverity.info,
                "No asbestos found — no communication needed",
            )
        )

    return checks, blockers, conditions, recommendations


# ---------------------------------------------------------------------------
# Evaluator dispatch
# ---------------------------------------------------------------------------

_EVALUATORS = {
    TransactionType.sell: _evaluate_sell,
    TransactionType.insure: _evaluate_insure,
    TransactionType.finance: _evaluate_finance,
    TransactionType.lease: _evaluate_lease,
}


# ---------------------------------------------------------------------------
# Score & status computation
# ---------------------------------------------------------------------------


def _compute_score(checks: list[TransactionCheck]) -> float:
    """Compute score as fraction of met checks over total checks."""
    if not checks:
        return 0.0
    met = sum(1 for c in checks if c.status == CheckStatus.met)
    return round(met / len(checks), 4)


def _determine_overall_status(
    checks: list[TransactionCheck],
    blockers: list[str],
) -> OverallStatus:
    """Determine overall status from checks and blockers."""
    if blockers:
        return OverallStatus.not_ready

    has_warning = any(
        c.severity == CheckSeverity.warning and c.status in (CheckStatus.unmet, CheckStatus.partial) for c in checks
    )
    if has_warning:
        return OverallStatus.conditional

    return OverallStatus.ready


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def evaluate_transaction_readiness(
    db: AsyncSession,
    building_id: UUID,
    transaction_type: TransactionType,
) -> TransactionReadiness:
    """
    Evaluate whether a building is ready for a specific transaction type.

    Args:
        db: Async database session.
        building_id: UUID of the building to evaluate.
        transaction_type: One of sell, insure, finance, lease.

    Returns:
        TransactionReadiness result with checks, blockers, conditions, recommendations.

    Raises:
        ValueError: If the building is not found.
    """
    # Verify building exists
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        msg = f"Building {building_id} not found"
        raise ValueError(msg)

    evaluator = _EVALUATORS[transaction_type]
    checks, blockers, conditions, recommendations = await evaluator(db, building_id)

    score = _compute_score(checks)
    overall_status = _determine_overall_status(checks, blockers)

    return TransactionReadiness(
        building_id=building_id,
        transaction_type=transaction_type,
        overall_status=overall_status,
        score=score,
        checks=checks,
        blockers=blockers,
        conditions=conditions,
        recommendations=recommendations,
        evaluated_at=datetime.now(UTC),
    )


async def evaluate_all_transaction_readiness(
    db: AsyncSession,
    building_id: UUID,
) -> list[TransactionReadiness]:
    """
    Evaluate all 4 transaction types for a building.

    Returns:
        List of 4 TransactionReadiness results.
    """
    results: list[TransactionReadiness] = []
    for tx_type in TransactionType:
        result = await evaluate_transaction_readiness(db, building_id, tx_type)
        results.append(result)
    return results


# ---------------------------------------------------------------------------
# Insurance risk tier
# ---------------------------------------------------------------------------

# Weights for insurance risk scoring (higher = riskier)
_INS_WEIGHT_POLLUTANT_DIVERSITY = 0.25
_INS_WEIGHT_THRESHOLD_EXCEEDANCE = 0.30
_INS_WEIGHT_INTERVENTION_COVERAGE = 0.25
_INS_WEIGHT_BUILDING_AGE = 0.20

# Tier boundaries (on 0-1 scale where 0 = safest)
_INS_TIER_BOUNDARIES = [0.25, 0.50, 0.75]  # tier_1 < 0.25 < tier_2 < 0.50 < tier_3 < 0.75 < tier_4


async def compute_insurance_risk_tier(
    db: AsyncSession,
    building_id: UUID,
) -> InsuranceRiskAssessment:
    """
    Compute insurance premium risk tier for a building.

    Factors:
      - Pollutant diversity (number of distinct pollutant types found)
      - Threshold exceedance count
      - Intervention coverage (% of hazards with completed interventions)
      - Building age factor (pre-1990 vs post-1990)

    Returns:
        InsuranceRiskAssessment with tier and component scores.

    Raises:
        ValueError: If the building is not found.
    """
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        msg = f"Building {building_id} not found"
        raise ValueError(msg)

    diagnostics = await _get_diagnostics(db, building_id)
    diag_ids = [d.id for d in diagnostics]
    samples = await _get_samples_for_diagnostics(db, diag_ids)
    interventions = await _get_interventions(db, building_id)

    # 1. Pollutant diversity: how many distinct pollutant types?
    pollutant_types_found = {s.pollutant_type for s in samples if s.pollutant_type}
    pollutant_diversity = len(pollutant_types_found)
    # Normalise: 0 types = 0.0, 5+ types = 1.0
    diversity_score = min(pollutant_diversity / len(ALL_POLLUTANTS), 1.0)

    # 2. Threshold exceedance count
    threshold_exceeded_samples = [s for s in samples if s.threshold_exceeded]
    threshold_exceedance_count = len(threshold_exceeded_samples)
    # Normalise: 0 = 0.0, 10+ = 1.0
    exceedance_score = min(threshold_exceedance_count / 10.0, 1.0)

    # 3. Intervention coverage (inverted: high coverage = low risk)
    hazard_samples = [
        s for s in samples if s.threshold_exceeded and (s.risk_level or "").lower() in ("critical", "high")
    ]
    completed_interventions = [i for i in interventions if i.status == "completed"]
    if hazard_samples:
        coverage = min(len(completed_interventions) / len(hazard_samples), 1.0)
    else:
        coverage = 1.0  # No hazards = full coverage
    intervention_coverage = coverage
    # Invert for risk: high coverage = low risk score
    intervention_risk = 1.0 - coverage

    # 4. Building age factor
    construction_year = building.construction_year
    if construction_year and construction_year >= 1990:
        age_factor = 1.0
        age_risk = 0.0
    else:
        age_factor = 1.5
        age_risk = 1.0

    # Compute weighted raw score (0.0 = safest, 1.0 = riskiest)
    raw_score = round(
        diversity_score * _INS_WEIGHT_POLLUTANT_DIVERSITY
        + exceedance_score * _INS_WEIGHT_THRESHOLD_EXCEEDANCE
        + intervention_risk * _INS_WEIGHT_INTERVENTION_COVERAGE
        + age_risk * _INS_WEIGHT_BUILDING_AGE,
        4,
    )

    # Assign tier
    if raw_score < _INS_TIER_BOUNDARIES[0]:
        tier = InsuranceRiskTier.tier_1
    elif raw_score < _INS_TIER_BOUNDARIES[1]:
        tier = InsuranceRiskTier.tier_2
    elif raw_score < _INS_TIER_BOUNDARIES[2]:
        tier = InsuranceRiskTier.tier_3
    else:
        tier = InsuranceRiskTier.tier_4

    return InsuranceRiskAssessment(
        building_id=building_id,
        risk_tier=tier,
        pollutant_diversity=pollutant_diversity,
        threshold_exceedance_count=threshold_exceedance_count,
        intervention_coverage=round(intervention_coverage, 4),
        building_age_factor=age_factor,
        raw_score=raw_score,
        evaluated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Financing score breakdown
# ---------------------------------------------------------------------------

# Weights for financing sub-scores
_FIN_WEIGHT_DOCUMENTATION = 0.35
_FIN_WEIGHT_RISK_MITIGATION = 0.30
_FIN_WEIGHT_REGULATORY = 0.35


async def compute_financing_score(
    db: AsyncSession,
    building_id: UUID,
) -> FinancingScoreBreakdown:
    """
    Compute detailed financing score with sub-scores.

    Sub-scores:
      - documentation_score: completeness + evidence count
      - risk_mitigation_score: interventions completed / hazards found
      - regulatory_compliance_score: completed diagnostics per pollutant coverage

    Returns:
        FinancingScoreBreakdown with sub-scores and overall score.

    Raises:
        ValueError: If the building is not found.
    """
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        msg = f"Building {building_id} not found"
        raise ValueError(msg)

    # 1. Documentation score (completeness + evidence count)
    completeness = await _get_completeness_score(db, building_id) or 0.0

    # Evidence count: count evidence links related to this building
    evidence_result = await db.execute(
        select(func.count(EvidenceLink.id)).where(
            and_(
                EvidenceLink.source_type == "building",
                EvidenceLink.source_id == building_id,
            )
        )
    )
    evidence_count = evidence_result.scalar() or 0
    # Normalise evidence: 0 = 0.0, 10+ = 1.0
    evidence_norm = min(evidence_count / 10.0, 1.0)
    documentation_score = round((completeness * 0.7 + evidence_norm * 0.3), 4)

    # 2. Risk mitigation score
    diagnostics = await _get_diagnostics(db, building_id)
    diag_ids = [d.id for d in diagnostics]
    samples = await _get_samples_for_diagnostics(db, diag_ids)
    interventions = await _get_interventions(db, building_id)

    hazard_samples = [
        s for s in samples if s.threshold_exceeded and (s.risk_level or "").lower() in ("critical", "high")
    ]
    completed_interventions = [i for i in interventions if i.status == "completed"]

    if hazard_samples:
        risk_mitigation_score = round(min(len(completed_interventions) / len(hazard_samples), 1.0), 4)
    else:
        risk_mitigation_score = 1.0  # No hazards = full mitigation

    # 3. Regulatory compliance score (pollutant coverage)
    completed_diags = [d for d in diagnostics if d.status in ("completed", "validated")]
    pollutants_covered: set[str] = set()
    for s in samples:
        diag = next((d for d in completed_diags if d.id == s.diagnostic_id), None)
        if diag and s.pollutant_type:
            pollutants_covered.add(s.pollutant_type.lower())
    regulatory_compliance_score = round(min(len(pollutants_covered) / len(ALL_POLLUTANTS), 1.0), 4)

    # Overall weighted score
    overall_score = round(
        documentation_score * _FIN_WEIGHT_DOCUMENTATION
        + risk_mitigation_score * _FIN_WEIGHT_RISK_MITIGATION
        + regulatory_compliance_score * _FIN_WEIGHT_REGULATORY,
        4,
    )

    return FinancingScoreBreakdown(
        building_id=building_id,
        documentation_score=documentation_score,
        risk_mitigation_score=risk_mitigation_score,
        regulatory_compliance_score=regulatory_compliance_score,
        overall_score=overall_score,
        evaluated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Comparative readiness
# ---------------------------------------------------------------------------

_COMPARE_MIN_BUILDINGS = 2
_COMPARE_MAX_BUILDINGS = 10


async def compare_transaction_readiness(
    db: AsyncSession,
    building_ids: list[UUID],
) -> list[ComparativeReadiness]:
    """
    Evaluate all 4 transaction types for multiple buildings and return
    a comparative view with rankings per transaction type.

    Args:
        db: Async database session.
        building_ids: 2-10 building UUIDs to compare.

    Returns:
        List of ComparativeReadiness (one per transaction type), each containing
        ranked buildings.

    Raises:
        ValueError: If building count is out of range or any building is not found.
    """
    if len(building_ids) < _COMPARE_MIN_BUILDINGS:
        msg = f"At least {_COMPARE_MIN_BUILDINGS} buildings required for comparison"
        raise ValueError(msg)
    if len(building_ids) > _COMPARE_MAX_BUILDINGS:
        msg = f"At most {_COMPARE_MAX_BUILDINGS} buildings allowed for comparison"
        raise ValueError(msg)

    # Verify all buildings exist
    for bid in building_ids:
        result = await db.execute(select(Building).where(Building.id == bid))
        if result.scalar_one_or_none() is None:
            msg = f"Building {bid} not found"
            raise ValueError(msg)

    # Evaluate all buildings x all transaction types
    all_results: dict[TransactionType, list[TransactionReadiness]] = {tx: [] for tx in TransactionType}
    for bid in building_ids:
        for tx_type in TransactionType:
            r = await evaluate_transaction_readiness(db, bid, tx_type)
            all_results[tx_type].append(r)

    comparisons: list[ComparativeReadiness] = []
    for tx_type in TransactionType:
        # Sort by score descending
        sorted_results = sorted(all_results[tx_type], key=lambda r: r.score, reverse=True)
        rankings = [
            BuildingReadinessRank(
                building_id=r.building_id,
                transaction_type=tx_type,
                score=r.score,
                overall_status=r.overall_status,
                rank=idx + 1,
            )
            for idx, r in enumerate(sorted_results)
        ]
        comparisons.append(
            ComparativeReadiness(
                transaction_type=tx_type,
                rankings=rankings,
            )
        )

    return comparisons


# ---------------------------------------------------------------------------
# Readiness trend
# ---------------------------------------------------------------------------


async def get_readiness_trend(
    db: AsyncSession,
    building_id: UUID,
    transaction_type: TransactionType,
    months: int = 12,
) -> ReadinessTrend:
    """
    Simulate the readiness trend over the past N months.

    Since we don't store historical snapshots, this computes the current
    readiness and projects backward using creation timestamps of diagnostics,
    samples, and interventions to simulate what data was available at each
    monthly interval.

    Args:
        db: Async database session.
        building_id: UUID of the building.
        transaction_type: Transaction type to trend.
        months: Number of months to look back (default 12).

    Returns:
        ReadinessTrend with monthly data points.

    Raises:
        ValueError: If the building is not found.
    """
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        msg = f"Building {building_id} not found"
        raise ValueError(msg)

    now = datetime.now(UTC)
    data_points: list[ReadinessTrendPoint] = []

    # Get all relevant data once
    diagnostics = await _get_diagnostics(db, building_id)
    diag_ids = [d.id for d in diagnostics]
    samples = await _get_samples_for_diagnostics(db, diag_ids)
    interventions = await _get_interventions(db, building_id)

    for i in range(months, -1, -1):
        # Calculate the cutoff date for this month point
        year = now.year
        month = now.month - i
        while month <= 0:
            month += 12
            year -= 1
        # Use first of the month as cutoff (aware datetime)
        cutoff = datetime(year, month, 1, tzinfo=UTC)
        month_label = f"{year:04d}-{month:02d}"

        # Filter data to what existed by cutoff
        available_diags = [d for d in diagnostics if _created_before(d, cutoff)]
        available_diag_ids = {d.id for d in available_diags}
        available_samples = [s for s in samples if s.diagnostic_id in available_diag_ids and _created_before(s, cutoff)]
        available_interventions = [iv for iv in interventions if _created_before(iv, cutoff)]

        # Simulate checks for this time point
        completed_diags = [d for d in available_diags if d.status in ("completed", "validated")]
        hazard_samples = [
            s
            for s in available_samples
            if s.threshold_exceeded and (s.risk_level or "").lower() in ("critical", "high")
        ]
        completed_ivs = [iv for iv in available_interventions if iv.status == "completed"]

        # Build a simplified score based on transaction type
        score, status = _simulate_trend_score(
            transaction_type,
            completed_diags=completed_diags,
            hazard_samples=hazard_samples,
            completed_interventions=completed_ivs,
            all_samples=available_samples,
        )

        data_points.append(
            ReadinessTrendPoint(
                month=month_label,
                score=score,
                overall_status=status,
            )
        )

    return ReadinessTrend(
        building_id=building_id,
        transaction_type=transaction_type,
        data_points=data_points,
    )


def _created_before(obj: object, cutoff: datetime) -> bool:
    """Check if an object was created before the cutoff datetime."""
    created = getattr(obj, "created_at", None)
    if created is None:
        return True  # If no created_at, assume it always existed
    # Make naive datetimes timezone-aware (assume UTC)
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    return created <= cutoff


def _simulate_trend_score(
    transaction_type: TransactionType,
    *,
    completed_diags: list,
    hazard_samples: list,
    completed_interventions: list,
    all_samples: list,
) -> tuple[float, OverallStatus]:
    """
    Compute a simplified score and status for a trend data point.

    This uses a lightweight scoring model (no passport/completeness calls)
    that approximates readiness based on available diagnostic data.
    """
    checks_met = 0
    checks_total = 0
    has_blocker = False

    if transaction_type == TransactionType.sell:
        # Check: has completed diagnostics
        checks_total += 1
        if completed_diags:
            checks_met += 1
        else:
            has_blocker = True
        # Check: no unaddressed hazards
        checks_total += 1
        if not hazard_samples or completed_interventions:
            checks_met += 1
        else:
            has_blocker = True

    elif transaction_type == TransactionType.insure:
        # Check: risk analysis done
        checks_total += 1
        if completed_diags:
            checks_met += 1
        else:
            has_blocker = True
        # Check: hazards addressed
        checks_total += 1
        if not hazard_samples or completed_interventions:
            checks_met += 1
        else:
            has_blocker = True
        # Check: asbestos documented
        checks_total += 1
        asbestos = [s for s in all_samples if (s.pollutant_type or "").lower() == "asbestos"]
        if asbestos or completed_diags:
            checks_met += 1

    elif transaction_type == TransactionType.finance:
        # Check: documentation
        checks_total += 1
        if completed_diags:
            checks_met += 1
        else:
            has_blocker = True
        # Check: risk mitigation
        checks_total += 1
        if not hazard_samples or completed_interventions:
            checks_met += 1

    elif transaction_type == TransactionType.lease:
        # Check: no active hazards
        checks_total += 1
        if not hazard_samples or completed_interventions:
            checks_met += 1
        else:
            has_blocker = True
        # Check: radon documented
        checks_total += 1
        radon = [s for s in all_samples if (s.pollutant_type or "").lower() == "radon"]
        if radon:
            checks_met += 1

    if checks_total == 0:
        return 0.0, OverallStatus.not_ready

    score = round(checks_met / checks_total, 4)

    if has_blocker:
        status = OverallStatus.not_ready
    elif score < 1.0:
        status = OverallStatus.conditional
    else:
        status = OverallStatus.ready

    return score, status
