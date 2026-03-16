"""
SwissBuildingOS - Readiness Reasoner Service

Evaluates whether a building is ready for regulatory milestones:
  - safe_to_start: can renovation works safely begin?
  - safe_to_tender: can tender documents be prepared?
  - safe_to_reopen: can the building be reoccupied after works?
  - safe_to_requalify: should a new diagnostic be triggered?

Unlike the completeness engine (dossier completeness scoring), this service
is the regulatory layer that answers go/no-go questions based on actual
Swiss regulatory requirements, jurisdiction-specific rules, and building data.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import ALL_POLLUTANTS
from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.readiness_assessment import ReadinessAssessment
from app.models.sample import Sample
from app.models.zone import Zone
from app.schemas.readiness import _derive_prework_triggers
from app.services.rule_resolver import resolve_cantonal_requirements

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

READINESS_TYPES = ("safe_to_start", "safe_to_tender", "safe_to_reopen", "safe_to_requalify")

_ALL_POLLUTANTS_SET: set[str] = set(ALL_POLLUTANTS)

# Default diagnostic validity period (years)
DIAGNOSTIC_VALIDITY_YEARS = 5

# ---------------------------------------------------------------------------
# Check result helpers
# ---------------------------------------------------------------------------


def _check(
    check_id: str,
    label: str,
    status: str,
    *,
    legal_basis: str | None = None,
    detail: str | None = None,
    required: bool = True,
) -> dict[str, Any]:
    """Build a single check dict for checks_json."""
    return {
        "id": check_id,
        "label": label,
        "status": status,
        "legal_basis": legal_basis,
        "detail": detail,
        "required": required,
    }


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


async def _load_building_data(db: AsyncSession, building_id: UUID) -> dict[str, Any] | None:
    """Load all data needed for readiness evaluation in a single pass."""
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

    action_result = await db.execute(select(ActionItem).where(ActionItem.building_id == building_id))
    actions = list(action_result.scalars().all())

    intervention_result = await db.execute(select(Intervention).where(Intervention.building_id == building_id))
    interventions = list(intervention_result.scalars().all())

    zone_result = await db.execute(select(Zone).where(Zone.building_id == building_id))
    zones = list(zone_result.scalars().all())

    return {
        "building": building,
        "diagnostics": diagnostics,
        "samples": samples,
        "documents": documents,
        "actions": actions,
        "interventions": interventions,
        "zones": zones,
    }


# ---------------------------------------------------------------------------
# safe_to_start checks
# ---------------------------------------------------------------------------


async def _evaluate_safe_to_start(
    db: AsyncSession,
    data: dict[str, Any],
) -> tuple[list[dict], list[str], list[str]]:
    """Evaluate all checks for safe_to_start readiness."""
    checks: list[dict] = []
    blockers: list[str] = []
    conditions: list[str] = []

    building: Building = data["building"]
    diagnostics: list[Diagnostic] = data["diagnostics"]
    samples: list[Sample] = data["samples"]
    documents: list[Document] = data["documents"]
    actions: list[ActionItem] = data["actions"]

    # 1. Completed diagnostic with all pollutants evaluated
    completed_diags = [d for d in diagnostics if d.status in ("completed", "validated")]
    if completed_diags:
        checks.append(
            _check(
                "completed_diagnostic",
                "Completed diagnostic available",
                "pass",
                legal_basis="OTConst Art. 60a",
                detail=f"{len(completed_diags)} completed diagnostic(s)",
            )
        )
    else:
        checks.append(
            _check(
                "completed_diagnostic",
                "Completed diagnostic available",
                "fail",
                legal_basis="OTConst Art. 60a",
                detail="No completed or validated diagnostic",
            )
        )
        blockers.append("No completed or validated diagnostic found")

    # 2. All pollutants evaluated
    evaluated_pollutants = {(s.pollutant_type or "").lower() for s in samples} & _ALL_POLLUTANTS_SET
    if evaluated_pollutants == _ALL_POLLUTANTS_SET:
        checks.append(
            _check(
                "all_pollutants_evaluated",
                "All pollutants evaluated",
                "pass",
                detail="All 5 pollutant types covered",
            )
        )
    else:
        missing = _ALL_POLLUTANTS_SET - evaluated_pollutants
        checks.append(
            _check(
                "all_pollutants_evaluated",
                "All pollutants evaluated",
                "fail",
                detail=f"Missing: {', '.join(sorted(missing))}",
            )
        )
        blockers.append(f"Missing pollutant evaluation: {', '.join(sorted(missing))}")

    # 3. Positive samples have risk_level and action_required
    positive_samples = [s for s in samples if s.threshold_exceeded]
    if positive_samples:
        missing_risk = [s for s in positive_samples if not s.risk_level]
        missing_action = [s for s in positive_samples if not s.action_required]
        if not missing_risk and not missing_action:
            checks.append(
                _check(
                    "positive_samples_classified",
                    "Positive samples fully classified",
                    "pass",
                    detail=f"{len(positive_samples)} positive sample(s) classified",
                )
            )
        else:
            details = []
            if missing_risk:
                details.append(f"{len(missing_risk)} missing risk_level")
            if missing_action:
                details.append(f"{len(missing_action)} missing action_required")
            checks.append(
                _check(
                    "positive_samples_classified",
                    "Positive samples fully classified",
                    "fail",
                    detail="; ".join(details),
                )
            )
            blockers.append(f"Positive samples not fully classified: {'; '.join(details)}")
    else:
        checks.append(
            _check(
                "positive_samples_classified",
                "Positive samples fully classified",
                "not_applicable",
                detail="No positive samples",
            )
        )

    # 4. SUVA notification (if asbestos positive)
    has_positive_asbestos = any(
        (s.pollutant_type or "").lower() == "asbestos" and s.threshold_exceeded for s in samples
    )
    if has_positive_asbestos:
        notified = any(d.suva_notification_required and d.suva_notification_date for d in diagnostics)
        if notified:
            checks.append(
                _check(
                    "suva_notification",
                    "SUVA notification filed",
                    "pass",
                    legal_basis="OTConst Art. 82-86",
                    detail="SUVA notified",
                )
            )
        else:
            checks.append(
                _check(
                    "suva_notification",
                    "SUVA notification filed",
                    "fail",
                    legal_basis="OTConst Art. 82-86",
                    detail="SUVA notification required but not filed",
                )
            )
            blockers.append("SUVA notification required for asbestos but not filed")
    else:
        checks.append(
            _check(
                "suva_notification",
                "SUVA notification filed",
                "not_applicable",
                legal_basis="OTConst Art. 82-86",
                detail="No positive asbestos samples",
            )
        )

    # 5. CFST work category determined (if asbestos positive)
    if has_positive_asbestos:
        asbestos_positive = [
            s for s in samples if (s.pollutant_type or "").lower() == "asbestos" and s.threshold_exceeded
        ]
        missing_cfst = [s for s in asbestos_positive if not s.cfst_work_category]
        if not missing_cfst:
            checks.append(
                _check(
                    "cfst_work_category",
                    "CFST work category determined",
                    "pass",
                    legal_basis="CFST 6503",
                    detail="Work category set for all asbestos materials",
                )
            )
        else:
            checks.append(
                _check(
                    "cfst_work_category",
                    "CFST work category determined",
                    "fail",
                    legal_basis="CFST 6503",
                    detail=f"{len(missing_cfst)} asbestos sample(s) missing work category",
                )
            )
            blockers.append(f"{len(missing_cfst)} asbestos sample(s) missing CFST work category")
    else:
        checks.append(
            _check(
                "cfst_work_category",
                "CFST work category determined",
                "not_applicable",
                legal_basis="CFST 6503",
                detail="No positive asbestos samples",
            )
        )

    # 6. Waste disposal classified for all positive samples
    if positive_samples:
        missing_waste = [s for s in positive_samples if not s.waste_disposal_type]
        if not missing_waste:
            checks.append(
                _check(
                    "waste_classified",
                    "Waste disposal classified",
                    "pass",
                    legal_basis="OLED",
                    detail="All positive samples have waste classification",
                )
            )
        else:
            checks.append(
                _check(
                    "waste_classified",
                    "Waste disposal classified",
                    "fail",
                    legal_basis="OLED",
                    detail=f"{len(missing_waste)} positive sample(s) missing waste classification",
                )
            )
            blockers.append(f"{len(missing_waste)} positive sample(s) missing waste disposal classification")
    else:
        checks.append(
            _check(
                "waste_classified",
                "Waste disposal classified",
                "not_applicable",
                legal_basis="OLED",
                detail="No positive samples",
            )
        )

    # 7. No open critical/high priority actions
    critical_open = [a for a in actions if a.status == "open" and a.priority in ("critical", "high")]
    if not critical_open:
        checks.append(
            _check(
                "no_critical_actions",
                "No open critical/high actions",
                "pass",
                detail="No open critical/high priority actions",
            )
        )
    else:
        checks.append(
            _check(
                "no_critical_actions",
                "No open critical/high actions",
                "fail",
                detail=f"{len(critical_open)} open critical/high action(s)",
            )
        )
        blockers.append(f"{len(critical_open)} open critical/high priority action(s)")

    # 8. Diagnostic report uploaded (conditional)
    reports = [d for d in documents if (d.document_type or "").lower() in ("diagnostic_report", "report")]
    if reports:
        checks.append(
            _check(
                "diagnostic_report",
                "Diagnostic report uploaded",
                "pass",
                detail=f"{len(reports)} report(s) available",
                required=False,
            )
        )
    else:
        checks.append(
            _check(
                "diagnostic_report",
                "Diagnostic report uploaded",
                "conditional",
                detail="No diagnostic report uploaded",
                required=False,
            )
        )
        conditions.append("Diagnostic report not yet uploaded")

    # 9. Cantonal form submitted (conditional, jurisdiction-dependent)
    cantonal_reqs = await resolve_cantonal_requirements(db, building.jurisdiction_id)
    if cantonal_reqs and cantonal_reqs.get("form_name"):
        canton_notified = any(d.canton_notification_date for d in diagnostics)
        if canton_notified:
            checks.append(
                _check(
                    "cantonal_form",
                    f"Cantonal form submitted ({cantonal_reqs['form_name']})",
                    "pass",
                    detail="Cantonal notification sent",
                    required=False,
                )
            )
        else:
            checks.append(
                _check(
                    "cantonal_form",
                    f"Cantonal form submitted ({cantonal_reqs['form_name']})",
                    "conditional",
                    detail=f"Cantonal form '{cantonal_reqs['form_name']}' not submitted",
                    required=False,
                )
            )
            conditions.append(f"Cantonal form '{cantonal_reqs['form_name']}' not yet submitted")
    else:
        checks.append(
            _check(
                "cantonal_form",
                "Cantonal form submitted",
                "not_applicable",
                detail="No jurisdiction-specific form requirement",
                required=False,
            )
        )

    return checks, blockers, conditions


# ---------------------------------------------------------------------------
# safe_to_tender checks
# ---------------------------------------------------------------------------


async def _evaluate_safe_to_tender(
    db: AsyncSession,
    data: dict[str, Any],
) -> tuple[list[dict], list[str], list[str]]:
    """Evaluate all checks for safe_to_tender readiness."""
    checks: list[dict] = []
    blockers: list[str] = []
    conditions: list[str] = []

    building: Building = data["building"]
    documents: list[Document] = data["documents"]
    actions: list[ActionItem] = data["actions"]
    zones: list[Zone] = data["zones"]

    # 1. Diagnostic report available
    reports = [d for d in documents if (d.document_type or "").lower() in ("diagnostic_report", "report")]
    if reports:
        checks.append(
            _check(
                "diagnostic_report",
                "Diagnostic report available",
                "pass",
                detail=f"{len(reports)} report(s) available",
            )
        )
    else:
        checks.append(
            _check(
                "diagnostic_report",
                "Diagnostic report available",
                "fail",
                detail="No diagnostic report uploaded",
            )
        )
        blockers.append("No diagnostic report available for tender preparation")

    # 2. Waste elimination plan (if required by canton)
    cantonal_reqs = await resolve_cantonal_requirements(db, building.jurisdiction_id)
    requires_wep = False
    if cantonal_reqs and cantonal_reqs.get("requires_waste_elimination_plan"):
        requires_wep = True

    if requires_wep:
        wep_docs = [
            d
            for d in documents
            if (d.document_type or "").lower() in ("waste_elimination_plan", "ped", "plan_elimination")
        ]
        if wep_docs:
            checks.append(
                _check(
                    "waste_elimination_plan",
                    "Waste elimination plan",
                    "pass",
                    detail="Waste elimination plan document available",
                )
            )
        else:
            checks.append(
                _check(
                    "waste_elimination_plan",
                    "Waste elimination plan",
                    "fail",
                    detail="Waste elimination plan required by canton but not uploaded",
                )
            )
            blockers.append("Waste elimination plan required by canton but not uploaded")
    else:
        checks.append(
            _check(
                "waste_elimination_plan",
                "Waste elimination plan",
                "not_applicable",
                detail="Not required by jurisdiction",
            )
        )

    # 3. Cost estimation / action items assigned
    active_actions = [a for a in actions if a.status in ("open", "in_progress")]
    if active_actions:
        checks.append(
            _check(
                "cost_estimation",
                "Action items assigned for cost scoping",
                "pass",
                detail=f"{len(active_actions)} active action(s) for work scoping",
            )
        )
    else:
        checks.append(
            _check(
                "cost_estimation",
                "Action items assigned for cost scoping",
                "fail",
                detail="No active action items for work scoping",
            )
        )
        blockers.append("No action items available for cost estimation")

    # 4. Zones mapped for work scoping (conditional)
    if zones:
        checks.append(
            _check(
                "zones_mapped",
                "Zones mapped for work scoping",
                "pass",
                detail=f"{len(zones)} zone(s) mapped",
                required=False,
            )
        )
    else:
        checks.append(
            _check(
                "zones_mapped",
                "Zones mapped for work scoping",
                "conditional",
                detail="No zones mapped for work scoping",
                required=False,
            )
        )
        conditions.append("No zones mapped — work scoping may be less precise")

    return checks, blockers, conditions


# ---------------------------------------------------------------------------
# safe_to_reopen checks
# ---------------------------------------------------------------------------


async def _evaluate_safe_to_reopen(
    db: AsyncSession,
    data: dict[str, Any],
) -> tuple[list[dict], list[str], list[str]]:
    """Evaluate all checks for safe_to_reopen readiness."""
    checks: list[dict] = []
    blockers: list[str] = []
    conditions: list[str] = []

    samples: list[Sample] = data["samples"]
    documents: list[Document] = data["documents"]
    interventions: list[Intervention] = data["interventions"]

    # 1. All planned interventions completed
    planned = [i for i in interventions if i.status in ("planned", "in_progress")]
    completed = [i for i in interventions if i.status == "completed"]
    if planned:
        checks.append(
            _check(
                "interventions_completed",
                "All planned interventions completed",
                "fail",
                detail=f"{len(planned)} intervention(s) still planned or in progress",
            )
        )
        blockers.append(f"{len(planned)} intervention(s) not yet completed")
    elif completed:
        checks.append(
            _check(
                "interventions_completed",
                "All planned interventions completed",
                "pass",
                detail=f"{len(completed)} intervention(s) completed",
            )
        )
    else:
        checks.append(
            _check(
                "interventions_completed",
                "All planned interventions completed",
                "not_applicable",
                detail="No interventions recorded",
            )
        )

    # 2. Air clearance measurements (if asbestos was removed)
    asbestos_removed = any(
        (i.intervention_type or "").lower() in ("asbestos_removal", "desamiantage", "removal")
        and i.status == "completed"
        for i in interventions
    )
    if asbestos_removed:
        clearance_docs = [
            d
            for d in documents
            if (d.document_type or "").lower() in ("air_clearance", "clearance_measurement", "liberation_mesure")
        ]
        if clearance_docs:
            checks.append(
                _check(
                    "air_clearance",
                    "Air clearance measurements after asbestos removal",
                    "pass",
                    legal_basis="CFST 6503",
                    detail="Air clearance document available",
                )
            )
        else:
            checks.append(
                _check(
                    "air_clearance",
                    "Air clearance measurements after asbestos removal",
                    "fail",
                    legal_basis="CFST 6503",
                    detail="Air clearance measurement required after asbestos removal",
                )
            )
            blockers.append("Air clearance measurement required after asbestos removal")
    else:
        checks.append(
            _check(
                "air_clearance",
                "Air clearance measurements after asbestos removal",
                "not_applicable",
                detail="No asbestos removal intervention recorded",
            )
        )

    # 3. No remaining critical risk levels
    critical_samples = [s for s in samples if (s.risk_level or "").lower() in ("critical", "high")]
    # Check if corresponding interventions have been completed
    if critical_samples:
        # If there are completed interventions, we assume remediation was done
        if completed:
            checks.append(
                _check(
                    "no_critical_risk",
                    "No remaining critical risk levels",
                    "pass",
                    detail="Critical/high risk samples present but interventions completed",
                )
            )
        else:
            checks.append(
                _check(
                    "no_critical_risk",
                    "No remaining critical risk levels",
                    "fail",
                    detail=f"{len(critical_samples)} sample(s) with critical/high risk, no completed interventions",
                )
            )
            blockers.append(f"{len(critical_samples)} sample(s) with critical/high risk level remain unaddressed")
    else:
        checks.append(
            _check(
                "no_critical_risk",
                "No remaining critical risk levels",
                "pass",
                detail="No critical/high risk samples",
            )
        )

    # 4. Post-works inspection report (conditional)
    inspection_docs = [
        d
        for d in documents
        if (d.document_type or "").lower() in ("post_works_inspection", "inspection_report", "pv_reception")
    ]
    if inspection_docs:
        checks.append(
            _check(
                "post_works_inspection",
                "Post-works inspection report uploaded",
                "pass",
                detail="Post-works inspection report available",
                required=False,
            )
        )
    else:
        checks.append(
            _check(
                "post_works_inspection",
                "Post-works inspection report uploaded",
                "conditional",
                detail="No post-works inspection report uploaded",
                required=False,
            )
        )
        conditions.append("Post-works inspection report not yet uploaded")

    return checks, blockers, conditions


# ---------------------------------------------------------------------------
# safe_to_requalify checks
# ---------------------------------------------------------------------------


async def _evaluate_safe_to_requalify(
    db: AsyncSession,
    data: dict[str, Any],
) -> tuple[list[dict], list[str], list[str]]:
    """Evaluate all checks for safe_to_requalify readiness."""
    checks: list[dict] = []
    blockers: list[str] = []
    conditions: list[str] = []

    diagnostics: list[Diagnostic] = data["diagnostics"]
    interventions: list[Intervention] = data["interventions"]

    now = datetime.now(UTC)

    # 1. Diagnostic older than validity period
    completed_diags = [d for d in diagnostics if d.status in ("completed", "validated")]
    if completed_diags:
        latest_date = max(
            (d.date_inspection or d.created_at.date() if d.created_at else None for d in completed_diags),
            default=None,
        )
        if latest_date is not None:
            # Handle date vs datetime comparison
            if hasattr(latest_date, "date"):
                latest_date = latest_date.date()
            age_days = (now.date() - latest_date).days
            age_years = age_days / 365.25
            if age_years >= DIAGNOSTIC_VALIDITY_YEARS:
                checks.append(
                    _check(
                        "diagnostic_age",
                        "Diagnostic within validity period",
                        "fail",
                        detail=f"Latest diagnostic is {age_years:.1f} years old (threshold: {DIAGNOSTIC_VALIDITY_YEARS} years)",
                        required=False,
                    )
                )
                conditions.append(f"Diagnostic is {age_years:.1f} years old — requalification recommended")
            else:
                checks.append(
                    _check(
                        "diagnostic_age",
                        "Diagnostic within validity period",
                        "pass",
                        detail=f"Latest diagnostic is {age_years:.1f} years old",
                        required=False,
                    )
                )
        else:
            checks.append(
                _check(
                    "diagnostic_age",
                    "Diagnostic within validity period",
                    "fail",
                    detail="Cannot determine diagnostic date",
                    required=False,
                )
            )
            conditions.append("Cannot determine diagnostic age — requalification recommended")
    else:
        checks.append(
            _check(
                "diagnostic_age",
                "Diagnostic within validity period",
                "fail",
                detail="No completed diagnostic found",
                required=False,
            )
        )
        conditions.append("No completed diagnostic — qualification needed")

    # 2. Significant building modifications since last diagnostic
    recent_interventions = [
        i
        for i in interventions
        if i.status == "completed"
        and i.intervention_type
        and i.intervention_type.lower() in ("renovation", "transformation", "extension", "demolition_partial")
    ]
    if recent_interventions:
        checks.append(
            _check(
                "building_modifications",
                "No significant modifications since diagnostic",
                "fail",
                detail=f"{len(recent_interventions)} significant modification(s) recorded",
                required=False,
            )
        )
        conditions.append(
            f"{len(recent_interventions)} significant building modification(s) — requalification recommended"
        )
    else:
        checks.append(
            _check(
                "building_modifications",
                "No significant modifications since diagnostic",
                "pass",
                detail="No significant modifications recorded",
                required=False,
            )
        )

    return checks, blockers, conditions


# ---------------------------------------------------------------------------
# Score computation
# ---------------------------------------------------------------------------


def _compute_score(checks: list[dict]) -> float:
    """Compute readiness score as fraction of applicable checks that pass."""
    applicable = [c for c in checks if c["status"] != "not_applicable"]
    if not applicable:
        return 1.0
    passed = sum(1 for c in applicable if c["status"] == "pass")
    return round(passed / len(applicable), 4)


def _determine_status(checks: list[dict], blockers: list[str], conditions: list[str]) -> str:
    """Determine overall readiness status."""
    if blockers:
        return "blocked"

    # Check if any required checks failed
    required_failed = [c for c in checks if c.get("required", True) and c["status"] == "fail"]
    if required_failed:
        return "blocked"

    # Check if there are conditional items
    conditional_checks = [c for c in checks if c["status"] == "conditional"]
    if conditional_checks or conditions:
        return "conditional"

    return "ready"


# ---------------------------------------------------------------------------
# Evaluator dispatch
# ---------------------------------------------------------------------------

_EVALUATORS = {
    "safe_to_start": _evaluate_safe_to_start,
    "safe_to_tender": _evaluate_safe_to_tender,
    "safe_to_reopen": _evaluate_safe_to_reopen,
    "safe_to_requalify": _evaluate_safe_to_requalify,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def evaluate_readiness(
    db: AsyncSession,
    building_id: UUID,
    readiness_type: str,
    assessed_by_id: UUID | None = None,
) -> ReadinessAssessment:
    """
    Evaluate whether a building is ready for a specific regulatory milestone.

    Loads building data, runs the relevant checks, computes a score and status,
    and upserts the result into the ReadinessAssessment table (idempotent for
    same building + readiness_type).

    Args:
        db: Async database session.
        building_id: UUID of the building to evaluate.
        readiness_type: One of safe_to_start, safe_to_tender, safe_to_reopen, safe_to_requalify.
        assessed_by_id: Optional UUID of the user triggering evaluation.

    Returns:
        The persisted ReadinessAssessment record.

    Raises:
        ValueError: If readiness_type is not recognized or building not found.
    """
    if readiness_type not in _EVALUATORS:
        raise ValueError(f"Unknown readiness_type '{readiness_type}'. Must be one of: {', '.join(READINESS_TYPES)}")

    data = await _load_building_data(db, building_id)
    if data is None:
        raise ValueError(f"Building {building_id} not found")

    evaluator = _EVALUATORS[readiness_type]
    checks, blockers, conditions = await evaluator(db, data)

    score = _compute_score(checks)
    status = _determine_status(checks, blockers, conditions)
    now = datetime.now(UTC)

    # Upsert: find existing assessment for this building + type
    result = await db.execute(
        select(ReadinessAssessment).where(
            ReadinessAssessment.building_id == building_id,
            ReadinessAssessment.readiness_type == readiness_type,
        )
    )
    assessment = result.scalar_one_or_none()

    if assessment is None:
        assessment = ReadinessAssessment(
            building_id=building_id,
            readiness_type=readiness_type,
        )
        db.add(assessment)

    assessment.status = status
    assessment.score = score
    assessment.checks_json = checks
    assessment.blockers_json = [{"message": b} for b in blockers]
    assessment.conditions_json = [{"message": c} for c in conditions]
    assessment.assessed_at = now
    assessment.assessed_by = assessed_by_id
    assessment.notes = f"Auto-evaluated at {now.isoformat()}"

    await db.commit()
    await db.refresh(assessment)
    return assessment


async def evaluate_all_readiness(
    db: AsyncSession,
    building_id: UUID,
    assessed_by_id: UUID | None = None,
) -> list[ReadinessAssessment]:
    """
    Evaluate all 4 readiness types for a building and return all assessments.

    Args:
        db: Async database session.
        building_id: UUID of the building to evaluate.
        assessed_by_id: Optional UUID of the user triggering evaluation.

    Returns:
        List of 4 ReadinessAssessment records.
    """
    assessments: list[ReadinessAssessment] = []
    for rtype in READINESS_TYPES:
        assessment = await evaluate_readiness(db, building_id, rtype, assessed_by_id)
        assessments.append(assessment)
    return assessments


def generate_prework_triggers(checks_json: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """
    Deterministically derive prework triggers from readiness checks.

    This is the service-layer entry point. The same logic is also used inside
    ``ReadinessAssessmentRead`` (schema) so that serialised API responses always
    include the ``prework_triggers`` field.

    Returns:
        List of dicts with keys: trigger_type, reason, urgency, source_check.
    """
    return _derive_prework_triggers(checks_json)
