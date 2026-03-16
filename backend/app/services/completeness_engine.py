"""
SwissBuildingOS - Completeness Engine Service

Evaluates whether a building's dossier is complete for a given workflow stage
(AvT or ApT). The commercial wedge is "safe-to-start dossier" for property
managers. A building is considered ready when completeness >= 95%.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.sample import Sample
from app.models.technical_plan import TechnicalPlan
from app.schemas.completeness import CompletenessCheck, CompletenessResult

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALL_POLLUTANTS = {"asbestos", "pcb", "lead", "hap", "radon"}

READY_THRESHOLD = 0.95

# Year-based applicability cutoffs
ASBESTOS_CUTOFF_YEAR = 1990
PCB_START_YEAR = 1955
PCB_END_YEAR = 1975
LEAD_CUTOFF_YEAR = 2006


# ---------------------------------------------------------------------------
# Individual check functions
# ---------------------------------------------------------------------------


def _check_has_diagnostic(
    diagnostics: list[Diagnostic],
    stage: str,
) -> CompletenessCheck:
    """Check that at least one diagnostic is completed or validated."""
    completed = [d for d in diagnostics if d.status in ("completed", "validated")]
    if completed:
        return CompletenessCheck(
            id="has_diagnostic",
            category="diagnostic",
            label_key="completeness.check.has_diagnostic",
            status="complete",
            weight=1.0,
            details=f"{len(completed)} completed diagnostic(s)",
        )
    if diagnostics:
        return CompletenessCheck(
            id="has_diagnostic",
            category="diagnostic",
            label_key="completeness.check.has_diagnostic",
            status="partial",
            weight=1.0,
            details="Diagnostic(s) exist but none completed/validated",
        )
    return CompletenessCheck(
        id="has_diagnostic",
        category="diagnostic",
        label_key="completeness.check.has_diagnostic",
        status="missing",
        weight=1.0,
        details="No diagnostic found",
    )


def _check_diagnostic_context(
    diagnostics: list[Diagnostic],
    stage: str,
) -> CompletenessCheck:
    """Check that at least one diagnostic has the correct context for the stage."""
    target_context = stage.upper() if stage.lower() in ("avt", "apt") else "AvT"
    matching = [d for d in diagnostics if (d.diagnostic_context or "").upper() == target_context]
    if matching:
        return CompletenessCheck(
            id="diagnostic_context",
            category="diagnostic",
            label_key="completeness.check.diagnostic_context",
            status="complete",
            weight=0.6,
            details=f"Diagnostic with context {target_context} found",
        )
    return CompletenessCheck(
        id="diagnostic_context",
        category="diagnostic",
        label_key="completeness.check.diagnostic_context",
        status="missing",
        weight=0.6,
        details=f"No diagnostic with context {target_context}",
    )


def _check_all_pollutants_evaluated(
    samples: list[Sample],
) -> CompletenessCheck:
    """Check that all 5 pollutant types have been evaluated."""
    evaluated = {(s.pollutant_type or "").lower() for s in samples}
    covered = evaluated & ALL_POLLUTANTS
    if covered == ALL_POLLUTANTS:
        return CompletenessCheck(
            id="all_pollutants_evaluated",
            category="diagnostic",
            label_key="completeness.check.all_pollutants_evaluated",
            status="complete",
            weight=0.8,
            details="All 5 pollutant types evaluated",
        )
    missing_pollutants = ALL_POLLUTANTS - covered
    return CompletenessCheck(
        id="all_pollutants_evaluated",
        category="diagnostic",
        label_key="completeness.check.all_pollutants_evaluated",
        status="partial" if covered else "missing",
        weight=0.8,
        details=f"Missing: {', '.join(sorted(missing_pollutants))}",
    )


def _check_pollutant_samples(
    samples: list[Sample],
    pollutant: str,
    construction_year: int | None,
    cutoff_year: int | None,
    end_year: int | None = None,
) -> CompletenessCheck:
    """Check if samples exist for a specific pollutant, considering building age."""
    check_id = f"has_{pollutant}_samples"
    label_key = f"completeness.check.has_{pollutant}_samples"

    # Determine applicability based on construction year
    if construction_year is not None and cutoff_year is not None:
        if end_year is not None:
            # Range check (e.g. PCB: 1955-1975)
            if construction_year < cutoff_year or construction_year > end_year:
                return CompletenessCheck(
                    id=check_id,
                    category="evidence",
                    label_key=label_key,
                    status="not_applicable",
                    weight=0.7,
                    details=f"Building year {construction_year} outside {cutoff_year}-{end_year}",
                )
        else:
            # Before-year check (e.g. asbestos: pre-1990)
            if construction_year >= cutoff_year:
                return CompletenessCheck(
                    id=check_id,
                    category="evidence",
                    label_key=label_key,
                    status="not_applicable",
                    weight=0.7,
                    details=f"Building year {construction_year} >= {cutoff_year}",
                )

    pollutant_samples = [s for s in samples if (s.pollutant_type or "").lower() == pollutant]
    if pollutant_samples:
        return CompletenessCheck(
            id=check_id,
            category="evidence",
            label_key=label_key,
            status="complete",
            weight=0.7,
            details=f"{len(pollutant_samples)} {pollutant} sample(s)",
        )
    return CompletenessCheck(
        id=check_id,
        category="evidence",
        label_key=label_key,
        status="missing",
        weight=0.7,
        details=f"No {pollutant} samples found",
    )


def _check_lab_results(samples: list[Sample]) -> CompletenessCheck:
    """Check that all samples have lab results (concentration + unit)."""
    if not samples:
        return CompletenessCheck(
            id="has_lab_results",
            category="evidence",
            label_key="completeness.check.has_lab_results",
            status="missing",
            weight=0.8,
            details="No samples to check",
        )
    missing_results = [s for s in samples if s.concentration is None or not s.unit]
    if not missing_results:
        return CompletenessCheck(
            id="has_lab_results",
            category="evidence",
            label_key="completeness.check.has_lab_results",
            status="complete",
            weight=0.8,
            details=f"All {len(samples)} samples have lab results",
        )
    return CompletenessCheck(
        id="has_lab_results",
        category="evidence",
        label_key="completeness.check.has_lab_results",
        status="partial",
        weight=0.8,
        details=f"{len(missing_results)}/{len(samples)} samples missing lab results",
    )


def _check_risk_levels(samples: list[Sample]) -> CompletenessCheck:
    """Check that no samples have missing risk_level."""
    if not samples:
        return CompletenessCheck(
            id="no_missing_risk_level",
            category="evidence",
            label_key="completeness.check.no_missing_risk_level",
            status="not_applicable",
            weight=0.5,
            details="No samples",
        )
    missing = [s for s in samples if not s.risk_level]
    if not missing:
        return CompletenessCheck(
            id="no_missing_risk_level",
            category="evidence",
            label_key="completeness.check.no_missing_risk_level",
            status="complete",
            weight=0.5,
            details="All samples have risk_level",
        )
    return CompletenessCheck(
        id="no_missing_risk_level",
        category="evidence",
        label_key="completeness.check.no_missing_risk_level",
        status="partial",
        weight=0.5,
        details=f"{len(missing)} sample(s) missing risk_level",
    )


def _check_has_report(documents: list[Document]) -> CompletenessCheck:
    """Check that at least one diagnostic report is uploaded."""
    reports = [d for d in documents if (d.document_type or "").lower() in ("diagnostic_report", "report")]
    if reports:
        return CompletenessCheck(
            id="has_report",
            category="document",
            label_key="completeness.check.has_report",
            status="complete",
            weight=0.8,
            details=f"{len(reports)} report(s) uploaded",
        )
    return CompletenessCheck(
        id="has_report",
        category="document",
        label_key="completeness.check.has_report",
        status="missing",
        weight=0.8,
        details="No diagnostic report uploaded",
    )


def _check_has_lab_reports(
    documents: list[Document],
    samples: list[Sample],
) -> CompletenessCheck:
    """Check that lab analysis reports are present for pollutants with samples."""
    pollutants_with_samples = {(s.pollutant_type or "").lower() for s in samples} & ALL_POLLUTANTS
    if not pollutants_with_samples:
        return CompletenessCheck(
            id="has_lab_reports",
            category="document",
            label_key="completeness.check.has_lab_reports",
            status="not_applicable",
            weight=0.6,
            details="No pollutant samples to require lab reports",
        )
    lab_reports = [d for d in documents if (d.document_type or "").lower() in ("lab_report", "lab_analysis")]
    if lab_reports:
        return CompletenessCheck(
            id="has_lab_reports",
            category="document",
            label_key="completeness.check.has_lab_reports",
            status="complete",
            weight=0.6,
            details=f"{len(lab_reports)} lab report(s)",
        )
    return CompletenessCheck(
        id="has_lab_reports",
        category="document",
        label_key="completeness.check.has_lab_reports",
        status="missing",
        weight=0.6,
        details="No lab analysis reports uploaded",
    )


def _check_has_plans(plans: list[TechnicalPlan]) -> CompletenessCheck:
    """Check that at least one floor plan is uploaded."""
    floor_plans = [p for p in plans if (p.plan_type or "").lower() == "floor_plan"]
    if floor_plans:
        return CompletenessCheck(
            id="has_plans",
            category="document",
            label_key="completeness.check.has_plans",
            status="complete",
            weight=0.5,
            details=f"{len(floor_plans)} floor plan(s)",
        )
    if plans:
        return CompletenessCheck(
            id="has_plans",
            category="document",
            label_key="completeness.check.has_plans",
            status="partial",
            weight=0.5,
            details="Plans exist but no floor_plan type",
        )
    return CompletenessCheck(
        id="has_plans",
        category="document",
        label_key="completeness.check.has_plans",
        status="missing",
        weight=0.5,
        details="No technical plans uploaded",
    )


def _check_suva_notified(
    diagnostics: list[Diagnostic],
    samples: list[Sample],
) -> CompletenessCheck:
    """Check SUVA notification if asbestos found."""
    has_positive_asbestos = any(
        (s.pollutant_type or "").lower() == "asbestos" and s.threshold_exceeded for s in samples
    )
    if not has_positive_asbestos:
        return CompletenessCheck(
            id="suva_notified",
            category="regulatory",
            label_key="completeness.check.suva_notified",
            status="not_applicable",
            weight=0.7,
            details="No positive asbestos samples",
        )
    notified = any(d.suva_notification_required and d.suva_notification_date for d in diagnostics)
    if notified:
        return CompletenessCheck(
            id="suva_notified",
            category="regulatory",
            label_key="completeness.check.suva_notified",
            status="complete",
            weight=0.7,
            details="SUVA notification sent",
        )
    return CompletenessCheck(
        id="suva_notified",
        category="regulatory",
        label_key="completeness.check.suva_notified",
        status="missing",
        weight=0.7,
        details="SUVA notification required but not sent",
    )


def _check_work_category(samples: list[Sample]) -> CompletenessCheck:
    """Check that work category is set for asbestos materials."""
    asbestos_positive = [s for s in samples if (s.pollutant_type or "").lower() == "asbestos" and s.threshold_exceeded]
    if not asbestos_positive:
        return CompletenessCheck(
            id="work_category_set",
            category="regulatory",
            label_key="completeness.check.work_category_set",
            status="not_applicable",
            weight=0.6,
            details="No positive asbestos samples",
        )
    missing = [s for s in asbestos_positive if not s.cfst_work_category]
    if not missing:
        return CompletenessCheck(
            id="work_category_set",
            category="regulatory",
            label_key="completeness.check.work_category_set",
            status="complete",
            weight=0.6,
            details="Work category set for all asbestos materials",
        )
    return CompletenessCheck(
        id="work_category_set",
        category="regulatory",
        label_key="completeness.check.work_category_set",
        status="partial",
        weight=0.6,
        details=f"{len(missing)} asbestos sample(s) missing work category",
    )


def _check_waste_classified(samples: list[Sample]) -> CompletenessCheck:
    """Check that waste disposal type is set for all positive samples."""
    positive = [s for s in samples if s.threshold_exceeded]
    if not positive:
        return CompletenessCheck(
            id="waste_classified",
            category="regulatory",
            label_key="completeness.check.waste_classified",
            status="not_applicable",
            weight=0.5,
            details="No positive samples",
        )
    missing = [s for s in positive if not s.waste_disposal_type]
    if not missing:
        return CompletenessCheck(
            id="waste_classified",
            category="regulatory",
            label_key="completeness.check.waste_classified",
            status="complete",
            weight=0.5,
            details="All positive samples have waste classification",
        )
    return CompletenessCheck(
        id="waste_classified",
        category="regulatory",
        label_key="completeness.check.waste_classified",
        status="partial",
        weight=0.5,
        details=f"{len(missing)} positive sample(s) missing waste classification",
    )


def _check_no_critical_actions(actions: list[ActionItem]) -> CompletenessCheck:
    """Check that no critical/high priority actions are in 'open' status."""
    critical_open = [a for a in actions if a.status == "open" and a.priority in ("critical", "high")]
    if not critical_open:
        return CompletenessCheck(
            id="no_critical_actions",
            category="action",
            label_key="completeness.check.no_critical_actions",
            status="complete",
            weight=0.7,
            details="No open critical/high actions",
        )
    return CompletenessCheck(
        id="no_critical_actions",
        category="action",
        label_key="completeness.check.no_critical_actions",
        status="missing",
        weight=0.7,
        details=f"{len(critical_open)} open critical/high action(s)",
    )


def _check_actions_assigned(actions: list[ActionItem]) -> CompletenessCheck:
    """Check that all required actions have an assignee."""
    required = [a for a in actions if a.status in ("open", "in_progress")]
    if not required:
        return CompletenessCheck(
            id="actions_assigned",
            category="action",
            label_key="completeness.check.actions_assigned",
            status="not_applicable",
            weight=0.4,
            details="No open/in_progress actions",
        )
    unassigned = [a for a in required if not a.assigned_to]
    if not unassigned:
        return CompletenessCheck(
            id="actions_assigned",
            category="action",
            label_key="completeness.check.actions_assigned",
            status="complete",
            weight=0.4,
            details="All actions assigned",
        )
    return CompletenessCheck(
        id="actions_assigned",
        category="action",
        label_key="completeness.check.actions_assigned",
        status="partial",
        weight=0.4,
        details=f"{len(unassigned)} action(s) without assignee",
    )


# ---------------------------------------------------------------------------
# Score calculation
# ---------------------------------------------------------------------------


def _calculate_score(checks: list[CompletenessCheck]) -> float:
    """Calculate weighted completeness score from checks."""
    applicable = [c for c in checks if c.status != "not_applicable"]
    if not applicable:
        return 1.0

    total_weight = sum(c.weight for c in applicable)
    if total_weight == 0:
        return 1.0

    earned = 0.0
    for check in applicable:
        if check.status == "complete":
            earned += check.weight
        elif check.status == "partial":
            earned += check.weight * 0.5

    return round(earned / total_weight, 4)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def evaluate_completeness(
    db: AsyncSession,
    building_id: UUID,
    workflow_stage: str = "avt",
) -> CompletenessResult:
    """
    Evaluate the completeness of a building dossier for a workflow stage.

    Queries all related data (diagnostics, samples, documents, actions, plans)
    and runs all applicable checks, returning a structured result with a
    weighted score.
    """
    # Fetch building
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return CompletenessResult(
            building_id=building_id,
            workflow_stage=workflow_stage,
            overall_score=0.0,
            checks=[],
            missing_items=["Building not found"],
            ready_to_proceed=False,
            evaluated_at=datetime.now(UTC),
        )

    construction_year = building.construction_year

    # Fetch diagnostics
    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(diag_result.scalars().all())

    # Fetch samples (via diagnostics)
    samples: list[Sample] = []
    if diagnostics:
        diag_ids = [d.id for d in diagnostics]
        sample_result = await db.execute(select(Sample).where(Sample.diagnostic_id.in_(diag_ids)))
        samples = list(sample_result.scalars().all())

    # Fetch documents
    doc_result = await db.execute(select(Document).where(Document.building_id == building_id))
    documents = list(doc_result.scalars().all())

    # Fetch technical plans
    plan_result = await db.execute(select(TechnicalPlan).where(TechnicalPlan.building_id == building_id))
    plans = list(plan_result.scalars().all())

    # Fetch action items
    action_result = await db.execute(select(ActionItem).where(ActionItem.building_id == building_id))
    actions = list(action_result.scalars().all())

    # Run all checks
    checks: list[CompletenessCheck] = []

    # Diagnostic checks
    checks.append(_check_has_diagnostic(diagnostics, workflow_stage))
    checks.append(_check_diagnostic_context(diagnostics, workflow_stage))
    checks.append(_check_all_pollutants_evaluated(samples))

    # Sample / evidence checks
    checks.append(_check_pollutant_samples(samples, "asbestos", construction_year, ASBESTOS_CUTOFF_YEAR))
    checks.append(_check_pollutant_samples(samples, "pcb", construction_year, PCB_START_YEAR, PCB_END_YEAR))
    checks.append(_check_pollutant_samples(samples, "lead", construction_year, LEAD_CUTOFF_YEAR))
    checks.append(_check_lab_results(samples))
    checks.append(_check_risk_levels(samples))

    # Document checks
    checks.append(_check_has_report(documents))
    checks.append(_check_has_lab_reports(documents, samples))
    checks.append(_check_has_plans(plans))

    # Regulatory checks
    checks.append(_check_suva_notified(diagnostics, samples))
    checks.append(_check_work_category(samples))
    checks.append(_check_waste_classified(samples))

    # Action checks
    checks.append(_check_no_critical_actions(actions))
    checks.append(_check_actions_assigned(actions))

    # Calculate score
    overall_score = _calculate_score(checks)

    # Build missing items list
    missing_items = [c.details or c.label_key for c in checks if c.status == "missing"]

    return CompletenessResult(
        building_id=building_id,
        workflow_stage=workflow_stage,
        overall_score=overall_score,
        checks=checks,
        missing_items=missing_items,
        ready_to_proceed=overall_score >= READY_THRESHOLD,
        evaluated_at=datetime.now(UTC),
    )
