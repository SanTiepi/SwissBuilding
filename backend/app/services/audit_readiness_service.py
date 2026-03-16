"""
SwissBuildingOS - Audit Readiness Service

Evaluates how prepared a building (or portfolio) is for an authority audit.
Covers documentation, compliance artefacts, evidence chain, and process
readiness.  Score is 0-100; simulated outcome is pass / conditional / fail.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.assignment import Assignment
from app.models.building import Building
from app.models.compliance_artefact import ComplianceArtefact
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.event import Event
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.models.technical_plan import TechnicalPlan
from app.schemas.audit_readiness import (
    AuditChecklist,
    AuditChecklistItem,
    AuditFlag,
    AuditReadinessCheck,
    AuditReadinessResult,
    AuditSimulationResult,
    BuildingAuditSummary,
    PortfolioAuditReadiness,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

READY_THRESHOLD = 80  # score >= 80 → building considered audit-ready

ALL_POLLUTANTS = {"asbestos", "pcb", "lead", "hap", "radon"}


# ---------------------------------------------------------------------------
# Internal data loader
# ---------------------------------------------------------------------------


async def _load_building_data(db: AsyncSession, building_id: UUID) -> dict | None:
    """Fetch all entities relevant to audit readiness for a single building."""
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

    plan_result = await db.execute(select(TechnicalPlan).where(TechnicalPlan.building_id == building_id))
    plans = list(plan_result.scalars().all())

    action_result = await db.execute(select(ActionItem).where(ActionItem.building_id == building_id))
    actions = list(action_result.scalars().all())

    artefact_result = await db.execute(select(ComplianceArtefact).where(ComplianceArtefact.building_id == building_id))
    artefacts = list(artefact_result.scalars().all())

    assign_result = await db.execute(
        select(Assignment).where(
            Assignment.target_type == "building",
            Assignment.target_id == building_id,
        )
    )
    assignments = list(assign_result.scalars().all())

    event_result = await db.execute(select(Event).where(Event.building_id == building_id))
    events = list(event_result.scalars().all())

    intervention_result = await db.execute(select(Intervention).where(Intervention.building_id == building_id))
    interventions = list(intervention_result.scalars().all())

    return {
        "building": building,
        "diagnostics": diagnostics,
        "samples": samples,
        "documents": documents,
        "plans": plans,
        "actions": actions,
        "artefacts": artefacts,
        "assignments": assignments,
        "events": events,
        "interventions": interventions,
    }


# ---------------------------------------------------------------------------
# Individual checks  (used by FN1 + FN2)
# ---------------------------------------------------------------------------


def _chk_diagnostic_validated(diagnostics: list[Diagnostic]) -> AuditReadinessCheck:
    validated = [d for d in diagnostics if d.status == "validated"]
    if validated:
        return AuditReadinessCheck(
            id="diagnostic_validated",
            category="documentation",
            label="All diagnostics validated",
            status="done",
            weight=10.0,
            detail=f"{len(validated)} validated diagnostic(s)",
        )
    completed = [d for d in diagnostics if d.status == "completed"]
    if completed:
        return AuditReadinessCheck(
            id="diagnostic_validated",
            category="documentation",
            label="All diagnostics validated",
            status="partial",
            weight=10.0,
            detail="Diagnostics completed but not validated",
        )
    return AuditReadinessCheck(
        id="diagnostic_validated",
        category="documentation",
        label="All diagnostics validated",
        status="missing",
        weight=10.0,
        detail="No validated or completed diagnostics",
    )


def _chk_all_samples_documented(samples: list[Sample]) -> AuditReadinessCheck:
    if not samples:
        return AuditReadinessCheck(
            id="samples_documented",
            category="evidence",
            label="All samples documented with results",
            status="missing",
            weight=8.0,
            detail="No samples found",
        )
    incomplete = [s for s in samples if s.concentration is None or not s.unit]
    if not incomplete:
        return AuditReadinessCheck(
            id="samples_documented",
            category="evidence",
            label="All samples documented with results",
            status="done",
            weight=8.0,
            detail=f"{len(samples)} sample(s) fully documented",
        )
    return AuditReadinessCheck(
        id="samples_documented",
        category="evidence",
        label="All samples documented with results",
        status="partial",
        weight=8.0,
        detail=f"{len(incomplete)}/{len(samples)} samples missing results",
    )


def _chk_compliance_artefacts_current(
    artefacts: list[ComplianceArtefact],
) -> AuditReadinessCheck:
    now = datetime.now(UTC)
    if not artefacts:
        return AuditReadinessCheck(
            id="compliance_artefacts_current",
            category="compliance",
            label="Compliance artefacts present and current",
            status="missing",
            weight=9.0,
            detail="No compliance artefacts found",
        )
    expired = [a for a in artefacts if a.expires_at is not None and a.expires_at < now]
    active = [a for a in artefacts if a.status in ("submitted", "acknowledged")]
    if expired:
        return AuditReadinessCheck(
            id="compliance_artefacts_current",
            category="compliance",
            label="Compliance artefacts present and current",
            status="partial",
            weight=9.0,
            detail=f"{len(expired)} expired artefact(s)",
        )
    if active:
        return AuditReadinessCheck(
            id="compliance_artefacts_current",
            category="compliance",
            label="Compliance artefacts present and current",
            status="done",
            weight=9.0,
            detail=f"{len(active)} active artefact(s)",
        )
    return AuditReadinessCheck(
        id="compliance_artefacts_current",
        category="compliance",
        label="Compliance artefacts present and current",
        status="partial",
        weight=9.0,
        detail="Artefacts in draft status only",
    )


def _chk_waste_plan_exists(
    samples: list[Sample],
    interventions: list[Intervention],
) -> AuditReadinessCheck:
    positive = [s for s in samples if s.threshold_exceeded]
    if not positive:
        return AuditReadinessCheck(
            id="waste_plan_exists",
            category="compliance",
            label="Waste management plan exists",
            status="done",
            weight=7.0,
            detail="No positive samples — waste plan not required",
        )
    classified = [s for s in positive if s.waste_disposal_type]
    waste_interventions = [
        i for i in interventions if (i.intervention_type or "").lower() in ("waste_removal", "decontamination")
    ]
    if classified and len(classified) == len(positive):
        return AuditReadinessCheck(
            id="waste_plan_exists",
            category="compliance",
            label="Waste management plan exists",
            status="done",
            weight=7.0,
            detail=f"All {len(positive)} positive samples have waste classification",
        )
    if classified or waste_interventions:
        return AuditReadinessCheck(
            id="waste_plan_exists",
            category="compliance",
            label="Waste management plan exists",
            status="partial",
            weight=7.0,
            detail="Partial waste management coverage",
        )
    return AuditReadinessCheck(
        id="waste_plan_exists",
        category="compliance",
        label="Waste management plan exists",
        status="missing",
        weight=7.0,
        detail="Positive samples without waste classification or plan",
    )


def _chk_responsible_parties_assigned(
    assignments: list[Assignment],
) -> AuditReadinessCheck:
    if not assignments:
        return AuditReadinessCheck(
            id="responsible_parties",
            category="process",
            label="Responsible parties assigned",
            status="missing",
            weight=6.0,
            detail="No assignments found for this building",
        )
    roles_present = {a.role for a in assignments}
    if "responsible" in roles_present:
        return AuditReadinessCheck(
            id="responsible_parties",
            category="process",
            label="Responsible parties assigned",
            status="done",
            weight=6.0,
            detail=f"{len(assignments)} assignment(s), responsible present",
        )
    return AuditReadinessCheck(
        id="responsible_parties",
        category="process",
        label="Responsible parties assigned",
        status="partial",
        weight=6.0,
        detail="Assignments exist but no 'responsible' role",
    )


def _chk_timeline_commitments(events: list[Event]) -> AuditReadinessCheck:
    if not events:
        return AuditReadinessCheck(
            id="timeline_commitments",
            category="process",
            label="Timeline commitments documented",
            status="missing",
            weight=5.0,
            detail="No events recorded",
        )
    if len(events) >= 3:
        return AuditReadinessCheck(
            id="timeline_commitments",
            category="process",
            label="Timeline commitments documented",
            status="done",
            weight=5.0,
            detail=f"{len(events)} event(s) recorded",
        )
    return AuditReadinessCheck(
        id="timeline_commitments",
        category="process",
        label="Timeline commitments documented",
        status="partial",
        weight=5.0,
        detail=f"Only {len(events)} event(s) recorded (recommend ≥3)",
    )


def _chk_report_uploaded(documents: list[Document]) -> AuditReadinessCheck:
    reports = [d for d in documents if (d.document_type or "").lower() in ("diagnostic_report", "report")]
    if reports:
        return AuditReadinessCheck(
            id="report_uploaded",
            category="documentation",
            label="Diagnostic report uploaded",
            status="done",
            weight=8.0,
            detail=f"{len(reports)} report(s)",
        )
    return AuditReadinessCheck(
        id="report_uploaded",
        category="documentation",
        label="Diagnostic report uploaded",
        status="missing",
        weight=8.0,
        detail="No diagnostic report found",
    )


def _chk_lab_reports(documents: list[Document], samples: list[Sample]) -> AuditReadinessCheck:
    pollutants_with_samples = {(s.pollutant_type or "").lower() for s in samples} & ALL_POLLUTANTS
    if not pollutants_with_samples:
        return AuditReadinessCheck(
            id="lab_reports",
            category="documentation",
            label="Lab analysis reports uploaded",
            status="done",
            weight=6.0,
            detail="No pollutant samples requiring lab reports",
        )
    lab_docs = [d for d in documents if (d.document_type or "").lower() in ("lab_report", "lab_analysis")]
    if lab_docs:
        return AuditReadinessCheck(
            id="lab_reports",
            category="documentation",
            label="Lab analysis reports uploaded",
            status="done",
            weight=6.0,
            detail=f"{len(lab_docs)} lab report(s)",
        )
    return AuditReadinessCheck(
        id="lab_reports",
        category="documentation",
        label="Lab analysis reports uploaded",
        status="missing",
        weight=6.0,
        detail="No lab reports uploaded for sampled pollutants",
    )


def _chk_floor_plans(plans: list[TechnicalPlan]) -> AuditReadinessCheck:
    floor_plans = [p for p in plans if (p.plan_type or "").lower() == "floor_plan"]
    if floor_plans:
        return AuditReadinessCheck(
            id="floor_plans",
            category="documentation",
            label="Floor plans available",
            status="done",
            weight=5.0,
            detail=f"{len(floor_plans)} floor plan(s)",
        )
    if plans:
        return AuditReadinessCheck(
            id="floor_plans",
            category="documentation",
            label="Floor plans available",
            status="partial",
            weight=5.0,
            detail="Plans present but no floor_plan type",
        )
    return AuditReadinessCheck(
        id="floor_plans",
        category="documentation",
        label="Floor plans available",
        status="missing",
        weight=5.0,
        detail="No technical plans uploaded",
    )


def _chk_risk_levels_assigned(samples: list[Sample]) -> AuditReadinessCheck:
    if not samples:
        return AuditReadinessCheck(
            id="risk_levels_assigned",
            category="evidence",
            label="Risk levels assigned to all samples",
            status="missing",
            weight=7.0,
            detail="No samples",
        )
    missing = [s for s in samples if not s.risk_level]
    if not missing:
        return AuditReadinessCheck(
            id="risk_levels_assigned",
            category="evidence",
            label="Risk levels assigned to all samples",
            status="done",
            weight=7.0,
            detail="All samples have risk levels",
        )
    return AuditReadinessCheck(
        id="risk_levels_assigned",
        category="evidence",
        label="Risk levels assigned to all samples",
        status="partial",
        weight=7.0,
        detail=f"{len(missing)} sample(s) missing risk level",
    )


def _chk_no_critical_open_actions(actions: list[ActionItem]) -> AuditReadinessCheck:
    critical_open = [a for a in actions if a.status == "open" and a.priority in ("critical", "high")]
    if not critical_open:
        return AuditReadinessCheck(
            id="no_critical_open_actions",
            category="process",
            label="No open critical/high actions",
            status="done",
            weight=8.0,
            detail="No blocking actions",
        )
    return AuditReadinessCheck(
        id="no_critical_open_actions",
        category="process",
        label="No open critical/high actions",
        status="missing",
        weight=8.0,
        detail=f"{len(critical_open)} critical/high action(s) still open",
    )


def _chk_suva_notification(diagnostics: list[Diagnostic], samples: list[Sample]) -> AuditReadinessCheck:
    has_positive_asbestos = any(
        (s.pollutant_type or "").lower() == "asbestos" and s.threshold_exceeded for s in samples
    )
    if not has_positive_asbestos:
        return AuditReadinessCheck(
            id="suva_notification",
            category="compliance",
            label="SUVA notification sent (if required)",
            status="done",
            weight=7.0,
            detail="No positive asbestos — SUVA not required",
        )
    notified = any(d.suva_notification_required and d.suva_notification_date for d in diagnostics)
    if notified:
        return AuditReadinessCheck(
            id="suva_notification",
            category="compliance",
            label="SUVA notification sent (if required)",
            status="done",
            weight=7.0,
            detail="SUVA notification sent",
        )
    return AuditReadinessCheck(
        id="suva_notification",
        category="compliance",
        label="SUVA notification sent (if required)",
        status="missing",
        weight=7.0,
        detail="Positive asbestos but SUVA notification missing",
    )


def _chk_work_categories(samples: list[Sample]) -> AuditReadinessCheck:
    asbestos_positive = [s for s in samples if (s.pollutant_type or "").lower() == "asbestos" and s.threshold_exceeded]
    if not asbestos_positive:
        return AuditReadinessCheck(
            id="work_categories",
            category="compliance",
            label="CFST work categories set for asbestos",
            status="done",
            weight=6.0,
            detail="No positive asbestos samples",
        )
    missing = [s for s in asbestos_positive if not s.cfst_work_category]
    if not missing:
        return AuditReadinessCheck(
            id="work_categories",
            category="compliance",
            label="CFST work categories set for asbestos",
            status="done",
            weight=6.0,
            detail="Work category set for all asbestos materials",
        )
    return AuditReadinessCheck(
        id="work_categories",
        category="compliance",
        label="CFST work categories set for asbestos",
        status="partial",
        weight=6.0,
        detail=f"{len(missing)} asbestos sample(s) missing work category",
    )


def _chk_all_pollutants_covered(samples: list[Sample]) -> AuditReadinessCheck:
    evaluated = {(s.pollutant_type or "").lower() for s in samples}
    covered = evaluated & ALL_POLLUTANTS
    if covered == ALL_POLLUTANTS:
        return AuditReadinessCheck(
            id="all_pollutants_covered",
            category="evidence",
            label="All 5 pollutant types evaluated",
            status="done",
            weight=7.0,
            detail="All pollutants covered",
        )
    if covered:
        missing = ALL_POLLUTANTS - covered
        return AuditReadinessCheck(
            id="all_pollutants_covered",
            category="evidence",
            label="All 5 pollutant types evaluated",
            status="partial",
            weight=7.0,
            detail=f"Missing: {', '.join(sorted(missing))}",
        )
    return AuditReadinessCheck(
        id="all_pollutants_covered",
        category="evidence",
        label="All 5 pollutant types evaluated",
        status="missing",
        weight=7.0,
        detail="No pollutant samples found",
    )


def _chk_actions_assigned(actions: list[ActionItem]) -> AuditReadinessCheck:
    active = [a for a in actions if a.status in ("open", "in_progress")]
    if not active:
        return AuditReadinessCheck(
            id="actions_assigned",
            category="process",
            label="All active actions assigned",
            status="done",
            weight=5.0,
            detail="No active actions",
        )
    unassigned = [a for a in active if not a.assigned_to]
    if not unassigned:
        return AuditReadinessCheck(
            id="actions_assigned",
            category="process",
            label="All active actions assigned",
            status="done",
            weight=5.0,
            detail="All active actions assigned",
        )
    return AuditReadinessCheck(
        id="actions_assigned",
        category="process",
        label="All active actions assigned",
        status="partial",
        weight=5.0,
        detail=f"{len(unassigned)} action(s) without assignee",
    )


def _chk_interventions_documented(
    interventions: list[Intervention],
) -> AuditReadinessCheck:
    if not interventions:
        return AuditReadinessCheck(
            id="interventions_documented",
            category="documentation",
            label="Interventions documented",
            status="done",
            weight=4.0,
            detail="No interventions (not required)",
        )
    completed = [i for i in interventions if i.status == "completed"]
    if len(completed) == len(interventions):
        return AuditReadinessCheck(
            id="interventions_documented",
            category="documentation",
            label="Interventions documented",
            status="done",
            weight=4.0,
            detail=f"{len(completed)} intervention(s) completed",
        )
    return AuditReadinessCheck(
        id="interventions_documented",
        category="documentation",
        label="Interventions documented",
        status="partial",
        weight=4.0,
        detail=f"{len(interventions) - len(completed)} intervention(s) not completed",
    )


# ---------------------------------------------------------------------------
# Collect all checks
# ---------------------------------------------------------------------------


def _run_all_checks(data: dict) -> list[AuditReadinessCheck]:
    """Run all audit readiness checks and return the list."""
    return [
        _chk_diagnostic_validated(data["diagnostics"]),
        _chk_report_uploaded(data["documents"]),
        _chk_lab_reports(data["documents"], data["samples"]),
        _chk_floor_plans(data["plans"]),
        _chk_interventions_documented(data["interventions"]),
        _chk_all_samples_documented(data["samples"]),
        _chk_risk_levels_assigned(data["samples"]),
        _chk_all_pollutants_covered(data["samples"]),
        _chk_compliance_artefacts_current(data["artefacts"]),
        _chk_suva_notification(data["diagnostics"], data["samples"]),
        _chk_work_categories(data["samples"]),
        _chk_waste_plan_exists(data["samples"], data["interventions"]),
        _chk_responsible_parties_assigned(data["assignments"]),
        _chk_timeline_commitments(data["events"]),
        _chk_no_critical_open_actions(data["actions"]),
        _chk_actions_assigned(data["actions"]),
    ]


def _calculate_score(checks: list[AuditReadinessCheck]) -> int:
    """Weighted score 0-100 from check results."""
    total_weight = sum(c.weight for c in checks)
    if total_weight == 0:
        return 100
    earned = 0.0
    for c in checks:
        if c.status == "done":
            earned += c.weight
        elif c.status == "partial":
            earned += c.weight * 0.5
    return round(earned / total_weight * 100)


# ---------------------------------------------------------------------------
# FN1 - evaluate_audit_readiness
# ---------------------------------------------------------------------------


async def evaluate_audit_readiness(db: AsyncSession, building_id: UUID) -> AuditReadinessResult | None:
    data = await _load_building_data(db, building_id)
    if data is None:
        return None

    checks = _run_all_checks(data)
    score = _calculate_score(checks)

    return AuditReadinessResult(
        building_id=building_id,
        score=score,
        checks=checks,
        evaluated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN2 - get_audit_checklist
# ---------------------------------------------------------------------------

_CHECKLIST_DEFINITIONS: list[dict] = [
    # Documentation (7 items)
    {
        "id": "cl_diag_validated",
        "cat": "documentation",
        "label": "All diagnostics validated",
        "required": True,
        "check_id": "diagnostic_validated",
    },
    {
        "id": "cl_report_uploaded",
        "cat": "documentation",
        "label": "Diagnostic report uploaded",
        "required": True,
        "check_id": "report_uploaded",
    },
    {
        "id": "cl_lab_reports",
        "cat": "documentation",
        "label": "Lab analysis reports uploaded",
        "required": True,
        "check_id": "lab_reports",
    },
    {
        "id": "cl_floor_plans",
        "cat": "documentation",
        "label": "Floor plans available",
        "required": False,
        "check_id": "floor_plans",
    },
    {
        "id": "cl_interventions_doc",
        "cat": "documentation",
        "label": "Interventions documented",
        "required": False,
        "check_id": "interventions_documented",
    },
    {
        "id": "cl_building_info",
        "cat": "documentation",
        "label": "Building metadata complete (year, type, area)",
        "required": True,
        "check_id": None,
    },
    {
        "id": "cl_photo_evidence",
        "cat": "documentation",
        "label": "Photo evidence for key findings",
        "required": False,
        "check_id": None,
    },
    # Compliance (6 items)
    {
        "id": "cl_artefacts_current",
        "cat": "compliance",
        "label": "Compliance artefacts current",
        "required": True,
        "check_id": "compliance_artefacts_current",
    },
    {
        "id": "cl_suva",
        "cat": "compliance",
        "label": "SUVA notification sent (if required)",
        "required": True,
        "check_id": "suva_notification",
    },
    {
        "id": "cl_work_cat",
        "cat": "compliance",
        "label": "CFST work categories set",
        "required": True,
        "check_id": "work_categories",
    },
    {
        "id": "cl_waste_plan",
        "cat": "compliance",
        "label": "Waste management plan",
        "required": True,
        "check_id": "waste_plan_exists",
    },
    {
        "id": "cl_canton_notification",
        "cat": "compliance",
        "label": "Canton notification (if required)",
        "required": False,
        "check_id": None,
    },
    {
        "id": "cl_legal_basis",
        "cat": "compliance",
        "label": "Legal basis referenced on artefacts",
        "required": False,
        "check_id": None,
    },
    # Evidence (5 items)
    {
        "id": "cl_samples_doc",
        "cat": "evidence",
        "label": "All samples documented with results",
        "required": True,
        "check_id": "samples_documented",
    },
    {
        "id": "cl_risk_levels",
        "cat": "evidence",
        "label": "Risk levels assigned",
        "required": True,
        "check_id": "risk_levels_assigned",
    },
    {
        "id": "cl_pollutants_covered",
        "cat": "evidence",
        "label": "All 5 pollutant types evaluated",
        "required": True,
        "check_id": "all_pollutants_covered",
    },
    {
        "id": "cl_sample_locations",
        "cat": "evidence",
        "label": "Sample locations documented (floor/room)",
        "required": False,
        "check_id": None,
    },
    {
        "id": "cl_threshold_assessment",
        "cat": "evidence",
        "label": "Threshold exceedance assessed for all samples",
        "required": False,
        "check_id": None,
    },
    # Process (5 items)
    {
        "id": "cl_responsible",
        "cat": "process",
        "label": "Responsible parties assigned",
        "required": True,
        "check_id": "responsible_parties",
    },
    {
        "id": "cl_timeline",
        "cat": "process",
        "label": "Timeline commitments documented",
        "required": False,
        "check_id": "timeline_commitments",
    },
    {
        "id": "cl_no_critical",
        "cat": "process",
        "label": "No open critical/high actions",
        "required": True,
        "check_id": "no_critical_open_actions",
    },
    {
        "id": "cl_actions_assigned",
        "cat": "process",
        "label": "All active actions assigned",
        "required": False,
        "check_id": "actions_assigned",
    },
    {
        "id": "cl_review_sign_off",
        "cat": "process",
        "label": "Final review / sign-off recorded",
        "required": False,
        "check_id": None,
    },
]

_FIX_ACTIONS: dict[str, str] = {
    "diagnostic_validated": "Validate pending diagnostics via the diagnostic detail page",
    "report_uploaded": "Upload the diagnostic report in the Documents tab",
    "lab_reports": "Upload lab analysis reports for sampled pollutants",
    "floor_plans": "Upload floor plans in Technical Plans",
    "interventions_documented": "Complete or update intervention records",
    "compliance_artefacts_current": "Create or renew compliance artefacts",
    "suva_notification": "Submit SUVA notification for asbestos findings",
    "work_categories": "Set CFST work category on positive asbestos samples",
    "waste_plan_exists": "Classify waste disposal type for positive samples",
    "samples_documented": "Complete concentration and unit for all samples",
    "risk_levels_assigned": "Assign risk level to all samples",
    "all_pollutants_covered": "Add samples for missing pollutant types",
    "responsible_parties": "Assign a responsible party to this building",
    "timeline_commitments": "Record at least 3 building events",
    "no_critical_open_actions": "Resolve open critical/high priority actions",
    "actions_assigned": "Assign owners to all active actions",
}


def _build_checklist_item(
    defn: dict,
    checks_by_id: dict[str, AuditReadinessCheck],
    data: dict,
) -> AuditChecklistItem:
    check_id = defn["check_id"]

    if check_id and check_id in checks_by_id:
        status = checks_by_id[check_id].status
        fix = _FIX_ACTIONS.get(check_id) if status != "done" else None
    else:
        # Items without a direct check: derive from data heuristics
        status = _derive_status(defn["id"], data)
        fix = None if status == "done" else f"Review and complete: {defn['label']}"

    return AuditChecklistItem(
        id=defn["id"],
        category=defn["cat"],
        label=defn["label"],
        required=defn["required"],
        status=status,
        fix_action=fix,
    )


def _derive_status(item_id: str, data: dict) -> str:
    """Heuristic status for checklist items without a direct check."""
    building = data["building"]
    if item_id == "cl_building_info":
        has_year = building.construction_year is not None
        has_type = bool(building.building_type)
        has_area = building.surface_area_m2 is not None
        if has_year and has_type and has_area:
            return "done"
        if has_year or has_type:
            return "partial"
        return "missing"
    if item_id == "cl_photo_evidence":
        photos = [d for d in data["documents"] if (d.mime_type or "").startswith("image/")]
        return "done" if photos else "missing"
    if item_id == "cl_canton_notification":
        notified = any(d.canton_notification_date for d in data["diagnostics"])
        return "done" if notified else "missing"
    if item_id == "cl_legal_basis":
        has_basis = any(a.legal_basis for a in data["artefacts"])
        return "done" if has_basis else "missing"
    if item_id == "cl_sample_locations":
        samples = data["samples"]
        if not samples:
            return "missing"
        documented = [s for s in samples if s.location_floor or s.location_room]
        if len(documented) == len(samples):
            return "done"
        return "partial" if documented else "missing"
    if item_id == "cl_threshold_assessment":
        samples = data["samples"]
        if not samples:
            return "missing"
        # threshold_exceeded is a boolean; we consider it assessed if concentration is set
        assessed = [s for s in samples if s.concentration is not None]
        if len(assessed) == len(samples):
            return "done"
        return "partial" if assessed else "missing"
    if item_id == "cl_review_sign_off":
        sign_off_events = [
            e for e in data["events"] if (e.event_type or "").lower() in ("sign_off", "review", "validation")
        ]
        return "done" if sign_off_events else "missing"
    return "missing"


async def get_audit_checklist(db: AsyncSession, building_id: UUID) -> AuditChecklist | None:
    data = await _load_building_data(db, building_id)
    if data is None:
        return None

    checks = _run_all_checks(data)
    checks_by_id = {c.id: c for c in checks}

    items = [_build_checklist_item(defn, checks_by_id, data) for defn in _CHECKLIST_DEFINITIONS]

    done_count = sum(1 for i in items if i.status == "done")
    missing_count = sum(1 for i in items if i.status == "missing")
    partial_count = sum(1 for i in items if i.status == "partial")

    return AuditChecklist(
        building_id=building_id,
        items=items,
        total_items=len(items),
        done_count=done_count,
        missing_count=missing_count,
        partial_count=partial_count,
        evaluated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN3 - simulate_audit_outcome
# ---------------------------------------------------------------------------


def _build_flags(checks: list[AuditReadinessCheck], data: dict) -> list[AuditFlag]:
    flags: list[AuditFlag] = []

    # Critical: no validated diagnostic
    diag_check = next((c for c in checks if c.id == "diagnostic_validated"), None)
    if diag_check and diag_check.status == "missing":
        flags.append(
            AuditFlag(
                id="flag_no_validated_diag",
                severity="critical",
                description="No validated diagnostic present",
                recommendation="Validate at least one diagnostic before audit",
            )
        )

    # Critical: open critical actions
    action_check = next((c for c in checks if c.id == "no_critical_open_actions"), None)
    if action_check and action_check.status == "missing":
        flags.append(
            AuditFlag(
                id="flag_critical_actions",
                severity="critical",
                description="Open critical/high priority actions remain",
                recommendation="Resolve or mitigate all critical/high actions",
            )
        )

    # Major: missing compliance artefacts
    artefact_check = next((c for c in checks if c.id == "compliance_artefacts_current"), None)
    if artefact_check and artefact_check.status in ("missing", "partial"):
        flags.append(
            AuditFlag(
                id="flag_compliance_artefacts",
                severity="major",
                description="Compliance artefacts missing or expired",
                recommendation="Create or renew required compliance artefacts",
            )
        )

    # Major: SUVA notification missing
    suva_check = next((c for c in checks if c.id == "suva_notification"), None)
    if suva_check and suva_check.status == "missing":
        flags.append(
            AuditFlag(
                id="flag_suva_missing",
                severity="major",
                description="SUVA notification not sent for positive asbestos",
                recommendation="Submit SUVA notification immediately",
            )
        )

    # Major: samples not documented
    sample_check = next((c for c in checks if c.id == "samples_documented"), None)
    if sample_check and sample_check.status == "missing":
        flags.append(
            AuditFlag(
                id="flag_no_samples",
                severity="major",
                description="No documented samples with results",
                recommendation="Complete lab analysis and document all samples",
            )
        )

    # Minor: no floor plans
    plan_check = next((c for c in checks if c.id == "floor_plans"), None)
    if plan_check and plan_check.status == "missing":
        flags.append(
            AuditFlag(
                id="flag_no_plans",
                severity="minor",
                description="No floor plans uploaded",
                recommendation="Upload floor plans to support spatial evidence",
            )
        )

    # Minor: timeline sparse
    timeline_check = next((c for c in checks if c.id == "timeline_commitments"), None)
    if timeline_check and timeline_check.status in ("missing", "partial"):
        flags.append(
            AuditFlag(
                id="flag_sparse_timeline",
                severity="minor",
                description="Sparse timeline — few events recorded",
                recommendation="Document key milestones and deadlines",
            )
        )

    # Major: no responsible party
    resp_check = next((c for c in checks if c.id == "responsible_parties"), None)
    if resp_check and resp_check.status == "missing":
        flags.append(
            AuditFlag(
                id="flag_no_responsible",
                severity="major",
                description="No responsible party assigned",
                recommendation="Assign a responsible party for audit accountability",
            )
        )

    # Major: waste plan missing
    waste_check = next((c for c in checks if c.id == "waste_plan_exists"), None)
    if waste_check and waste_check.status == "missing":
        flags.append(
            AuditFlag(
                id="flag_waste_plan",
                severity="major",
                description="Waste management plan missing for positive samples",
                recommendation="Classify waste disposal type for all positive samples",
            )
        )

    # Minor: report missing
    report_check = next((c for c in checks if c.id == "report_uploaded"), None)
    if report_check and report_check.status == "missing":
        flags.append(
            AuditFlag(
                id="flag_no_report",
                severity="minor",
                description="Diagnostic report not uploaded",
                recommendation="Upload the final diagnostic report",
            )
        )

    return flags


def _determine_outcome(score: int, flags: list[AuditFlag]) -> str:
    critical_count = sum(1 for f in flags if f.severity == "critical")
    major_count = sum(1 for f in flags if f.severity == "major")
    if critical_count > 0 or score < 40:
        return "fail"
    if major_count > 0 or score < READY_THRESHOLD:
        return "conditional"
    return "pass"


async def simulate_audit_outcome(db: AsyncSession, building_id: UUID) -> AuditSimulationResult | None:
    data = await _load_building_data(db, building_id)
    if data is None:
        return None

    checks = _run_all_checks(data)
    score = _calculate_score(checks)
    flags = _build_flags(checks, data)
    outcome = _determine_outcome(score, flags)

    recommendations: list[str] = []
    for f in flags:
        recommendations.append(f.recommendation)
    # Deduplicate preserving order
    seen: set[str] = set()
    unique_recs: list[str] = []
    for r in recommendations:
        if r not in seen:
            seen.add(r)
            unique_recs.append(r)

    return AuditSimulationResult(
        building_id=building_id,
        outcome=outcome,
        flags=flags,
        recommendations=unique_recs,
        evaluated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN4 - get_portfolio_audit_readiness
# ---------------------------------------------------------------------------


def _estimate_prep_hours(score: int) -> float:
    """Rough estimate of hours needed to reach READY_THRESHOLD from current score."""
    if score >= READY_THRESHOLD:
        return 0.0
    gap = READY_THRESHOLD - score
    # ~0.5h per percentage-point gap (heuristic)
    return round(gap * 0.5, 1)


async def get_portfolio_audit_readiness(db: AsyncSession, org_id: UUID) -> PortfolioAuditReadiness | None:
    """Evaluate audit readiness for all buildings linked to an organisation's members."""
    from app.services.building_data_loader import load_org_buildings

    buildings = await load_org_buildings(db, org_id)

    if not buildings:
        return PortfolioAuditReadiness(
            organization_id=org_id,
            average_score=0.0,
            buildings_ready=0,
            buildings_needing_prep=0,
            total_buildings=0,
            buildings=[],
            evaluated_at=datetime.now(UTC),
        )

    summaries: list[BuildingAuditSummary] = []
    for b in buildings:
        readiness = await evaluate_audit_readiness(db, b.id)
        if readiness is None:
            continue
        summaries.append(
            BuildingAuditSummary(
                building_id=b.id,
                address=b.address,
                score=readiness.score,
                ready=readiness.score >= READY_THRESHOLD,
                estimated_prep_hours=_estimate_prep_hours(readiness.score),
            )
        )

    ready_count = sum(1 for s in summaries if s.ready)
    avg_score = sum(s.score for s in summaries) / len(summaries) if summaries else 0.0

    return PortfolioAuditReadiness(
        organization_id=org_id,
        average_score=round(avg_score, 1),
        buildings_ready=ready_count,
        buildings_needing_prep=len(summaries) - ready_count,
        total_buildings=len(summaries),
        buildings=summaries,
        evaluated_at=datetime.now(UTC),
    )
