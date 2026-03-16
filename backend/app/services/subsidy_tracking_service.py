"""
SwissBuildingOS - Subsidy Tracking Service

Tracks public funding opportunities, subsidy eligibility, and grant
application status for building pollutant remediation. Covers federal,
cantonal (VD/GE), and municipal programs.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.organization import Organization
from app.models.sample import Sample
from app.schemas.subsidy_tracking import (
    BuildingFundingGapAnalysis,
    BuildingSubsidyEligibility,
    BuildingSubsidyStatus,
    FundingGap,
    PortfolioSubsidySummary,
    SubsidyApplication,
    SubsidyProgram,
)
from app.services.building_data_loader import load_org_buildings

# ---------------------------------------------------------------------------
# Known Swiss subsidy programs
# ---------------------------------------------------------------------------

_PROGRAMS: list[dict] = [
    {
        "program_id": "fed-batiments",
        "name": "Programme Bâtiments",
        "provider": "federal",
        "canton": None,
        "eligible_pollutants": ["asbestos", "pcb", "lead", "hap", "radon"],
        "max_amount_chf": 50000.0,
        "coverage_percentage": 40.0,
        "application_deadline": None,
        "requirements": ["Diagnostic completed", "Remediation plan approved"],
        "status": "open",
    },
    {
        "program_id": "vd-assainissement",
        "name": "Subvention assainissement",
        "provider": "cantonal",
        "canton": "VD",
        "eligible_pollutants": ["asbestos", "pcb"],
        "max_amount_chf": 30000.0,
        "coverage_percentage": 30.0,
        "application_deadline": None,
        "requirements": ["Canton VD building", "Validated diagnostic"],
        "status": "open",
    },
    {
        "program_id": "ge-prime-energie",
        "name": "Prime énergie Genève",
        "provider": "cantonal",
        "canton": "GE",
        "eligible_pollutants": ["asbestos"],
        "max_amount_chf": 20000.0,
        "coverage_percentage": 25.0,
        "application_deadline": None,
        "requirements": ["Canton GE building", "Energy audit"],
        "status": "open",
    },
    {
        "program_id": "municipal-support",
        "name": "Soutien communal assainissement",
        "provider": "municipal",
        "canton": None,
        "eligible_pollutants": ["asbestos", "pcb", "lead", "hap", "radon"],
        "max_amount_chf": 10000.0,
        "coverage_percentage": 15.0,
        "application_deadline": None,
        "requirements": ["Registered building"],
        "status": "open",
    },
]

# Cost per affected diagnostic (CHF)
_REMEDIATION_COST: dict[str, float] = {
    "asbestos": 15000.0,
    "pcb": 8000.0,
    "lead": 5000.0,
    "hap": 3000.0,
    "radon": 2000.0,
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _fetch_building(db: AsyncSession, building_id: UUID) -> Building:
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")
    return building


async def _exceeded_pollutants(db: AsyncSession, building_id: UUID) -> set[str]:
    """Return pollutant types with at least one exceeded sample in completed diagnostics."""
    stmt = (
        select(Sample.pollutant_type)
        .join(Diagnostic, Diagnostic.id == Sample.diagnostic_id)
        .where(
            Diagnostic.building_id == building_id,
            Diagnostic.status.in_(["completed", "validated"]),
            Sample.threshold_exceeded.is_(True),
            Sample.pollutant_type.isnot(None),
        )
        .distinct()
    )
    result = await db.execute(stmt)
    return {row[0] for row in result.all()}


async def _count_exceeded_diagnostics(
    db: AsyncSession,
    building_id: UUID,
    pollutant: str,
) -> int:
    """Count diagnostics with at least one exceeded sample for a given pollutant."""
    stmt = (
        select(Diagnostic.id)
        .join(Sample, Sample.diagnostic_id == Diagnostic.id)
        .where(
            Diagnostic.building_id == building_id,
            Diagnostic.status.in_(["completed", "validated"]),
            Sample.threshold_exceeded.is_(True),
            Sample.pollutant_type == pollutant,
        )
        .distinct()
    )
    result = await db.execute(stmt)
    return len(result.all())


def _match_programs(canton: str, pollutants: set[str]) -> list[SubsidyProgram]:
    """Filter known programs by canton and pollutant presence."""
    matched: list[SubsidyProgram] = []
    for prog in _PROGRAMS:
        # Canton filter: cantonal programs must match canton
        if prog["canton"] is not None and prog["canton"] != canton:
            continue
        # Check pollutant overlap
        overlap = set(prog["eligible_pollutants"]) & pollutants
        if not overlap:
            continue
        matched.append(SubsidyProgram(**prog))
    return matched


# ---------------------------------------------------------------------------
# FN1 — get_building_subsidy_eligibility
# ---------------------------------------------------------------------------


async def get_building_subsidy_eligibility(
    building_id: UUID,
    db: AsyncSession,
) -> BuildingSubsidyEligibility:
    """Determine which subsidy programs a building qualifies for."""
    building = await _fetch_building(db, building_id)
    pollutants = await _exceeded_pollutants(db, building_id)

    if not pollutants:
        return BuildingSubsidyEligibility(
            building_id=building_id,
            eligible_programs=[],
            total_potential_funding=0.0,
            recommended_priority=[],
            generated_at=datetime.now(UTC),
        )

    programs = _match_programs(building.canton, pollutants)
    total_funding = sum(p.max_amount_chf for p in programs)

    # Priority: programs with highest coverage first
    priority = [p.program_id for p in sorted(programs, key=lambda p: p.coverage_percentage, reverse=True)]

    return BuildingSubsidyEligibility(
        building_id=building_id,
        eligible_programs=programs,
        total_potential_funding=round(total_funding, 2),
        recommended_priority=priority,
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN2 — get_building_subsidy_status
# ---------------------------------------------------------------------------

_ACTION_STATUS_MAP: dict[str, str] = {
    "open": "draft",
    "in_progress": "submitted",
    "completed": "approved",
    "cancelled": "rejected",
}


async def get_building_subsidy_status(
    building_id: UUID,
    db: AsyncSession,
) -> BuildingSubsidyStatus:
    """Build subsidy application status from funding-related action items."""
    await _fetch_building(db, building_id)

    stmt = select(ActionItem).where(ActionItem.building_id == building_id)
    result = await db.execute(stmt)
    actions = result.scalars().all()

    applications: list[SubsidyApplication] = []
    total_requested = 0.0
    total_approved = 0.0
    total_disbursed = 0.0
    pending_count = 0

    for action in actions:
        at = (action.action_type or "").lower()
        if not any(kw in at for kw in ("funding", "subsidy", "grant")):
            continue

        app_status = _ACTION_STATUS_MAP.get(action.status, "draft")
        # Derive amounts from action metadata or use defaults
        amount_requested = 10000.0
        amount_approved: float | None = None

        if app_status == "approved":
            amount_approved = amount_requested
            total_approved += amount_requested
        elif app_status == "disbursed":
            amount_approved = amount_requested
            total_approved += amount_requested
            total_disbursed += amount_requested
        elif app_status in ("draft", "submitted", "under_review"):
            pending_count += 1

        total_requested += amount_requested

        applications.append(
            SubsidyApplication(
                application_id=str(action.id),
                program_name=action.title or "",
                amount_requested=amount_requested,
                amount_approved=amount_approved,
                status=app_status,
                submitted_date=action.due_date,
                decision_date=None,
            )
        )

    return BuildingSubsidyStatus(
        building_id=building_id,
        applications=applications,
        total_requested=round(total_requested, 2),
        total_approved=round(total_approved, 2),
        total_disbursed=round(total_disbursed, 2),
        pending_count=pending_count,
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN3 — analyze_funding_gap
# ---------------------------------------------------------------------------


async def analyze_funding_gap(
    building_id: UUID,
    db: AsyncSession,
) -> BuildingFundingGapAnalysis:
    """Calculate the gap between remediation cost and available subsidies per pollutant."""
    building = await _fetch_building(db, building_id)
    pollutants = await _exceeded_pollutants(db, building_id)

    if not pollutants:
        return BuildingFundingGapAnalysis(
            building_id=building_id,
            gaps=[],
            total_remediation_cost=0.0,
            total_available_funding=0.0,
            total_gap=0.0,
            funding_coverage_pct=0.0,
            generated_at=datetime.now(UTC),
        )

    programs = _match_programs(building.canton, pollutants)

    # Total program funding proportioned equally across matched pollutants
    total_program_funding = sum(p.max_amount_chf for p in programs)

    gaps: list[FundingGap] = []
    total_cost = 0.0
    total_available = 0.0

    for pt in sorted(pollutants):
        diag_count = await _count_exceeded_diagnostics(db, building_id, pt)
        cost = _REMEDIATION_COST.get(pt, 5000.0) * max(diag_count, 1)

        # Available subsidies: proportional share for this pollutant
        if len(pollutants) > 0:
            available = total_program_funding / len(pollutants)
        else:
            available = 0.0

        gap = max(cost - available, 0.0)
        gap_pct = (gap / cost * 100) if cost > 0 else 0.0

        total_cost += cost
        total_available += available

        gaps.append(
            FundingGap(
                pollutant_type=pt,
                estimated_remediation_cost=round(cost, 2),
                available_subsidies=round(available, 2),
                gap_amount=round(gap, 2),
                gap_percentage=round(gap_pct, 2),
            )
        )

    total_gap = max(total_cost - total_available, 0.0)
    coverage_pct = (total_available / total_cost * 100) if total_cost > 0 else 0.0

    return BuildingFundingGapAnalysis(
        building_id=building_id,
        gaps=gaps,
        total_remediation_cost=round(total_cost, 2),
        total_available_funding=round(total_available, 2),
        total_gap=round(total_gap, 2),
        funding_coverage_pct=round(coverage_pct, 2),
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN4 — get_portfolio_subsidy_summary
# ---------------------------------------------------------------------------


async def get_portfolio_subsidy_summary(
    org_id: UUID,
    db: AsyncSession,
) -> PortfolioSubsidySummary:
    """Aggregate subsidy eligibility across all buildings in an organization."""
    org_result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = org_result.scalar_one_or_none()
    if org is None:
        raise ValueError(f"Organization {org_id} not found")

    buildings = await load_org_buildings(db, org_id)

    empty = PortfolioSubsidySummary(
        organization_id=org_id,
        total_buildings_eligible=0,
        total_potential_funding=0.0,
        total_approved=0.0,
        total_gap=0.0,
        by_provider={},
        generated_at=datetime.now(UTC),
    )

    if not buildings:
        return empty

    total_eligible = 0
    total_funding = 0.0
    total_approved = 0.0
    total_gap = 0.0
    by_provider: dict[str, float] = {}

    for bldg in buildings:
        eligibility = await get_building_subsidy_eligibility(bldg.id, db)
        if eligibility.eligible_programs:
            total_eligible += 1
        total_funding += eligibility.total_potential_funding

        for prog in eligibility.eligible_programs:
            by_provider[prog.provider] = by_provider.get(prog.provider, 0.0) + prog.max_amount_chf

        status = await get_building_subsidy_status(bldg.id, db)
        total_approved += status.total_approved

        gap_analysis = await analyze_funding_gap(bldg.id, db)
        total_gap += gap_analysis.total_gap

    return PortfolioSubsidySummary(
        organization_id=org_id,
        total_buildings_eligible=total_eligible,
        total_potential_funding=round(total_funding, 2),
        total_approved=round(total_approved, 2),
        total_gap=round(total_gap, 2),
        by_provider={k: round(v, 2) for k, v in by_provider.items()},
        generated_at=datetime.now(UTC),
    )
