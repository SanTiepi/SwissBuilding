"""
BatiConnect - Compliance Scanner Service

Proactive compliance scanning: full compliance audit, regulatory deadline
calculation, and anomaly detection for buildings. Turns the passive
compliance_engine.py into an active scanner.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.obligation import Obligation
from app.models.sample import Sample

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regulatory reference table
# ---------------------------------------------------------------------------

_REGULATORY_RULES: list[dict[str, Any]] = [
    {
        "rule": "OTConst Art. 82",
        "article": "Art. 82",
        "description": "Asbestos analysis required before any renovation works on buildings constructed before 1990",
        "pollutant": "asbestos",
        "construction_year_max": 1990,
    },
    {
        "rule": "ORRChim Annexe 2.15",
        "article": "Annexe 2.15",
        "description": "PCB analysis required for buildings constructed 1955-1975 (joint sealants, capacitors)",
        "pollutant": "pcb",
        "construction_year_min": 1955,
        "construction_year_max": 1975,
    },
    {
        "rule": "ORRChim Annexe 2.18",
        "article": "Annexe 2.18",
        "description": "Lead paint analysis required for buildings with pre-1960 paint",
        "pollutant": "lead",
        "construction_year_max": 1960,
    },
    {
        "rule": "ORaP Art. 110",
        "article": "Art. 110",
        "description": "Radon measurement obligatory in radon-prone areas or buildings with basement occupancy",
        "pollutant": "radon",
    },
    {
        "rule": "OLED",
        "article": "Annexe 5",
        "description": "Waste classification required for all pollutant-positive materials before disposal",
        "pollutant": None,
    },
    {
        "rule": "OTConst Art. 60a",
        "article": "Art. 60a",
        "description": "Complete pollutant diagnostic required before any demolition or renovation",
        "pollutant": None,
        "construction_year_max": 1990,
    },
]

# Asbestos high-risk period
_ASBESTOS_YEAR_MIN = 1920
_ASBESTOS_YEAR_MAX = 1990

# PCB high-risk period
_PCB_YEAR_MIN = 1955
_PCB_YEAR_MAX = 1975

# Lead paint period
_LEAD_YEAR_MAX = 1960

# HAP high-risk period
_HAP_YEAR_MIN = 1950
_HAP_YEAR_MAX = 1980

# Diagnostic validity (years)
_DIAGNOSTIC_VALIDITY_YEARS = 5

# Grade thresholds
_GRADE_THRESHOLDS = {
    "A": 90,
    "B": 75,
    "C": 60,
    "D": 40,
    "E": 20,
    "F": 0,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def scan_building_compliance(db: AsyncSession, building_id: UUID) -> dict[str, Any]:
    """Full compliance scan for a building.

    Returns:
        Dict with keys: non_conformities, upcoming_obligations,
        missing_diagnostics, score (0-100), grade (A-F).
    """
    data = await _load_building_data(db, building_id)
    if data is None:
        raise ValueError(f"Building {building_id} not found")

    non_conformities = _check_non_conformities(data)
    upcoming = await _get_upcoming_obligations(db, building_id)
    missing = _detect_missing_diagnostics(data)
    anomalies = _detect_anomalies(data)

    # Score: start at 100, deduct for issues
    score = 100
    for nc in non_conformities:
        deduction = {"critical": 20, "high": 10, "medium": 5, "low": 2}.get(nc["severity"], 5)
        score -= deduction
    for m in missing:
        deduction = {"critical": 15, "high": 10, "medium": 5}.get(m["urgency"], 5)
        score -= deduction
    for a in anomalies:
        deduction = {"critical": 15, "high": 10, "medium": 5}.get(a["urgency"], 5)
        score -= deduction
    score = max(0, min(100, score))

    grade = _score_to_grade(score)

    return {
        "building_id": str(building_id),
        "non_conformities": non_conformities,
        "upcoming_obligations": upcoming,
        "missing_diagnostics": missing,
        "score": score,
        "grade": grade,
        "scanned_at": datetime.utcnow().isoformat(),
    }


async def compute_regulatory_deadlines(db: AsyncSession, building_id: UUID) -> list[dict[str, Any]]:
    """Calculate all applicable regulatory deadlines for a building.

    Returns:
        List of dicts: rule, article, deadline, status, description.
    """
    data = await _load_building_data(db, building_id)
    if data is None:
        raise ValueError(f"Building {building_id} not found")

    building: Building = data["building"]
    diagnostics: list[Diagnostic] = data["diagnostics"]
    obligations: list[Obligation] = data["obligations"]

    deadlines: list[dict[str, Any]] = []
    today = date.today()
    construction_year = building.construction_year or 0

    # 1. Asbestos analysis before works (OTConst Art. 82)
    if construction_year <= _ASBESTOS_YEAR_MAX:
        has_asbestos_diag = any(
            d.status in ("completed", "validated")
            and any((s.pollutant_type or "").lower() == "asbestos" for s in data["samples"] if s.diagnostic_id == d.id)
            for d in diagnostics
        )
        deadlines.append(
            {
                "rule": "OTConst Art. 82",
                "article": "Art. 82",
                "deadline": None,
                "status": "met" if has_asbestos_diag else "required_before_works",
                "description": "Asbestos analysis required before any renovation or demolition works",
            }
        )

    # 2. PCB check (ORRChim)
    if _PCB_YEAR_MIN <= construction_year <= _PCB_YEAR_MAX:
        has_pcb_diag = any(
            d.status in ("completed", "validated")
            and any((s.pollutant_type or "").lower() == "pcb" for s in data["samples"] if s.diagnostic_id == d.id)
            for d in diagnostics
        )
        deadlines.append(
            {
                "rule": "ORRChim Annexe 2.15",
                "article": "Annexe 2.15",
                "deadline": None,
                "status": "met" if has_pcb_diag else "required_before_works",
                "description": "PCB analysis required for buildings from 1955-1975 period",
            }
        )

    # 3. Lead check (ORRChim)
    if construction_year <= _LEAD_YEAR_MAX and construction_year > 0:
        has_lead_diag = any(
            d.status in ("completed", "validated")
            and any((s.pollutant_type or "").lower() == "lead" for s in data["samples"] if s.diagnostic_id == d.id)
            for d in diagnostics
        )
        deadlines.append(
            {
                "rule": "ORRChim Annexe 2.18",
                "article": "Annexe 2.18",
                "deadline": None,
                "status": "met" if has_lead_diag else "recommended",
                "description": "Lead paint analysis recommended for pre-1960 buildings",
            }
        )

    # 4. Radon measurement (ORaP)
    has_basement = (building.floors_below or 0) > 0
    if has_basement:
        has_radon = any(
            d.status in ("completed", "validated")
            and any((s.pollutant_type or "").lower() == "radon" for s in data["samples"] if s.diagnostic_id == d.id)
            for d in diagnostics
        )
        deadlines.append(
            {
                "rule": "ORaP Art. 110",
                "article": "Art. 110",
                "deadline": None,
                "status": "met" if has_radon else "recommended",
                "description": "Radon measurement recommended for buildings with basement spaces",
            }
        )

    # 5. Waste classification for positive samples (OLED)
    positive_samples = [s for s in data["samples"] if s.threshold_exceeded]
    unclassified = [s for s in positive_samples if not s.waste_disposal_type]
    if positive_samples:
        deadlines.append(
            {
                "rule": "OLED",
                "article": "Annexe 5",
                "deadline": None,
                "status": "met" if not unclassified else "non_conformity",
                "description": (
                    f"{len(unclassified)} positive sample(s) missing waste classification"
                    if unclassified
                    else "All positive samples have waste classification"
                ),
            }
        )

    # 6. Obligation-based deadlines
    for obl in obligations:
        if obl.status in ("upcoming", "due_soon", "overdue"):
            days_remaining = (obl.due_date - today).days if obl.due_date else None
            status = "overdue" if days_remaining is not None and days_remaining < 0 else "upcoming"
            if days_remaining is not None and 0 <= days_remaining <= 30:
                status = "due_soon"
            deadlines.append(
                {
                    "rule": obl.obligation_type,
                    "article": None,
                    "deadline": obl.due_date.isoformat() if obl.due_date else None,
                    "status": status,
                    "description": obl.title,
                }
            )

    return deadlines


async def detect_regulatory_anomalies(db: AsyncSession, building_id: UUID) -> list[dict[str, Any]]:
    """Find regulatory anomalies — buildings that SHOULD have certain diagnostics but don't.

    Returns:
        List of dicts: anomaly_type, description, urgency, recommended_action.
    """
    data = await _load_building_data(db, building_id)
    if data is None:
        raise ValueError(f"Building {building_id} not found")

    return _detect_anomalies(data)


# ---------------------------------------------------------------------------
# Internal data loading
# ---------------------------------------------------------------------------


async def _load_building_data(db: AsyncSession, building_id: UUID) -> dict[str, Any] | None:
    """Load all data needed for compliance scanning."""
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        return None

    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(diag_result.scalars().all())

    samples: list[Sample] = []
    if diagnostics:
        diag_ids = [d.id for d in diagnostics]
        sample_result = await db.execute(select(Sample).where(Sample.diagnostic_id.in_(diag_ids)))
        samples = list(sample_result.scalars().all())

    doc_result = await db.execute(select(Document).where(Document.building_id == building_id))
    documents = list(doc_result.scalars().all())

    intervention_result = await db.execute(select(Intervention).where(Intervention.building_id == building_id))
    interventions = list(intervention_result.scalars().all())

    obligation_result = await db.execute(select(Obligation).where(Obligation.building_id == building_id))
    obligations = list(obligation_result.scalars().all())

    return {
        "building": building,
        "diagnostics": diagnostics,
        "samples": samples,
        "documents": documents,
        "interventions": interventions,
        "obligations": obligations,
    }


# ---------------------------------------------------------------------------
# Non-conformity checks
# ---------------------------------------------------------------------------


def _check_non_conformities(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Check for current non-conformities."""
    non_conformities: list[dict[str, Any]] = []
    building: Building = data["building"]
    diagnostics: list[Diagnostic] = data["diagnostics"]
    samples: list[Sample] = data["samples"]
    construction_year = building.construction_year or 0

    completed_diags = [d for d in diagnostics if d.status in ("completed", "validated")]

    # 1. Positive asbestos without SUVA notification
    has_positive_asbestos = any(
        (s.pollutant_type or "").lower() == "asbestos" and s.threshold_exceeded for s in samples
    )
    if has_positive_asbestos:
        notified = any(d.suva_notification_required and d.suva_notification_date for d in diagnostics)
        if not notified:
            non_conformities.append(
                {
                    "rule": "OTConst Art. 82-86",
                    "description": "Positive asbestos detected but SUVA notification not filed",
                    "severity": "critical",
                    "reference": "OTConst Art. 82-86, CFST 6503",
                }
            )

    # 2. Positive samples without waste classification
    positive_samples = [s for s in samples if s.threshold_exceeded]
    unclassified = [s for s in positive_samples if not s.waste_disposal_type]
    if unclassified:
        non_conformities.append(
            {
                "rule": "OLED",
                "description": f"{len(unclassified)} positive sample(s) missing waste disposal classification",
                "severity": "high",
                "reference": "OLED Annexe 5",
            }
        )

    # 3. Asbestos samples without CFST work category
    asbestos_positive = [s for s in samples if (s.pollutant_type or "").lower() == "asbestos" and s.threshold_exceeded]
    missing_cfst = [s for s in asbestos_positive if not s.cfst_work_category]
    if missing_cfst:
        non_conformities.append(
            {
                "rule": "CFST 6503",
                "description": f"{len(missing_cfst)} asbestos sample(s) missing CFST work category classification",
                "severity": "high",
                "reference": "CFST 6503",
            }
        )

    # 4. Outdated diagnostics (>5 years)
    now = datetime.utcnow()
    for diag in completed_diags:
        diag_date = diag.date_inspection or (diag.created_at.date() if diag.created_at else None)
        if diag_date is not None:
            if hasattr(diag_date, "date"):
                diag_date = diag_date.date()
            age_days = (now.date() - diag_date).days
            if age_days > _DIAGNOSTIC_VALIDITY_YEARS * 365:
                non_conformities.append(
                    {
                        "rule": "Best practice",
                        "description": f"Diagnostic from {diag_date} is {age_days // 365} years old — requalification recommended",
                        "severity": "medium",
                        "reference": "Professional best practice (5-year validity)",
                    }
                )
                break  # Report only once

    # 5. Building pre-1990 without any completed diagnostic
    if construction_year <= _ASBESTOS_YEAR_MAX and construction_year > 0 and not completed_diags:
        non_conformities.append(
            {
                "rule": "OTConst Art. 60a",
                "description": "Pre-1990 building has no completed pollutant diagnostic",
                "severity": "critical",
                "reference": "OTConst Art. 60a",
            }
        )

    return non_conformities


# ---------------------------------------------------------------------------
# Missing diagnostics detection
# ---------------------------------------------------------------------------


def _detect_missing_diagnostics(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Detect pollutants that should have been tested but weren't."""
    missing: list[dict[str, Any]] = []
    building: Building = data["building"]
    samples: list[Sample] = data["samples"]
    construction_year = building.construction_year or 0

    evaluated_pollutants = {(s.pollutant_type or "").lower() for s in samples}

    # Asbestos: mandatory for pre-1990
    if construction_year <= _ASBESTOS_YEAR_MAX and construction_year > 0 and "asbestos" not in evaluated_pollutants:
        missing.append(
            {
                "pollutant": "asbestos",
                "reason": f"Building from {construction_year} (pre-1990) requires asbestos analysis",
                "urgency": "critical",
            }
        )

    # PCB: recommended for 1955-1975
    if _PCB_YEAR_MIN <= construction_year <= _PCB_YEAR_MAX and "pcb" not in evaluated_pollutants:
        missing.append(
            {
                "pollutant": "pcb",
                "reason": f"Building from {construction_year} (1955-1975 period) should have PCB analysis",
                "urgency": "high",
            }
        )

    # Lead: recommended for pre-1960
    if construction_year <= _LEAD_YEAR_MAX and construction_year > 0 and "lead" not in evaluated_pollutants:
        missing.append(
            {
                "pollutant": "lead",
                "reason": f"Building from {construction_year} (pre-1960) should have lead paint analysis",
                "urgency": "medium",
            }
        )

    # HAP: recommended for 1950-1980
    if _HAP_YEAR_MIN <= construction_year <= _HAP_YEAR_MAX and "hap" not in evaluated_pollutants:
        missing.append(
            {
                "pollutant": "hap",
                "reason": f"Building from {construction_year} (1950-1980) should have HAP analysis",
                "urgency": "medium",
            }
        )

    # Radon: recommended if basement
    has_basement = (building.floors_below or 0) > 0
    if has_basement and "radon" not in evaluated_pollutants:
        missing.append(
            {
                "pollutant": "radon",
                "reason": "Building has basement — radon measurement recommended",
                "urgency": "medium",
            }
        )

    return missing


# ---------------------------------------------------------------------------
# Anomaly detection
# ---------------------------------------------------------------------------


def _detect_anomalies(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Find buildings that SHOULD have certain diagnostics but don't."""
    anomalies: list[dict[str, Any]] = []
    building: Building = data["building"]
    samples: list[Sample] = data["samples"]
    diagnostics: list[Diagnostic] = data["diagnostics"]
    construction_year = building.construction_year or 0

    evaluated_pollutants = {(s.pollutant_type or "").lower() for s in samples}
    completed_diags = [d for d in diagnostics if d.status in ("completed", "validated")]

    # 1. Built 1960-1990 without asbestos diagnostic
    if _ASBESTOS_YEAR_MIN < construction_year <= _ASBESTOS_YEAR_MAX and "asbestos" not in evaluated_pollutants:
        anomalies.append(
            {
                "anomaly_type": "missing_asbestos_diagnostic",
                "description": f"Building from {construction_year} has no asbestos diagnostic (high-risk period)",
                "urgency": "critical",
                "recommended_action": "Commission asbestos diagnostic before any renovation works",
            }
        )

    # 2. Built 1955-1975 without PCB check
    if _PCB_YEAR_MIN <= construction_year <= _PCB_YEAR_MAX and "pcb" not in evaluated_pollutants:
        anomalies.append(
            {
                "anomaly_type": "missing_pcb_diagnostic",
                "description": f"Building from {construction_year} has no PCB analysis (peak usage period)",
                "urgency": "high",
                "recommended_action": "Commission PCB analysis focusing on joint sealants and capacitors",
            }
        )

    # 3. Basement without radon measurement
    has_basement = (building.floors_below or 0) > 0
    if has_basement and "radon" not in evaluated_pollutants:
        anomalies.append(
            {
                "anomaly_type": "missing_radon_measurement",
                "description": "Building has basement spaces but no radon measurement recorded",
                "urgency": "high",
                "recommended_action": "Install radon dosimeters in basement/ground-floor occupied spaces",
            }
        )

    # 4. Positive samples with no planned intervention
    positive_high = [
        s for s in samples if s.threshold_exceeded and (s.risk_level or "").lower() in ("high", "critical")
    ]
    interventions: list[Intervention] = data["interventions"]
    has_remediation = any(i.status in ("planned", "in_progress", "completed") for i in interventions)
    if positive_high and not has_remediation:
        anomalies.append(
            {
                "anomaly_type": "unaddressed_high_risk",
                "description": f"{len(positive_high)} high/critical risk sample(s) with no planned remediation",
                "urgency": "critical",
                "recommended_action": "Plan remediation interventions for high-risk positive samples",
            }
        )

    # 5. Diagnostic completed but no report uploaded
    for diag in completed_diags:
        if not diag.report_file_path:
            anomalies.append(
                {
                    "anomaly_type": "missing_diagnostic_report",
                    "description": f"Diagnostic completed but no report uploaded (diagnostic {diag.id})",
                    "urgency": "medium",
                    "recommended_action": "Upload the diagnostic report for traceability",
                }
            )
            break  # Report only once

    return anomalies


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_upcoming_obligations(db: AsyncSession, building_id: UUID) -> list[dict[str, Any]]:
    """Get upcoming obligations sorted by due date."""
    today = date.today()
    result = await db.execute(
        select(Obligation)
        .where(
            Obligation.building_id == building_id,
            Obligation.status.in_(["upcoming", "due_soon", "overdue"]),
        )
        .order_by(Obligation.due_date)
    )
    obligations = result.scalars().all()

    upcoming: list[dict[str, Any]] = []
    for obl in obligations:
        days_remaining = (obl.due_date - today).days if obl.due_date else None
        upcoming.append(
            {
                "type": obl.obligation_type,
                "title": obl.title,
                "deadline": obl.due_date.isoformat() if obl.due_date else None,
                "days_remaining": days_remaining,
                "priority": obl.priority,
                "status": obl.status,
            }
        )
    return upcoming


def _score_to_grade(score: int) -> str:
    """Convert numeric score to A-F grade."""
    for grade, threshold in _GRADE_THRESHOLDS.items():
        if score >= threshold:
            return grade
    return "F"
