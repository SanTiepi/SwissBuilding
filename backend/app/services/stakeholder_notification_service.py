"""Stakeholder-targeted notification service.

Generates role-specific briefings, reports, and digests for different
stakeholder types: owners, diagnosticians, authorities, contractors, architects.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.diagnostic import Diagnostic
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.zone import Zone
from app.schemas.stakeholder_notification import (
    AuthorityNotificationReport,
    BuildingIdentification,
    DiagnosticianBrief,
    DigestNotification,
    OwnerBriefing,
    OwnerDecision,
    OwnerObligation,
    PendingAnalysis,
    PriorityArea,
    RegulatoryViolation,
    RemediationAction,
    SampleCoverageGap,
    StakeholderDigest,
)
from app.services.building_data_loader import load_org_buildings

POLLUTANTS = ("asbestos", "pcb", "lead", "hap", "radon")

# Equipment mapping per pollutant
_EQUIPMENT_MAP = {
    "asbestos": "Asbestos sampling kit (PPE, HEPA bags, wet wipes)",
    "pcb": "PCB wipe/core sampling kit",
    "lead": "Lead paint XRF analyzer or sampling kit",
    "hap": "HAP core sampling kit",
    "radon": "Radon dosimeter / measurement device",
}

# Regulatory references per pollutant
_REGULATORY_REFS = {
    "asbestos": "OTConst Art. 60a, 82-86",
    "pcb": "ORRChim Annexe 2.15 (> 50 mg/kg)",
    "lead": "ORRChim Annexe 2.18 (> 5000 mg/kg)",
    "hap": "OLED (waste classification)",
    "radon": "ORaP Art. 110 (300/1000 Bq/m3)",
}

# Hours estimate per pending diagnostic
_HOURS_PER_DIAGNOSTIC = 4.0
_HOURS_PER_GAP = 1.5

VALID_DIGEST_ROLES = ("owner", "diagnostician", "authority", "contractor", "architect")


def _risk_level_from_probability(prob: float | None) -> str:
    if prob is None:
        return "unknown"
    if prob >= 0.75:
        return "critical"
    if prob >= 0.5:
        return "high"
    if prob >= 0.25:
        return "medium"
    return "low"


def _determine_urgency(
    high_risk_count: int,
    open_actions: int,
    overdue_count: int,
) -> str:
    if high_risk_count >= 2 or overdue_count >= 3:
        return "critical"
    if high_risk_count >= 1 or overdue_count >= 1:
        return "urgent"
    if open_actions >= 2:
        return "attention_needed"
    return "routine"


# ---------------------------------------------------------------------------
# FN1: Owner briefing
# ---------------------------------------------------------------------------


async def generate_owner_briefing(
    building_id: UUID,
    db: AsyncSession,
) -> OwnerBriefing | None:
    """Generate an owner-focused briefing with simple language."""
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return None

    now = datetime.now(UTC)

    # Risk scores
    risk_result = await db.execute(select(BuildingRiskScore).where(BuildingRiskScore.building_id == building_id))
    risk = risk_result.scalar_one_or_none()

    risk_parts: list[str] = []
    high_risk_count = 0
    if risk:
        for pollutant in POLLUTANTS:
            prob = getattr(risk, f"{pollutant}_probability", None)
            level = _risk_level_from_probability(prob)
            if level in ("high", "critical"):
                high_risk_count += 1
                risk_parts.append(f"{pollutant} ({level})")

    if risk_parts:
        risk_overview = (
            f"Your building has elevated risk for: {', '.join(risk_parts)}. "
            f"Professional assessment and remediation may be required."
        )
    elif risk:
        risk_overview = "Your building shows low overall pollutant risk based on current data."
    else:
        risk_overview = "No risk assessment available yet. A diagnostic is recommended."

    # Upcoming obligations from open actions with due dates
    actions_result = await db.execute(
        select(ActionItem)
        .where(
            ActionItem.building_id == building_id,
            ActionItem.status == "open",
        )
        .order_by(ActionItem.priority.desc())
    )
    actions = list(actions_result.scalars().all())

    obligations: list[OwnerObligation] = []
    overdue_count = 0
    for a in actions:
        if a.due_date:
            obligations.append(
                OwnerObligation(
                    title=a.title,
                    due_date=str(a.due_date),
                    description=a.description,
                )
            )
            if a.due_date < now.date():
                overdue_count += 1

    # Cost forecast from positive samples
    diag_ids_result = await db.execute(select(Diagnostic.id).where(Diagnostic.building_id == building_id))
    diag_ids = [row[0] for row in diag_ids_result.all()]

    cost_forecast = 0.0
    if diag_ids:
        exceeded_result = await db.execute(
            select(func.count())
            .select_from(Sample)
            .where(
                Sample.diagnostic_id.in_(diag_ids),
                Sample.threshold_exceeded.is_(True),
            )
        )
        exceeded_count = exceeded_result.scalar() or 0
        cost_forecast = exceeded_count * 12000.0  # avg CHF per positive sample

    # Recommended decisions
    decisions: list[OwnerDecision] = []
    if not diag_ids:
        decisions.append(
            OwnerDecision(
                title="Schedule initial diagnostic",
                rationale="No diagnostic exists for this building — required before renovation.",
                priority="high",
            )
        )
    if high_risk_count > 0:
        decisions.append(
            OwnerDecision(
                title="Engage remediation contractor",
                rationale=f"{high_risk_count} pollutant(s) at elevated risk require professional intervention.",
                priority="critical",
            )
        )
    if overdue_count > 0:
        decisions.append(
            OwnerDecision(
                title="Address overdue actions",
                rationale=f"{overdue_count} action(s) are past their due date.",
                priority="urgent" if overdue_count > 1 else "high",
            )
        )

    urgency = _determine_urgency(high_risk_count, len(actions), overdue_count)

    return OwnerBriefing(
        building_id=building.id,
        generated_at=now,
        risk_overview=risk_overview,
        upcoming_obligations=obligations,
        cost_forecast=cost_forecast,
        recommended_decisions=decisions,
        urgency_level=urgency,
    )


# ---------------------------------------------------------------------------
# FN2: Diagnostician brief
# ---------------------------------------------------------------------------


async def generate_diagnostician_brief(
    building_id: UUID,
    db: AsyncSession,
) -> DiagnosticianBrief | None:
    """Generate a diagnostician-focused brief for fieldwork planning."""
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return None

    now = datetime.now(UTC)

    # Pending analyses: diagnostics not yet completed
    diag_result = await db.execute(
        select(Diagnostic).where(
            Diagnostic.building_id == building_id,
            Diagnostic.status.in_(["draft", "in_progress"]),
        )
    )
    pending_diags = list(diag_result.scalars().all())
    pending_analyses = [
        PendingAnalysis(
            diagnostic_id=d.id,
            diagnostic_type=d.diagnostic_type,
            status=d.status,
            building_address=building.address,
        )
        for d in pending_diags
    ]

    # All diagnostics for sample coverage analysis
    all_diag_result = await db.execute(select(Diagnostic.id).where(Diagnostic.building_id == building_id))
    all_diag_ids = [row[0] for row in all_diag_result.all()]

    # Sampled pollutant types
    sampled_pollutants: set[str] = set()
    if all_diag_ids:
        sampled_result = await db.execute(
            select(Sample.pollutant_type).where(Sample.diagnostic_id.in_(all_diag_ids)).distinct()
        )
        sampled_pollutants = {row[0] for row in sampled_result.all() if row[0]}

    # Zones for this building
    zones_result = await db.execute(select(Zone).where(Zone.building_id == building_id))
    zones = list(zones_result.scalars().all())
    zone_names = [z.name for z in zones] if zones else ["(no zones defined)"]

    # Sample coverage gaps: pollutants not sampled x zones
    coverage_gaps: list[SampleCoverageGap] = []
    uncovered_pollutants = set(POLLUTANTS) - sampled_pollutants
    for pollutant in sorted(uncovered_pollutants):
        for zone_name in zone_names:
            coverage_gaps.append(
                SampleCoverageGap(
                    pollutant_type=pollutant,
                    uncovered_zone=zone_name,
                )
            )

    # Equipment needed based on uncovered + pending pollutant types
    equipment_needed: list[str] = []
    relevant_pollutants = uncovered_pollutants
    for d in pending_diags:
        # Check what the diagnostic type maps to
        dtype = d.diagnostic_type.lower()
        for p in POLLUTANTS:
            if p in dtype:
                relevant_pollutants.add(p)
    if not relevant_pollutants:
        relevant_pollutants = set(POLLUTANTS)

    for p in sorted(relevant_pollutants):
        equip = _EQUIPMENT_MAP.get(p)
        if equip:
            equipment_needed.append(equip)

    # Estimated fieldwork hours
    estimated_hours = len(pending_diags) * _HOURS_PER_DIAGNOSTIC + len(coverage_gaps) * _HOURS_PER_GAP
    estimated_hours = max(estimated_hours, 2.0)  # minimum 2 hours

    # Priority areas from risk scores
    priority_areas: list[PriorityArea] = []
    risk_result = await db.execute(select(BuildingRiskScore).where(BuildingRiskScore.building_id == building_id))
    risk = risk_result.scalar_one_or_none()
    if risk:
        for pollutant in POLLUTANTS:
            prob = getattr(risk, f"{pollutant}_probability", None)
            level = _risk_level_from_probability(prob)
            if level in ("high", "critical"):
                priority_areas.append(
                    PriorityArea(
                        area=f"{pollutant} assessment",
                        reason=f"Risk level is {level} — priority sampling required",
                        risk_level=level,
                    )
                )

    return DiagnosticianBrief(
        building_id=building.id,
        generated_at=now,
        pending_analyses=pending_analyses,
        sample_coverage_gaps=coverage_gaps,
        equipment_needed=equipment_needed,
        estimated_fieldwork_hours=estimated_hours,
        priority_areas=priority_areas,
    )


# ---------------------------------------------------------------------------
# FN3: Authority report
# ---------------------------------------------------------------------------


async def generate_authority_report(
    building_id: UUID,
    db: AsyncSession,
) -> AuthorityNotificationReport | None:
    """Generate an authority-focused compliance notification report."""
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return None

    now = datetime.now(UTC)

    # Building identification
    identification = BuildingIdentification(
        building_id=building.id,
        egid=building.egid,
        address=building.address,
        canton=building.canton,
    )

    # Diagnostics and samples
    diag_ids_result = await db.execute(select(Diagnostic.id).where(Diagnostic.building_id == building_id))
    diag_ids = [row[0] for row in diag_ids_result.all()]

    # Regulatory violations from threshold-exceeded samples
    violations: list[RegulatoryViolation] = []
    if diag_ids:
        exceeded_samples_result = await db.execute(
            select(Sample).where(
                Sample.diagnostic_id.in_(diag_ids),
                Sample.threshold_exceeded.is_(True),
            )
        )
        exceeded_samples = list(exceeded_samples_result.scalars().all())

        for s in exceeded_samples:
            pollutant = s.pollutant_type or "unknown"
            reg_ref = _REGULATORY_REFS.get(pollutant, "Swiss building regulations")
            location = s.location_detail or s.location_room or s.location_floor or "unspecified location"
            concentration_str = f"{s.concentration} {s.unit}" if s.concentration else "above threshold"

            violations.append(
                RegulatoryViolation(
                    regulation=reg_ref,
                    violation=f"{pollutant.title()} at {concentration_str} in {location}",
                    severity="critical" if s.risk_level in ("high", "critical") else "high",
                )
            )

    # Required remediation actions
    actions_result = await db.execute(
        select(ActionItem)
        .where(
            ActionItem.building_id == building_id,
            ActionItem.status == "open",
        )
        .order_by(ActionItem.priority.desc())
    )
    actions = list(actions_result.scalars().all())
    remediation_actions = [
        RemediationAction(
            title=a.title,
            priority=a.priority,
            status=a.status,
            due_date=str(a.due_date) if a.due_date else None,
        )
        for a in actions
    ]

    # Compliance status summary
    if violations:
        compliance_summary = (
            f"NON-COMPLIANT: {len(violations)} regulatory violation(s) identified. Immediate remediation required."
        )
    elif diag_ids:
        compliance_summary = "COMPLIANT: No threshold exceedances detected in available diagnostics."
    else:
        compliance_summary = "UNKNOWN: No diagnostics available for compliance assessment."

    # Deadline status
    overdue_count = sum(1 for a in actions if a.due_date and a.due_date < now.date())
    if overdue_count > 0:
        deadline_status = f"OVERDUE: {overdue_count} action(s) past deadline"
    elif actions:
        deadline_status = "ON TRACK: All actions within deadlines"
    else:
        deadline_status = "NO DEADLINES: No pending actions"

    return AuthorityNotificationReport(
        building_id=building.id,
        generated_at=now,
        compliance_status_summary=compliance_summary,
        regulatory_violations=violations,
        required_remediation_actions=remediation_actions,
        deadline_status=deadline_status,
        building_identification=identification,
    )


# ---------------------------------------------------------------------------
# FN4: Stakeholder digest
# ---------------------------------------------------------------------------


async def get_stakeholder_digest(
    org_id: UUID,
    role: str,
    db: AsyncSession,
) -> StakeholderDigest | None:
    """Generate a role-filtered digest of notifications across org buildings."""
    # Verify org exists
    org_result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = org_result.scalar_one_or_none()
    if not org:
        return None

    now = datetime.now(UTC)

    buildings = await load_org_buildings(db, org_id)

    notifications: list[DigestNotification] = []

    for building in buildings:
        # Risk-based notifications
        risk_result = await db.execute(select(BuildingRiskScore).where(BuildingRiskScore.building_id == building.id))
        risk = risk_result.scalar_one_or_none()

        if risk:
            for pollutant in POLLUTANTS:
                prob = getattr(risk, f"{pollutant}_probability", None)
                level = _risk_level_from_probability(prob)
                if level in ("high", "critical") and role in ("owner", "authority", "architect"):
                    notifications.append(
                        DigestNotification(
                            building_id=building.id,
                            building_address=building.address,
                            category="risk",
                            message=f"{pollutant.title()} risk is {level}",
                            priority=level,
                        )
                    )

        # Open actions
        actions_result = await db.execute(
            select(ActionItem).where(
                ActionItem.building_id == building.id,
                ActionItem.status == "open",
            )
        )
        open_actions = list(actions_result.scalars().all())

        for a in open_actions:
            if role == "contractor" and a.action_type in (
                "remediation",
                "removal",
                "encapsulation",
            ):
                notifications.append(
                    DigestNotification(
                        building_id=building.id,
                        building_address=building.address,
                        category="action",
                        message=f"Action required: {a.title}",
                        priority=a.priority,
                    )
                )
            elif role == "owner":
                notifications.append(
                    DigestNotification(
                        building_id=building.id,
                        building_address=building.address,
                        category="action",
                        message=f"Action pending: {a.title}",
                        priority=a.priority,
                    )
                )
            elif role == "authority" and a.priority in ("high", "critical"):
                notifications.append(
                    DigestNotification(
                        building_id=building.id,
                        building_address=building.address,
                        category="compliance",
                        message=f"High-priority action: {a.title}",
                        priority=a.priority,
                    )
                )

        # Pending diagnostics for diagnostician role
        if role == "diagnostician":
            pending_result = await db.execute(
                select(Diagnostic).where(
                    Diagnostic.building_id == building.id,
                    Diagnostic.status.in_(["draft", "in_progress"]),
                )
            )
            pending = list(pending_result.scalars().all())
            for d in pending:
                notifications.append(
                    DigestNotification(
                        building_id=building.id,
                        building_address=building.address,
                        category="fieldwork",
                        message=f"Pending {d.diagnostic_type} diagnostic ({d.status})",
                        priority="medium",
                    )
                )

    # Sort by priority
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    notifications.sort(key=lambda n: priority_order.get(n.priority, 4))

    return StakeholderDigest(
        organization_id=org_id,
        role=role,
        generated_at=now,
        notifications=notifications,
        total_buildings=len(buildings),
        total_notifications=len(notifications),
    )
