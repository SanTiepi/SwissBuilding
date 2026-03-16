"""Service for tracking regulatory deadlines on diagnostics and compliance artefacts."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.compliance_artefact import ComplianceArtefact
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.schemas.regulatory_deadline import (
    BuildingAtRisk,
    BuildingDeadlines,
    DeadlineCalendar,
    ExpiringCompliance,
    MonthDeadlines,
    PortfolioDeadlineReport,
    RegulatoryDeadline,
)

# ---------------------------------------------------------------------------
# Deadline rules
# ---------------------------------------------------------------------------

_POLLUTANT_RULES: list[dict] = [
    {
        "pollutant": "asbestos",
        "diagnostic_types": ["asbestos", "full"],
        "cycle_years": 3,
        "legal_reference": "OTConst Art. 60a, 82-86",
        "description_template": "Asbestos re-diagnosis (3-year cycle)",
        "building_filter": lambda b: b.construction_year is not None and b.construction_year < 1991,
        "missing_description": "Missing initial asbestos diagnostic (pre-1991 building)",
    },
    {
        "pollutant": "pcb",
        "diagnostic_types": ["pcb", "full"],
        "cycle_years": 5,
        "legal_reference": "ORRChim Annexe 2.15",
        "description_template": "PCB re-analysis (5-year cycle)",
        "building_filter": lambda b: b.construction_year is not None and 1955 <= b.construction_year <= 1975,
        "missing_description": "Missing initial PCB diagnostic (1955-1975 building)",
    },
    {
        "pollutant": "lead",
        "diagnostic_types": ["lead", "full"],
        "cycle_years": 5,
        "legal_reference": "ORRChim Annexe 2.18",
        "description_template": "Lead reassessment (5-year cycle)",
        "building_filter": None,
        "missing_description": "Missing initial lead assessment",
    },
    {
        "pollutant": "hap",
        "diagnostic_types": ["hap", "full"],
        "cycle_years": 5,
        "legal_reference": "OPair / LPE",
        "description_template": "HAP reassessment (5-year cycle)",
        "building_filter": None,
        "missing_description": "Missing initial HAP assessment",
    },
]

# Radon is special: only if a sample > 300 Bq/m³
_RADON_RULE = {
    "pollutant": "radon",
    "diagnostic_types": ["radon", "full"],
    "cycle_years": 10,
    "legal_reference": "ORaP Art. 110",
    "description_template": "Radon recheck (10-year cycle, >300 Bq/m³)",
    "missing_description": "Missing initial radon measurement",
}

_STATUS_ORDER = {"overdue": 0, "critical": 1, "warning": 2, "upcoming": 3, "ok": 4}


def _compute_status(due: date, today: date) -> str:
    delta = (due - today).days
    if delta < 0:
        return "overdue"
    if delta <= 30:
        return "critical"
    if delta <= 90:
        return "warning"
    if delta <= 365:
        return "upcoming"
    return "ok"


def _sort_deadlines(deadlines: list[RegulatoryDeadline]) -> list[RegulatoryDeadline]:
    return sorted(deadlines, key=lambda d: (_STATUS_ORDER.get(d.status, 99), d.due_date))


# ---------------------------------------------------------------------------
# Core: build deadlines for a single building
# ---------------------------------------------------------------------------


async def _build_deadlines_for_building(
    db: AsyncSession,
    building: Building,
    today: date | None = None,
) -> list[RegulatoryDeadline]:
    today = today or date.today()
    building_id = building.id

    # Fetch diagnostics for this building
    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(diag_result.scalars().all())

    deadlines: list[RegulatoryDeadline] = []

    # --- Standard pollutant rules ---
    for rule in _POLLUTANT_RULES:
        bfilter = rule["building_filter"]
        # If there's a building filter and it doesn't match, skip
        if bfilter is not None and not bfilter(building):
            continue

        # Find most recent matching diagnostic with a date
        matching = [
            d
            for d in diagnostics
            if d.diagnostic_type in rule["diagnostic_types"] and (d.date_report or d.date_inspection) is not None
        ]
        if matching:
            latest = max(matching, key=lambda d: d.date_report or d.date_inspection)
            diagnosis_date = latest.date_report or latest.date_inspection
            due = date(
                diagnosis_date.year + rule["cycle_years"],
                diagnosis_date.month,
                diagnosis_date.day,
            )
            deadlines.append(
                RegulatoryDeadline(
                    building_id=building_id,
                    deadline_type="re_diagnosis",
                    pollutant_type=rule["pollutant"],
                    due_date=due,
                    status=_compute_status(due, today),
                    source_diagnostic_id=latest.id,
                    description=rule["description_template"],
                    legal_reference=rule["legal_reference"],
                )
            )
        elif bfilter is not None:
            # Building is in the risk period but has no diagnostic → critical
            deadlines.append(
                RegulatoryDeadline(
                    building_id=building_id,
                    deadline_type="missing_initial",
                    pollutant_type=rule["pollutant"],
                    due_date=today,
                    status="critical",
                    source_diagnostic_id=None,
                    description=rule["missing_description"],
                    legal_reference=rule["legal_reference"],
                )
            )

    # --- Radon rule (only if sample > 300) ---
    radon_diagnostics = [
        d
        for d in diagnostics
        if d.diagnostic_type in _RADON_RULE["diagnostic_types"] and (d.date_report or d.date_inspection) is not None
    ]
    if radon_diagnostics:
        # Check if any sample has concentration > 300
        diag_ids = [d.id for d in radon_diagnostics]
        sample_result = await db.execute(
            select(Sample).where(
                Sample.diagnostic_id.in_(diag_ids),
                Sample.pollutant_type == "radon",
                Sample.concentration > 300,
            )
        )
        high_radon_samples = sample_result.scalars().all()
        if high_radon_samples:
            latest = max(radon_diagnostics, key=lambda d: d.date_report or d.date_inspection)
            diagnosis_date = latest.date_report or latest.date_inspection
            due = date(
                diagnosis_date.year + _RADON_RULE["cycle_years"],
                diagnosis_date.month,
                diagnosis_date.day,
            )
            deadlines.append(
                RegulatoryDeadline(
                    building_id=building_id,
                    deadline_type="re_diagnosis",
                    pollutant_type="radon",
                    due_date=due,
                    status=_compute_status(due, today),
                    source_diagnostic_id=latest.id,
                    description=_RADON_RULE["description_template"],
                    legal_reference=_RADON_RULE["legal_reference"],
                )
            )

    return deadlines


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def get_building_deadlines(
    db: AsyncSession,
    building_id: uuid.UUID,
    today: date | None = None,
) -> BuildingDeadlines:
    """All upcoming deadlines for a building."""
    today = today or date.today()

    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalars().first()
    if not building:
        return BuildingDeadlines(
            building_id=building_id,
            deadlines=[],
            overdue_count=0,
            critical_count=0,
            next_30_days=0,
            next_90_days=0,
        )

    deadlines = await _build_deadlines_for_building(db, building, today)
    deadlines = _sort_deadlines(deadlines)

    overdue = sum(1 for d in deadlines if d.status == "overdue")
    critical = sum(1 for d in deadlines if d.status == "critical")
    next_30 = sum(1 for d in deadlines if 0 <= (d.due_date - today).days <= 30)
    next_90 = sum(1 for d in deadlines if 0 <= (d.due_date - today).days <= 90)

    return BuildingDeadlines(
        building_id=building_id,
        deadlines=deadlines,
        overdue_count=overdue,
        critical_count=critical,
        next_30_days=next_30,
        next_90_days=next_90,
    )


async def get_portfolio_deadlines(
    db: AsyncSession,
    org_id: uuid.UUID | None = None,
    days_ahead: int = 90,
    today: date | None = None,
) -> PortfolioDeadlineReport:
    """Aggregate deadlines across buildings."""
    today = today or date.today()

    query = select(Building)
    # org_id filtering would require an org relationship; for now we just select all
    result = await db.execute(query)
    buildings = list(result.scalars().all())

    total_overdue = 0
    total_critical = 0
    upcoming_by_month: dict[str, int] = {}
    buildings_at_risk: list[BuildingAtRisk] = []

    for building in buildings:
        deadlines = await _build_deadlines_for_building(db, building, today)
        overdue = sum(1 for d in deadlines if d.status == "overdue")
        critical = sum(1 for d in deadlines if d.status == "critical")
        total_overdue += overdue
        total_critical += critical

        # Upcoming by month
        cutoff = today + timedelta(days=days_ahead)
        for d in deadlines:
            if today <= d.due_date <= cutoff:
                month_key = d.due_date.strftime("%Y-%m")
                upcoming_by_month[month_key] = upcoming_by_month.get(month_key, 0) + 1

        if overdue > 0 or critical > 0:
            sorted_dl = _sort_deadlines(deadlines)
            next_dl = sorted_dl[0].due_date if sorted_dl else None
            buildings_at_risk.append(
                BuildingAtRisk(
                    building_id=building.id,
                    address=building.address,
                    overdue_count=overdue,
                    next_deadline=next_dl,
                )
            )

    # Sort buildings_at_risk by overdue_count desc, then next_deadline asc
    buildings_at_risk.sort(key=lambda b: (-b.overdue_count, b.next_deadline or date.max))

    return PortfolioDeadlineReport(
        total_buildings=len(buildings),
        total_overdue=total_overdue,
        total_critical=total_critical,
        upcoming_by_month=upcoming_by_month,
        buildings_at_risk=buildings_at_risk,
    )


async def get_deadline_calendar(
    db: AsyncSession,
    building_id: uuid.UUID,
    year: int,
    today: date | None = None,
) -> DeadlineCalendar:
    """Monthly view of deadlines for a year."""
    today = today or date.today()

    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalars().first()

    all_deadlines: list[RegulatoryDeadline] = []
    if building:
        all_deadlines = await _build_deadlines_for_building(db, building, today)

    months: list[MonthDeadlines] = []
    for m in range(1, 13):
        month_deadlines = [d for d in all_deadlines if d.due_date.year == year and d.due_date.month == m]
        months.append(MonthDeadlines(month=m, deadlines=_sort_deadlines(month_deadlines)))

    return DeadlineCalendar(building_id=building_id, year=year, months=months)


async def check_compliance_expiry(
    db: AsyncSession,
    building_id: uuid.UUID,
    today: date | None = None,
) -> list[ExpiringCompliance]:
    """Check compliance artefacts nearing expiry (30/60/90 day windows)."""
    today = today or date.today()

    result = await db.execute(select(ComplianceArtefact).where(ComplianceArtefact.building_id == building_id))
    artefacts = list(result.scalars().all())

    items: list[ExpiringCompliance] = []
    for a in artefacts:
        # Determine expiry date
        if a.expires_at is not None:
            exp_date = a.expires_at.date() if hasattr(a.expires_at, "date") else a.expires_at
        elif a.submitted_at is not None:
            submitted = a.submitted_at.date() if hasattr(a.submitted_at, "date") else a.submitted_at
            exp_date = date(submitted.year + 2, submitted.month, submitted.day)
        else:
            continue

        days_remaining = (exp_date - today).days
        status = _compute_status(exp_date, today)

        # Only include if within 90 days or overdue
        if days_remaining <= 90:
            items.append(
                ExpiringCompliance(
                    artefact_id=a.id,
                    artefact_type=a.artefact_type,
                    expires_at=exp_date,
                    days_remaining=days_remaining,
                    status=status,
                )
            )

    items.sort(key=lambda x: x.days_remaining)
    return items
