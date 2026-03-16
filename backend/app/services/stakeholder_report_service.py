"""Stakeholder-specific report generation service.

Generates tailored reports for four audiences:
- Owner: plain-language risk summary, costs, action plan
- Authority: regulatory compliance per pollutant, thresholds, artefacts
- Contractor: work scope, pollutant locations, CFST 6503 safety categories
- Portfolio executive: C-level KPIs, top priorities, trend arrows
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.compliance_artefact import ComplianceArtefact
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.sample import Sample
from app.schemas.stakeholder_report import (
    AuthorityArtefactStatus,
    AuthorityPollutantStatus,
    AuthorityReport,
    ContractorBriefing,
    ContractorPollutantLocation,
    ContractorSafetyRequirement,
    OwnerActionPlanItem,
    OwnerFinancialImpact,
    OwnerReport,
    OwnerRiskOverview,
    PortfolioExecutiveSummary,
    PortfolioKPIs,
    PortfolioPriorityBuilding,
)
from app.services.building_data_loader import load_org_buildings

logger = logging.getLogger(__name__)

POLLUTANTS = ("asbestos", "pcb", "lead", "hap", "radon")

# Plain-language risk descriptions for owners (no technical jargon)
_RISK_PLAIN_LANGUAGE = {
    "asbestos": {
        "critical": "Asbestos has been confirmed at dangerous levels and requires immediate professional removal.",
        "high": "There is a high probability of asbestos presence that needs urgent attention.",
        "medium": "Asbestos may be present and should be investigated before any renovation work.",
        "low": "Asbestos risk is low based on current data.",
    },
    "pcb": {
        "critical": "PCB contamination exceeds legal limits and must be addressed immediately.",
        "high": "PCB levels are concerning and require professional assessment.",
        "medium": "PCB may be present in building materials and should be tested.",
        "low": "PCB risk is low based on current data.",
    },
    "lead": {
        "critical": "Lead contamination is above legal limits and poses a health hazard.",
        "high": "Lead paint or materials are likely present and need professional evaluation.",
        "medium": "Lead may be present, especially in older paint layers.",
        "low": "Lead risk is low based on current data.",
    },
    "hap": {
        "critical": "Polycyclic aromatic hydrocarbons exceed safe levels and require remediation.",
        "high": "HAP contamination is probable and needs professional assessment.",
        "medium": "HAP may be present in certain building materials.",
        "low": "HAP risk is low based on current data.",
    },
    "radon": {
        "critical": "Radon levels exceed the mandatory action threshold of 1000 Bq/m3.",
        "high": "Radon levels exceed the reference value of 300 Bq/m3 and action is recommended.",
        "medium": "Radon levels should be measured, especially in basement areas.",
        "low": "Radon risk is low based on current data.",
    },
}

# Swiss regulatory thresholds for authority report
_THRESHOLDS = {
    "asbestos": {"threshold": 1.0, "unit": "percent_weight", "legal_ref": "FACH 2018, OTConst Art. 82"},
    "pcb": {"threshold": 50.0, "unit": "mg/kg", "legal_ref": "ORRChim Annexe 2.15"},
    "lead": {"threshold": 5000.0, "unit": "mg/kg", "legal_ref": "ORRChim Annexe 2.18"},
    "hap": {"threshold": 200.0, "unit": "mg/kg", "legal_ref": "OLED dechet special"},
    "radon": {"threshold": 300.0, "unit": "Bq/m3", "legal_ref": "ORaP Art. 110"},
}

# CFST 6503 safety categories
_CFST_DESCRIPTIONS = {
    "minor": "Minor works — standard protective measures, dust control, wet methods.",
    "medium": "Medium-risk works — containment zone, HEPA filtration, trained personnel required.",
    "major": "Major works — full encapsulation, licensed contractor, SUVA notification mandatory.",
}

# Cost estimation multipliers (CHF per sample with threshold exceeded)
_COST_PER_POSITIVE_SAMPLE = {
    "asbestos": 15000.0,
    "pcb": 12000.0,
    "lead": 8000.0,
    "hap": 10000.0,
    "radon": 5000.0,
}


def _risk_level_from_probability(prob: float | None) -> str:
    """Map a probability to a risk level string."""
    if prob is None:
        return "low"
    if prob >= 0.75:
        return "critical"
    if prob >= 0.5:
        return "high"
    if prob >= 0.25:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# FN1: Owner report
# ---------------------------------------------------------------------------


async def generate_owner_report(db: AsyncSession, building_id: UUID) -> OwnerReport | None:
    """Generate an owner-facing summary with plain language and no jargon."""
    # Load building
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return None

    now = datetime.now(UTC)

    # Risk scores
    risk_result = await db.execute(select(BuildingRiskScore).where(BuildingRiskScore.building_id == building_id))
    risk = risk_result.scalar_one_or_none()

    risk_overview: list[OwnerRiskOverview] = []
    if risk:
        for pollutant in POLLUTANTS:
            prob = getattr(risk, f"{pollutant}_probability", None)
            level = _risk_level_from_probability(prob)
            plain = _RISK_PLAIN_LANGUAGE.get(pollutant, {}).get(level, f"{pollutant.title()} risk is {level}.")
            risk_overview.append(OwnerRiskOverview(pollutant=pollutant, risk_level=level, plain_language=plain))

    # Cost estimates from positive samples
    diag_ids_result = await db.execute(select(Diagnostic.id).where(Diagnostic.building_id == building_id))
    diag_ids = [row[0] for row in diag_ids_result.all()]

    total_cost = 0.0
    cost_breakdown: list[dict] = []
    if diag_ids:
        for pollutant in POLLUTANTS:
            count_result = await db.execute(
                select(func.count())
                .select_from(Sample)
                .where(
                    Sample.diagnostic_id.in_(diag_ids),
                    Sample.pollutant_type == pollutant,
                    Sample.threshold_exceeded.is_(True),
                )
            )
            count = count_result.scalar() or 0
            if count > 0:
                cost = count * _COST_PER_POSITIVE_SAMPLE.get(pollutant, 10000.0)
                total_cost += cost
                cost_breakdown.append({"category": pollutant, "amount": cost})

    financial_impact = OwnerFinancialImpact(
        estimated_total_chf=total_cost,
        cost_range_low_chf=total_cost * 0.7,
        cost_range_high_chf=total_cost * 1.5,
        breakdown=cost_breakdown if cost_breakdown else None,
    )

    # Action plan from open action items
    actions_result = await db.execute(
        select(ActionItem)
        .where(ActionItem.building_id == building_id, ActionItem.status == "open")
        .order_by(ActionItem.priority.desc())
        .limit(10)
    )
    actions = list(actions_result.scalars().all())
    action_plan = [
        OwnerActionPlanItem(
            title=a.title,
            priority=a.priority,
            description=a.description,
            due_date=str(a.due_date) if a.due_date else None,
        )
        for a in actions
    ]

    # Executive summary
    high_risk_count = sum(1 for r in risk_overview if r.risk_level in ("high", "critical"))
    if high_risk_count > 0:
        executive_summary = (
            f"Your building at {building.address}, {building.city} has {high_risk_count} pollutant(s) "
            f"requiring attention. Estimated remediation costs range from "
            f"CHF {financial_impact.cost_range_low_chf:,.0f} to CHF {financial_impact.cost_range_high_chf:,.0f}."
        )
    elif risk_overview:
        executive_summary = (
            f"Your building at {building.address}, {building.city} shows low overall pollutant risk. "
            f"Continue monitoring and ensure diagnostics are up to date."
        )
    else:
        executive_summary = (
            f"No risk assessment data is available for {building.address}, {building.city}. "
            f"A diagnostic is recommended before any renovation work."
        )

    # Next steps
    next_steps: list[str] = []
    if not diag_ids:
        next_steps.append("Schedule a professional pollutant diagnostic for the building.")
    if high_risk_count > 0:
        next_steps.append("Contact a certified remediation contractor to discuss the action plan.")
    if action_plan:
        next_steps.append(f"Review and prioritize the {len(action_plan)} recommended actions.")
    if not next_steps:
        next_steps.append("Keep diagnostic records up to date and monitor for regulatory changes.")

    return OwnerReport(
        building_id=building.id,
        generated_at=now,
        executive_summary=executive_summary,
        risk_overview=risk_overview,
        financial_impact=financial_impact,
        action_plan=action_plan,
        next_steps=next_steps,
    )


# ---------------------------------------------------------------------------
# FN2: Authority report
# ---------------------------------------------------------------------------


async def generate_authority_report(db: AsyncSession, building_id: UUID) -> AuthorityReport | None:
    """Generate an authority-facing report with regulatory compliance details."""
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return None

    now = datetime.now(UTC)

    # Diagnostics for this building
    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(diag_result.scalars().all())
    diag_ids = [d.id for d in diagnostics]

    # Diagnostic coverage and pollutant statuses
    diagnostic_coverage: dict[str, bool] = {}
    pollutant_statuses: list[AuthorityPollutantStatus] = []

    for pollutant in POLLUTANTS:
        # Check if any diagnostic covers this pollutant (via samples)
        has_diagnostic = False
        sample_count = 0
        threshold_exceeded = False
        max_conc: float | None = None
        max_unit: str | None = None

        if diag_ids:
            samples_result = await db.execute(
                select(Sample).where(
                    Sample.diagnostic_id.in_(diag_ids),
                    Sample.pollutant_type == pollutant,
                )
            )
            samples = list(samples_result.scalars().all())
            sample_count = len(samples)
            has_diagnostic = sample_count > 0

            for s in samples:
                if s.threshold_exceeded:
                    threshold_exceeded = True
                if s.concentration is not None and (max_conc is None or s.concentration > max_conc):
                    max_conc = s.concentration
                    max_unit = s.unit

        diagnostic_coverage[pollutant] = has_diagnostic

        threshold_info = _THRESHOLDS.get(pollutant, {})
        pollutant_statuses.append(
            AuthorityPollutantStatus(
                pollutant=pollutant,
                has_diagnostic=has_diagnostic,
                sample_count=sample_count,
                threshold_exceeded=threshold_exceeded,
                max_concentration=max_conc,
                unit=max_unit or threshold_info.get("unit"),
                legal_threshold=threshold_info.get("threshold"),
                legal_reference=threshold_info.get("legal_ref"),
            )
        )

    # Compliance artefacts
    artefacts_result = await db.execute(select(ComplianceArtefact).where(ComplianceArtefact.building_id == building_id))
    artefacts = list(artefacts_result.scalars().all())
    artefact_statuses = [
        AuthorityArtefactStatus(
            artefact_type=a.artefact_type,
            status=a.status,
            title=a.title,
            submitted_at=a.submitted_at,
        )
        for a in artefacts
    ]

    # Overall compliance
    any_exceeded = any(ps.threshold_exceeded for ps in pollutant_statuses)
    any_covered = any(ps.has_diagnostic for ps in pollutant_statuses)
    if any_exceeded:
        overall_compliance = "non_compliant"
    elif any_covered and all(not ps.threshold_exceeded for ps in pollutant_statuses if ps.has_diagnostic):
        overall_compliance = "compliant"
    elif any_covered:
        overall_compliance = "partial"
    else:
        overall_compliance = "unknown"

    # Deadline compliance (check overdue actions)
    overdue_result = await db.execute(
        select(func.count())
        .select_from(ActionItem)
        .where(
            ActionItem.building_id == building_id,
            ActionItem.status == "open",
            ActionItem.due_date.isnot(None),
        )
    )
    overdue_total = overdue_result.scalar() or 0
    deadline_compliance = "no_deadlines" if overdue_total == 0 else "on_track"

    return AuthorityReport(
        building_id=building.id,
        generated_at=now,
        overall_compliance_status=overall_compliance,
        diagnostic_coverage=diagnostic_coverage,
        pollutant_statuses=pollutant_statuses,
        artefact_statuses=artefact_statuses,
        deadline_compliance=deadline_compliance,
    )


# ---------------------------------------------------------------------------
# FN3: Contractor briefing
# ---------------------------------------------------------------------------


async def generate_contractor_briefing(db: AsyncSession, building_id: UUID) -> ContractorBriefing | None:
    """Generate a contractor-facing briefing with work scope and safety requirements."""
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return None

    now = datetime.now(UTC)

    # Get all samples with threshold exceeded for this building
    diag_ids_result = await db.execute(select(Diagnostic.id).where(Diagnostic.building_id == building_id))
    diag_ids = [row[0] for row in diag_ids_result.all()]

    pollutant_locations: list[ContractorPollutantLocation] = []
    estimated_quantities: dict[str, int] = {}
    cfst_categories_seen: dict[str, set[str]] = {}  # category -> set of pollutants

    if diag_ids:
        samples_result = await db.execute(
            select(Sample).where(
                Sample.diagnostic_id.in_(diag_ids),
                Sample.threshold_exceeded.is_(True),
            )
        )
        samples = list(samples_result.scalars().all())

        for s in samples:
            pollutant_locations.append(
                ContractorPollutantLocation(
                    pollutant=s.pollutant_type or "unknown",
                    location_floor=s.location_floor,
                    location_room=s.location_room,
                    location_detail=s.location_detail,
                    material_description=s.material_description,
                    concentration=s.concentration,
                    unit=s.unit,
                    cfst_work_category=s.cfst_work_category,
                    waste_disposal_type=s.waste_disposal_type,
                )
            )

            pollutant_key = s.pollutant_type or "unknown"
            estimated_quantities[pollutant_key] = estimated_quantities.get(pollutant_key, 0) + 1

            cat = s.cfst_work_category or "minor"
            if cat not in cfst_categories_seen:
                cfst_categories_seen[cat] = set()
            cfst_categories_seen[cat].add(pollutant_key)

    # Safety requirements from CFST categories
    safety_requirements: list[ContractorSafetyRequirement] = []
    for cat in ("major", "medium", "minor"):
        if cat in cfst_categories_seen:
            safety_requirements.append(
                ContractorSafetyRequirement(
                    category=cat,
                    description=_CFST_DESCRIPTIONS.get(cat, f"CFST category: {cat}"),
                    pollutants=sorted(cfst_categories_seen[cat]),
                )
            )

    # Access constraints from interventions
    access_constraints: list[str] = []
    interv_result = await db.execute(
        select(Intervention)
        .where(
            Intervention.building_id == building_id,
            Intervention.status.in_(("planned", "in_progress")),
        )
        .limit(5)
    )
    interventions = list(interv_result.scalars().all())
    for interv in interventions:
        access_constraints.append(f"Ongoing intervention: {interv.title} ({interv.status})")
    if not access_constraints:
        access_constraints.append("No known access constraints.")

    # Work scope summary
    total_locations = len(pollutant_locations)
    if total_locations > 0:
        pollutant_types = sorted({pl.pollutant for pl in pollutant_locations})
        work_scope_summary = (
            f"Remediation of {total_locations} identified contamination point(s) "
            f"involving {', '.join(pollutant_types)} at {building.address}, {building.city}."
        )
    else:
        work_scope_summary = (
            f"No confirmed contamination points at {building.address}, {building.city}. "
            f"Pre-work diagnostic recommended."
        )

    return ContractorBriefing(
        building_id=building.id,
        generated_at=now,
        work_scope_summary=work_scope_summary,
        pollutant_locations=pollutant_locations,
        safety_requirements=safety_requirements,
        access_constraints=access_constraints,
        estimated_quantities=estimated_quantities,
    )


# ---------------------------------------------------------------------------
# FN4: Portfolio executive summary
# ---------------------------------------------------------------------------


async def generate_portfolio_executive_summary(db: AsyncSession, org_id: UUID) -> PortfolioExecutiveSummary | None:
    """Generate a C-level portfolio summary for an organization."""
    # Verify org exists
    org_result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = org_result.scalar_one_or_none()
    if not org:
        return None

    now = datetime.now(UTC)

    # Get all buildings owned by users in this org
    buildings = await load_org_buildings(db, org_id)
    total_buildings = len(buildings)

    if total_buildings == 0:
        return PortfolioExecutiveSummary(
            organization_id=org.id,
            generated_at=now,
            kpis=PortfolioKPIs(
                total_buildings=0,
                buildings_at_risk=0,
                compliance_percentage=100.0,
                estimated_total_cost_chf=0.0,
            ),
            top_priorities=[],
            trend_arrows={"risk": "stable", "compliance": "stable", "cost": "stable"},
        )

    building_ids = [b.id for b in buildings]

    # Risk scores for portfolio buildings
    risk_result = await db.execute(select(BuildingRiskScore).where(BuildingRiskScore.building_id.in_(building_ids)))
    risk_scores = {rs.building_id: rs for rs in risk_result.scalars().all()}

    buildings_at_risk = 0
    for rs in risk_scores.values():
        if rs.overall_risk_level in ("high", "critical"):
            buildings_at_risk += 1

    # Compliance: buildings with no threshold-exceeded samples are "compliant"
    compliant_count = 0
    estimated_total_cost = 0.0
    for b in buildings:
        diag_ids_result = await db.execute(select(Diagnostic.id).where(Diagnostic.building_id == b.id))
        diag_ids = [row[0] for row in diag_ids_result.all()]

        has_exceeded = False
        if diag_ids:
            exceeded_result = await db.execute(
                select(func.count())
                .select_from(Sample)
                .where(Sample.diagnostic_id.in_(diag_ids), Sample.threshold_exceeded.is_(True))
            )
            exceeded_count = exceeded_result.scalar() or 0
            if exceeded_count > 0:
                has_exceeded = True
                estimated_total_cost += exceeded_count * 12000.0  # avg cost per positive sample

        if not has_exceeded:
            compliant_count += 1

    compliance_pct = (compliant_count / total_buildings * 100.0) if total_buildings > 0 else 100.0

    kpis = PortfolioKPIs(
        total_buildings=total_buildings,
        buildings_at_risk=buildings_at_risk,
        compliance_percentage=round(compliance_pct, 1),
        estimated_total_cost_chf=estimated_total_cost,
    )

    # Top 5 priorities: buildings with highest risk + most open actions
    priority_data: list[tuple[Building, int, str]] = []
    for b in buildings:
        actions_result = await db.execute(
            select(func.count())
            .select_from(ActionItem)
            .where(ActionItem.building_id == b.id, ActionItem.status == "open")
        )
        open_actions = actions_result.scalar() or 0
        rs = risk_scores.get(b.id)
        risk_level = rs.overall_risk_level if rs else "unknown"
        priority_data.append((b, open_actions, risk_level))

    # Sort: critical/high first, then by open_actions descending
    risk_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "unknown": 4}
    priority_data.sort(key=lambda x: (risk_order.get(x[2], 4), -x[1]))

    top_priorities = [
        PortfolioPriorityBuilding(
            building_id=b.id,
            address=b.address,
            city=b.city,
            risk_level=rl,
            open_actions=oa,
        )
        for b, oa, rl in priority_data[:5]
    ]

    # Trend arrows (simplified — stable if no historical data)
    trend_arrows = {
        "risk": "up" if buildings_at_risk > total_buildings * 0.3 else "stable",
        "compliance": "down" if compliance_pct < 70.0 else "stable",
        "cost": "up" if estimated_total_cost > 500000 else "stable",
    }

    return PortfolioExecutiveSummary(
        organization_id=org.id,
        generated_at=now,
        kpis=kpis,
        top_priorities=top_priorities,
        trend_arrows=trend_arrows,
    )
