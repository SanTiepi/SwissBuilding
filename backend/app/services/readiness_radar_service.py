"""
SwissBuildingOS - Readiness Radar Service

Computes a 7-axis readiness radar covering all major "safe_to_X" dimensions
for a building. Each axis is scored 0-100 and graded A-F.

Axes:
  1. safe_to_start   — pollutant readiness (can renovation begin?)
  2. safe_to_sell     — transaction readiness (sell)
  3. safe_to_insure   — insurance readiness
  4. safe_to_finance  — financing readiness
  5. safe_to_renovate — renovation readiness (broader than start)
  6. safe_to_occupy   — occupant safety
  7. safe_to_transfer — handoff/transfer readiness
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import ALL_POLLUTANTS
from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.building_trust_score_v2 import BuildingTrustScore
from app.models.data_quality_issue import DataQualityIssue
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.evidence_link import EvidenceLink
from app.models.intervention import Intervention
from app.models.readiness_assessment import ReadinessAssessment
from app.models.sample import Sample
from app.models.unknown_issue import UnknownIssue

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Grade helpers
# ---------------------------------------------------------------------------

_GRADE_THRESHOLDS = [
    ("A", 85),
    ("B", 70),
    ("C", 55),
    ("D", 40),
    ("E", 25),
]


def _score_to_grade(score: float) -> str:
    """Convert a 0-100 score to A-F grade."""
    for grade, threshold in _GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "F"


# ---------------------------------------------------------------------------
# Axis computations
# ---------------------------------------------------------------------------

_ALL_POLLUTANTS_SET: set[str] = set(ALL_POLLUTANTS)


async def _compute_safe_to_start(db: AsyncSession, building_id: UUID, data: dict) -> dict:
    """Pollutant readiness — can renovation works safely begin?"""
    blockers: list[str] = []
    score = 100.0

    # Check readiness assessment if available
    ra = data.get("readiness_start")
    if ra:
        if ra.status == "blocked":
            score = max(0, (ra.score or 0.0) * 100)
            if ra.blockers_json:
                blockers.extend(b.get("label", str(b)) if isinstance(b, dict) else str(b) for b in ra.blockers_json)
        elif ra.status == "ready":
            score = max(85, (ra.score or 1.0) * 100)
        else:
            score = max(40, (ra.score or 0.5) * 100)
    else:
        # No readiness assessment — check diagnostics
        diags = data.get("diagnostics", [])
        completed = [d for d in diags if d.status in ("completed", "validated")]
        if not completed:
            score -= 50
            blockers.append("No completed diagnostic")
        else:
            # Check pollutant coverage
            covered = set()
            for d in completed:
                samples = data.get("samples_by_diag", {}).get(d.id, [])
                for s in samples:
                    if s.pollutant_type:
                        covered.add(s.pollutant_type)
            missing = _ALL_POLLUTANTS_SET - covered
            if missing:
                score -= len(missing) * 8
                blockers.append(f"Missing pollutant coverage: {', '.join(sorted(missing))}")

    return {
        "name": "safe_to_start",
        "score": max(0, min(100, round(score))),
        "grade": _score_to_grade(max(0, min(100, score))),
        "blockers": blockers,
    }


async def _compute_safe_to_sell(db: AsyncSession, building_id: UUID, data: dict) -> dict:
    """Transaction readiness for sale."""
    blockers: list[str] = []
    score = 100.0

    trust = data.get("trust_score", 0.0)
    completeness = data.get("completeness_score", 0.0)

    # Trust contributes 30 points
    score -= max(0, (1.0 - trust) * 30)

    # Completeness contributes 30 points
    score -= max(0, (1.0 - completeness) * 30)

    # Contradictions penalty
    contradictions = data.get("contradiction_count", 0)
    if contradictions > 0:
        score -= min(20, contradictions * 5)
        blockers.append(f"{contradictions} unresolved contradiction(s)")

    # Open unknowns penalty
    unknowns = data.get("unknown_count", 0)
    if unknowns > 3:
        score -= min(15, (unknowns - 3) * 3)
        blockers.append(f"{unknowns} open unknown(s)")

    # Documents required
    docs = data.get("document_count", 0)
    if docs == 0:
        score -= 10
        blockers.append("No documents uploaded")

    return {
        "name": "safe_to_sell",
        "score": max(0, min(100, round(score))),
        "grade": _score_to_grade(max(0, min(100, score))),
        "blockers": blockers,
    }


async def _compute_safe_to_insure(db: AsyncSession, building_id: UUID, data: dict) -> dict:
    """Insurance readiness."""
    blockers: list[str] = []
    score = 100.0

    # Risk level impacts insurance
    risk_level = data.get("overall_risk_level", "unknown")
    risk_penalty = {"low": 0, "medium": 15, "high": 30, "critical": 50, "unknown": 25}
    score -= risk_penalty.get(risk_level, 25)
    if risk_level in ("high", "critical"):
        blockers.append(f"Overall risk level: {risk_level}")

    # High-risk samples
    high_risk_samples = data.get("high_risk_sample_count", 0)
    if high_risk_samples > 0:
        score -= min(20, high_risk_samples * 4)
        blockers.append(f"{high_risk_samples} high-risk sample(s)")

    # Completed interventions improve score
    completed_interventions = data.get("completed_intervention_count", 0)
    score += min(10, completed_interventions * 2)

    # Trust
    trust = data.get("trust_score", 0.0)
    if trust < 0.5:
        score -= 10
        blockers.append("Trust score below 50%")

    return {
        "name": "safe_to_insure",
        "score": max(0, min(100, round(score))),
        "grade": _score_to_grade(max(0, min(100, score))),
        "blockers": blockers,
    }


async def _compute_safe_to_finance(db: AsyncSession, building_id: UUID, data: dict) -> dict:
    """Bank/financing readiness."""
    blockers: list[str] = []
    score = 100.0

    trust = data.get("trust_score", 0.0)
    completeness = data.get("completeness_score", 0.0)

    # Banks need high trust + completeness
    if trust < 0.6:
        score -= 25
        blockers.append(f"Trust score {trust:.0%} below 60% threshold")
    if completeness < 0.8:
        score -= 20
        blockers.append(f"Completeness {completeness:.0%} below 80% threshold")

    # Evidence count
    evidence_count = data.get("evidence_count", 0)
    if evidence_count < 5:
        score -= 15
        blockers.append("Insufficient evidence links")

    # Contradictions are deal-breakers for banks
    contradictions = data.get("contradiction_count", 0)
    if contradictions > 0:
        score -= contradictions * 10
        blockers.append(f"{contradictions} contradiction(s) — banks require clean data")

    return {
        "name": "safe_to_finance",
        "score": max(0, min(100, round(score))),
        "grade": _score_to_grade(max(0, min(100, score))),
        "blockers": blockers,
    }


async def _compute_safe_to_renovate(db: AsyncSession, building_id: UUID, data: dict) -> dict:
    """Renovation readiness (broader than safe_to_start)."""
    blockers: list[str] = []
    score = 100.0

    # Start with safe_to_start base
    ra = data.get("readiness_start")
    if ra and ra.status == "blocked":
        score -= 30
        blockers.append("Pollutant readiness blocked")

    # Plans / technical documents
    doc_count = data.get("document_count", 0)
    if doc_count < 3:
        score -= 15
        blockers.append("Insufficient technical documentation")

    # Open actions
    open_actions = data.get("open_action_count", 0)
    if open_actions > 5:
        score -= min(20, (open_actions - 5) * 3)
        blockers.append(f"{open_actions} open action(s) to resolve")

    # Completeness
    completeness = data.get("completeness_score", 0.0)
    if completeness < 0.7:
        score -= 20
        blockers.append(f"Completeness {completeness:.0%} below renovation threshold")

    return {
        "name": "safe_to_renovate",
        "score": max(0, min(100, round(score))),
        "grade": _score_to_grade(max(0, min(100, score))),
        "blockers": blockers,
    }


async def _compute_safe_to_occupy(db: AsyncSession, building_id: UUID, data: dict) -> dict:
    """Occupant safety — is it safe for people to be in the building?"""
    blockers: list[str] = []
    score = 100.0

    # High/critical risk samples are occupancy hazards
    high_risk_samples = data.get("high_risk_sample_count", 0)
    critical_samples = data.get("critical_sample_count", 0)
    if critical_samples > 0:
        score -= min(50, critical_samples * 15)
        blockers.append(f"{critical_samples} critical-risk sample(s)")
    if high_risk_samples > 0:
        score -= min(25, high_risk_samples * 5)
        blockers.append(f"{high_risk_samples} high-risk sample(s)")

    # Active interventions = construction zone
    active_interventions = data.get("active_intervention_count", 0)
    if active_interventions > 0:
        score -= min(20, active_interventions * 10)
        blockers.append(f"{active_interventions} active intervention(s) — construction zone")

    # Radon check
    radon_risk = data.get("radon_risk", "unknown")
    if radon_risk in ("high", "critical"):
        score -= 20
        blockers.append(f"Radon risk: {radon_risk}")

    return {
        "name": "safe_to_occupy",
        "score": max(0, min(100, round(score))),
        "grade": _score_to_grade(max(0, min(100, score))),
        "blockers": blockers,
    }


async def _compute_safe_to_transfer(db: AsyncSession, building_id: UUID, data: dict) -> dict:
    """Handoff/transfer readiness — is the building knowledge portable?"""
    blockers: list[str] = []
    score = 100.0

    trust = data.get("trust_score", 0.0)
    completeness = data.get("completeness_score", 0.0)

    # Transfer needs comprehensive documentation
    if completeness < 0.9:
        score -= 30
        blockers.append(f"Completeness {completeness:.0%} below transfer threshold (90%)")
    if trust < 0.7:
        score -= 20
        blockers.append(f"Trust {trust:.0%} below transfer threshold (70%)")

    # Evidence links
    evidence_count = data.get("evidence_count", 0)
    if evidence_count < 10:
        score -= 15
        blockers.append("Insufficient evidence chain for transfer")

    # Open unknowns
    unknowns = data.get("unknown_count", 0)
    if unknowns > 0:
        score -= min(20, unknowns * 4)
        blockers.append(f"{unknowns} unresolved unknown(s)")

    return {
        "name": "safe_to_transfer",
        "score": max(0, min(100, round(score))),
        "grade": _score_to_grade(max(0, min(100, score))),
        "blockers": blockers,
    }


# ---------------------------------------------------------------------------
# Data loader
# ---------------------------------------------------------------------------


async def _load_radar_data(db: AsyncSession, building_id: UUID) -> dict | None:
    """Load all data needed for radar computation."""
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        return None

    data: dict = {"building": building}

    # Trust score
    trust_result = await db.execute(
        select(BuildingTrustScore)
        .where(BuildingTrustScore.building_id == building_id)
        .order_by(BuildingTrustScore.assessed_at.desc())
        .limit(1)
    )
    trust_obj = trust_result.scalar_one_or_none()
    data["trust_score"] = trust_obj.overall_score if trust_obj else 0.0

    # Risk score
    risk_result = await db.execute(select(BuildingRiskScore).where(BuildingRiskScore.building_id == building_id))
    risk_obj = risk_result.scalar_one_or_none()
    data["overall_risk_level"] = risk_obj.overall_risk_level if risk_obj else "unknown"
    data["radon_risk"] = "high" if risk_obj and (risk_obj.radon_probability or 0) > 0.5 else "low"

    # Diagnostics + samples
    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(diag_result.scalars().all())
    data["diagnostics"] = diagnostics

    diag_ids = [d.id for d in diagnostics]
    samples_by_diag: dict = {}
    if diag_ids:
        sample_result = await db.execute(select(Sample).where(Sample.diagnostic_id.in_(diag_ids)))
        all_samples = list(sample_result.scalars().all())
        for s in all_samples:
            samples_by_diag.setdefault(s.diagnostic_id, []).append(s)
        data["high_risk_sample_count"] = sum(1 for s in all_samples if s.risk_level in ("high", "critical"))
        data["critical_sample_count"] = sum(1 for s in all_samples if s.risk_level == "critical")
    else:
        all_samples = []
        data["high_risk_sample_count"] = 0
        data["critical_sample_count"] = 0
    data["samples_by_diag"] = samples_by_diag

    # Readiness assessments
    ra_result = await db.execute(select(ReadinessAssessment).where(ReadinessAssessment.building_id == building_id))
    for ra in ra_result.scalars().all():
        data[f"readiness_{ra.readiness_type.replace('safe_to_', '')}"] = ra

    # Documents
    doc_result = await db.execute(select(func.count()).select_from(Document).where(Document.building_id == building_id))
    data["document_count"] = doc_result.scalar() or 0

    # Evidence links (polymorphic: source_type='building', source_id=building_id)
    evidence_result = await db.execute(
        select(func.count())
        .select_from(EvidenceLink)
        .where(
            and_(
                EvidenceLink.source_type == "building",
                EvidenceLink.source_id == building_id,
            )
        )
    )
    data["evidence_count"] = evidence_result.scalar() or 0

    # Unknowns
    unknown_result = await db.execute(
        select(func.count())
        .select_from(UnknownIssue)
        .where(
            and_(
                UnknownIssue.building_id == building_id,
                UnknownIssue.status == "open",
            )
        )
    )
    data["unknown_count"] = unknown_result.scalar() or 0

    # Contradictions
    contra_result = await db.execute(
        select(func.count())
        .select_from(DataQualityIssue)
        .where(
            and_(
                DataQualityIssue.building_id == building_id,
                DataQualityIssue.issue_type == "contradiction",
                DataQualityIssue.status == "open",
            )
        )
    )
    data["contradiction_count"] = contra_result.scalar() or 0

    # Interventions
    interv_result = await db.execute(select(Intervention).where(Intervention.building_id == building_id))
    interventions = list(interv_result.scalars().all())
    data["completed_intervention_count"] = sum(1 for i in interventions if i.status == "completed")
    data["active_intervention_count"] = sum(1 for i in interventions if i.status in ("in_progress", "planned"))

    # Completeness (simplified — use ratio of non-zero data fields)
    filled = sum(
        1
        for attr in [
            building.construction_year,
            building.building_type,
            building.surface_area_m2,
            building.floors_above,
        ]
        if attr is not None
    )
    base_completeness = filled / 4.0
    # Boost with diagnostics and documents
    if diagnostics:
        base_completeness = min(1.0, base_completeness + 0.2)
    if data["document_count"] > 0:
        base_completeness = min(1.0, base_completeness + 0.1)
    data["completeness_score"] = base_completeness

    # Open actions (from ActionItem if available)
    try:
        from app.models.action_item import ActionItem

        action_result = await db.execute(
            select(func.count())
            .select_from(ActionItem)
            .where(
                and_(
                    ActionItem.building_id == building_id,
                    ActionItem.status.in_(["open", "in_progress"]),
                )
            )
        )
        data["open_action_count"] = action_result.scalar() or 0
    except Exception:
        data["open_action_count"] = 0

    return data


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


_AXIS_COMPUTERS = [
    _compute_safe_to_start,
    _compute_safe_to_sell,
    _compute_safe_to_insure,
    _compute_safe_to_finance,
    _compute_safe_to_renovate,
    _compute_safe_to_occupy,
    _compute_safe_to_transfer,
]


async def compute_readiness_radar(
    db: AsyncSession,
    building_id: UUID,
) -> dict | None:
    """Compute 7-axis readiness radar for a building.

    Returns None if building not found.
    Returns:
        {
            building_id,
            axes: [{name, score, grade, blockers}],
            overall_score,
            overall_grade,
            computed_at,
        }
    """
    data = await _load_radar_data(db, building_id)
    if data is None:
        return None

    axes = []
    for compute_fn in _AXIS_COMPUTERS:
        axis = await compute_fn(db, building_id, data)
        axes.append(axis)

    scores = [a["score"] for a in axes]
    overall_score = round(sum(scores) / len(scores)) if scores else 0
    overall_grade = _score_to_grade(overall_score)

    return {
        "building_id": str(building_id),
        "axes": axes,
        "overall_score": overall_score,
        "overall_grade": overall_grade,
        "computed_at": datetime.now(UTC).isoformat(),
    }
