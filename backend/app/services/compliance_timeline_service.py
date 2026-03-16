"""
SwissBuildingOS - Compliance Timeline Service

Tracks a building's regulatory compliance state over time by combining
diagnostic results, intervention completions, regulatory pack requirements,
and expiration deadlines into a unified compliance history.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.constants import ALL_POLLUTANTS, DIAGNOSTIC_VALIDITY_YEARS
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.schemas.compliance_timeline import (
    ComplianceDeadline,
    ComplianceEvent,
    ComplianceGapAnalysis,
    CompliancePeriod,
    ComplianceTimeline,
    PollutantComplianceState,
)

# ---------------------------------------------------------------------------
# Swiss regulatory constants
# ---------------------------------------------------------------------------

POLLUTANTS = list(ALL_POLLUTANTS)

# High-risk sample thresholds
HIGH_RISK_THRESHOLDS: dict[str, dict[str, float]] = {
    "asbestos": {"threshold": 0.1, "unit": "percent_weight"},
    "pcb": {"threshold": 50.0, "unit": "mg_per_kg"},
    "lead": {"threshold": 5000.0, "unit": "mg_per_kg"},
}

# Year ranges for pollutant relevance
ASBESTOS_CUTOFF_YEAR = 1991
PCB_START_YEAR = 1955
PCB_END_YEAR = 1975


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _today() -> date:
    return datetime.now(UTC).date()


def _relevant_pollutants(construction_year: int | None) -> list[str]:
    """Return pollutants relevant based on construction year."""
    if construction_year is None:
        return list(POLLUTANTS)
    relevant = []
    if construction_year < ASBESTOS_CUTOFF_YEAR:
        relevant.append("asbestos")
    if PCB_START_YEAR <= construction_year <= PCB_END_YEAR:
        relevant.append("pcb")
    # Lead, HAP, radon apply regardless of year
    relevant.extend(["lead", "hap", "radon"])
    return relevant


def _diagnostic_renewal_years(pollutant: str) -> int | None:
    """Return renewal period in years for a pollutant, or None if not applicable."""
    if pollutant in ("asbestos", "pcb"):
        return DIAGNOSTIC_VALIDITY_YEARS.get(pollutant)
    return None


def _is_pollutant_relevant(pollutant: str, construction_year: int | None) -> bool:
    """Check if a pollutant is relevant for a building's construction year."""
    if construction_year is None:
        return True
    if pollutant == "asbestos":
        return construction_year < ASBESTOS_CUTOFF_YEAR
    if pollutant == "pcb":
        return PCB_START_YEAR <= construction_year <= PCB_END_YEAR
    return True


async def _load_building(db: AsyncSession, building_id: UUID) -> Building | None:
    result = await db.execute(select(Building).where(Building.id == building_id))
    return result.scalar_one_or_none()


async def _load_diagnostics(db: AsyncSession, building_id: UUID) -> list[Diagnostic]:
    result = await db.execute(
        select(Diagnostic)
        .where(Diagnostic.building_id == building_id)
        .options(selectinload(Diagnostic.samples))
        .order_by(Diagnostic.date_report.asc().nullslast())
    )
    return list(result.scalars().all())


async def _load_interventions(db: AsyncSession, building_id: UUID) -> list[Intervention]:
    result = await db.execute(
        select(Intervention).where(Intervention.building_id == building_id).order_by(Intervention.created_at.asc())
    )
    return list(result.scalars().all())


def _has_high_risk_samples(samples: list[Sample], pollutant: str) -> bool:
    """Check if any sample for this pollutant exceeds the high-risk threshold."""
    threshold_info = HIGH_RISK_THRESHOLDS.get(pollutant)
    for s in samples:
        if s.pollutant_type and s.pollutant_type.lower() == pollutant.lower():
            if s.threshold_exceeded or (s.risk_level and s.risk_level.lower() in ("high", "critical")):
                return True
            if threshold_info and s.concentration is not None and s.concentration >= threshold_info["threshold"]:
                return True
    return False


def _latest_diagnostic_for_pollutant(
    diagnostics: list[Diagnostic], pollutant: str
) -> tuple[Diagnostic | None, date | None]:
    """Find the latest completed diagnostic that covers a given pollutant."""
    latest: Diagnostic | None = None
    latest_date: date | None = None

    for diag in diagnostics:
        if diag.status not in ("completed", "validated"):
            continue
        # Check if diagnostic covers this pollutant (via type or samples)
        covers = False
        diag_type_lower = (diag.diagnostic_type or "").lower()
        if pollutant.lower() in diag_type_lower or diag_type_lower in ("full", "avant_travaux", "avt", "renovation"):
            covers = True
        else:
            for s in diag.samples:
                if s.pollutant_type and s.pollutant_type.lower() == pollutant.lower():
                    covers = True
                    break
        if covers:
            d = diag.date_report or (diag.created_at.date() if diag.created_at else None)
            if d is not None and (latest_date is None or d > latest_date):
                latest = diag
                latest_date = d
    return latest, latest_date


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def get_pollutant_compliance_states(db: AsyncSession, building_id: UUID) -> list[PollutantComplianceState]:
    """Per-pollutant compliance status based on latest diagnostics and interventions."""
    building = await _load_building(db, building_id)
    if building is None:
        return []

    diagnostics = await _load_diagnostics(db, building_id)
    interventions = await _load_interventions(db, building_id)
    today = _today()

    relevant = _relevant_pollutants(building.construction_year)
    states: list[PollutantComplianceState] = []

    for pollutant in POLLUTANTS:
        is_relevant = pollutant in relevant
        latest_diag, latest_date = _latest_diagnostic_for_pollutant(diagnostics, pollutant)

        diagnostic_age_days: int | None = None
        if latest_date:
            diagnostic_age_days = (today - latest_date).days

        # Check for active interventions related to this pollutant
        has_active = any(
            i.status in ("planned", "in_progress")
            and i.intervention_type
            and pollutant.lower() in i.intervention_type.lower()
            for i in interventions
        )

        # Determine compliance
        renewal_years = _diagnostic_renewal_years(pollutant)
        compliant = True
        requires_action = False
        detail: str | None = None

        if not is_relevant:
            detail = f"{pollutant} not relevant for construction year {building.construction_year}"
        elif latest_diag is None:
            compliant = False
            requires_action = True
            detail = f"No completed diagnostic for {pollutant}"
        elif renewal_years and diagnostic_age_days is not None and diagnostic_age_days > renewal_years * 365:
            compliant = False
            requires_action = True
            detail = f"Diagnostic expired ({diagnostic_age_days} days old, renewal every {renewal_years} years)"
        elif latest_diag and _has_high_risk_samples(latest_diag.samples, pollutant) and not has_active:
            compliant = False
            requires_action = True
            detail = f"High-risk {pollutant} detected, no active intervention"

        states.append(
            PollutantComplianceState(
                pollutant=pollutant,
                compliant=compliant,
                last_diagnostic_date=latest_date,
                diagnostic_age_days=diagnostic_age_days,
                has_active_intervention=has_active,
                requires_action=requires_action,
                detail=detail,
            )
        )

    return states


async def get_compliance_deadlines(db: AsyncSession, building_id: UUID) -> list[ComplianceDeadline]:
    """Compute upcoming and overdue compliance deadlines."""
    building = await _load_building(db, building_id)
    if building is None:
        return []

    diagnostics = await _load_diagnostics(db, building_id)
    today = _today()
    relevant = _relevant_pollutants(building.construction_year)
    deadlines: list[ComplianceDeadline] = []

    for pollutant in relevant:
        renewal_years = _diagnostic_renewal_years(pollutant)
        if renewal_years is None:
            continue

        latest_diag, latest_date = _latest_diagnostic_for_pollutant(diagnostics, pollutant)
        if latest_date is None:
            # No diagnostic yet — deadline is now
            deadlines.append(
                ComplianceDeadline(
                    deadline_date=today,
                    regulation_ref=_regulation_ref(pollutant),
                    description=f"Initial {pollutant} diagnostic required",
                    status="overdue",
                    days_remaining=0,
                    related_diagnostic_id=None,
                )
            )
            continue

        deadline_date = latest_date + timedelta(days=renewal_years * 365)
        days_remaining = (deadline_date - today).days

        if days_remaining < 0:
            status = "overdue"
        elif days_remaining <= 90:
            status = "upcoming"
        else:
            status = "met"

        deadlines.append(
            ComplianceDeadline(
                deadline_date=deadline_date,
                regulation_ref=_regulation_ref(pollutant),
                description=f"{pollutant.capitalize()} diagnostic renewal",
                status=status,
                days_remaining=days_remaining,
                related_diagnostic_id=latest_diag.id if latest_diag else None,
            )
        )

    return deadlines


def _regulation_ref(pollutant: str) -> str:
    refs = {
        "asbestos": "OTConst Art. 60a, 82-86",
        "pcb": "ORRChim Annexe 2.15",
        "lead": "ORRChim Annexe 2.18",
        "hap": "OLED dechet special",
        "radon": "ORaP Art. 110",
    }
    return refs.get(pollutant, "")


async def analyze_compliance_gaps(db: AsyncSession, building_id: UUID) -> ComplianceGapAnalysis:
    """Identify what's missing or expired in compliance."""
    building = await _load_building(db, building_id)
    if building is None:
        return ComplianceGapAnalysis(
            building_id=building_id,
            gaps=[],
            total_gaps=0,
            critical_gaps=0,
            recommended_actions=[],
        )

    diagnostics = await _load_diagnostics(db, building_id)
    interventions = await _load_interventions(db, building_id)
    today = _today()
    relevant = _relevant_pollutants(building.construction_year)
    gaps: list[dict] = []
    recommended_actions: list[str] = []

    for pollutant in relevant:
        latest_diag, latest_date = _latest_diagnostic_for_pollutant(diagnostics, pollutant)

        # Missing diagnostic
        if latest_diag is None:
            severity = "critical" if pollutant in ("asbestos", "pcb") else "warning"
            gaps.append(
                {
                    "pollutant": pollutant,
                    "gap_type": "missing_diagnostic",
                    "description": f"No {pollutant} diagnostic on record",
                    "severity": severity,
                }
            )
            recommended_actions.append(f"Schedule {pollutant} diagnostic")
            continue

        # Expired diagnostic
        renewal_years = _diagnostic_renewal_years(pollutant)
        if renewal_years and latest_date:
            age_days = (today - latest_date).days
            if age_days > renewal_years * 365:
                gaps.append(
                    {
                        "pollutant": pollutant,
                        "gap_type": "expired_diagnostic",
                        "description": f"{pollutant.capitalize()} diagnostic expired ({age_days} days old)",
                        "severity": "critical",
                    }
                )
                recommended_actions.append(f"Renew {pollutant} diagnostic")

        # Untreated high risk
        if _has_high_risk_samples(latest_diag.samples, pollutant):
            has_active = any(
                i.status in ("planned", "in_progress")
                and i.intervention_type
                and pollutant.lower() in i.intervention_type.lower()
                for i in interventions
            )
            if not has_active:
                gaps.append(
                    {
                        "pollutant": pollutant,
                        "gap_type": "untreated_high_risk",
                        "description": f"High-risk {pollutant} samples without active intervention",
                        "severity": "critical",
                    }
                )
                recommended_actions.append(f"Plan intervention for high-risk {pollutant}")

        # Missing intervention plan for high-risk
        if _has_high_risk_samples(latest_diag.samples, pollutant):
            has_any_intervention = any(
                i.intervention_type and pollutant.lower() in i.intervention_type.lower() for i in interventions
            )
            if not has_any_intervention:
                gaps.append(
                    {
                        "pollutant": pollutant,
                        "gap_type": "missing_intervention_plan",
                        "description": f"No intervention plan for {pollutant}",
                        "severity": "warning",
                    }
                )
                recommended_actions.append(f"Create intervention plan for {pollutant}")

    critical_gaps = sum(1 for g in gaps if g["severity"] == "critical")

    return ComplianceGapAnalysis(
        building_id=building_id,
        gaps=gaps,
        total_gaps=len(gaps),
        critical_gaps=critical_gaps,
        recommended_actions=list(dict.fromkeys(recommended_actions)),  # dedupe preserving order
    )


async def get_compliance_periods(db: AsyncSession, building_id: UUID) -> list[CompliancePeriod]:
    """Reconstruct historical compliance/non-compliance periods."""
    building = await _load_building(db, building_id)
    if building is None:
        return []

    diagnostics = await _load_diagnostics(db, building_id)
    interventions = await _load_interventions(db, building_id)

    if not diagnostics:
        return [
            CompliancePeriod(
                start_date=None,
                end_date=None,
                status="unknown",
                reason="No diagnostics on record",
            )
        ]

    # Build timeline events sorted by date
    events: list[tuple[date, str, str]] = []  # (date, event_type, description)

    for diag in diagnostics:
        if diag.status not in ("completed", "validated"):
            continue
        d = diag.date_report or (diag.created_at.date() if diag.created_at else None)
        if d is None:
            continue
        has_high_risk = any(_has_high_risk_samples(diag.samples, p) for p in POLLUTANTS)
        if has_high_risk:
            events.append((d, "non_compliant", f"High-risk findings in diagnostic {diag.diagnostic_type}"))
        else:
            events.append((d, "compliant", f"Clean diagnostic {diag.diagnostic_type}"))

    for intv in interventions:
        if intv.status == "completed" and intv.date_end:
            events.append((intv.date_end, "compliant", f"Intervention completed: {intv.title}"))

    events.sort(key=lambda x: x[0])

    if not events:
        return [
            CompliancePeriod(
                start_date=None,
                end_date=None,
                status="unknown",
                reason="No completed diagnostics",
            )
        ]

    # Build periods from events
    periods: list[CompliancePeriod] = []
    current_status = events[0][1]
    current_start = events[0][0]
    current_reason = events[0][2]

    for evt_date, evt_status, evt_reason in events[1:]:
        if evt_status != current_status:
            periods.append(
                CompliancePeriod(
                    start_date=current_start,
                    end_date=evt_date,
                    status=current_status,
                    reason=current_reason,
                )
            )
            current_status = evt_status
            current_start = evt_date
            current_reason = evt_reason

    # Final open period
    periods.append(
        CompliancePeriod(
            start_date=current_start,
            end_date=None,
            status=current_status,
            reason=current_reason,
        )
    )

    return periods


async def build_compliance_timeline(db: AsyncSession, building_id: UUID, months: int = 24) -> ComplianceTimeline:
    """Build a full chronological compliance timeline."""
    building = await _load_building(db, building_id)
    if building is None:
        return ComplianceTimeline(
            building_id=building_id,
            events=[],
            deadlines=[],
            compliance_periods=[],
            current_status="unknown",
            pollutant_states=[],
        )

    diagnostics = await _load_diagnostics(db, building_id)
    interventions = await _load_interventions(db, building_id)
    today = _today()
    cutoff = today - timedelta(days=months * 30)

    # Build events
    events: list[ComplianceEvent] = []

    for diag in diagnostics:
        if diag.status not in ("completed", "validated"):
            continue
        d = diag.date_report or (diag.created_at.date() if diag.created_at else None)
        if d is None or d < cutoff:
            continue
        ts = datetime(d.year, d.month, d.day, tzinfo=UTC)
        has_high_risk = any(_has_high_risk_samples(diag.samples, p) for p in POLLUTANTS)
        severity = "critical" if has_high_risk else "info"
        events.append(
            ComplianceEvent(
                timestamp=ts,
                event_type="diagnostic_completed",
                title=f"Diagnostic completed: {diag.diagnostic_type}",
                description=diag.summary,
                severity=severity,
                metadata={"diagnostic_id": str(diag.id), "type": diag.diagnostic_type},
            )
        )

    for intv in interventions:
        d = intv.date_end or (intv.created_at.date() if intv.created_at else None)
        if d is None or d < cutoff:
            continue
        if intv.status == "completed":
            ts = datetime(d.year, d.month, d.day, tzinfo=UTC)
            events.append(
                ComplianceEvent(
                    timestamp=ts,
                    event_type="intervention_done",
                    title=f"Intervention completed: {intv.title}",
                    description=intv.description,
                    severity="info",
                    metadata={"intervention_id": str(intv.id), "type": intv.intervention_type},
                )
            )

    # Add deadline-approaching and gap events
    deadlines = await get_compliance_deadlines(db, building_id)
    for dl in deadlines:
        if dl.status == "overdue":
            ts = datetime(dl.deadline_date.year, dl.deadline_date.month, dl.deadline_date.day, tzinfo=UTC)
            if dl.deadline_date >= cutoff:
                events.append(
                    ComplianceEvent(
                        timestamp=ts,
                        event_type="compliance_gap_detected",
                        title=f"Overdue: {dl.description}",
                        description=f"Deadline was {dl.deadline_date.isoformat()}",
                        severity="critical",
                    )
                )
        elif dl.status == "upcoming":
            ts = datetime(dl.deadline_date.year, dl.deadline_date.month, dl.deadline_date.day, tzinfo=UTC)
            events.append(
                ComplianceEvent(
                    timestamp=ts,
                    event_type="deadline_approaching",
                    title=f"Upcoming: {dl.description}",
                    description=f"Due {dl.deadline_date.isoformat()} ({dl.days_remaining} days)",
                    severity="warning",
                )
            )

    events.sort(key=lambda e: e.timestamp)

    # Get other components
    pollutant_states = await get_pollutant_compliance_states(db, building_id)
    compliance_periods = await get_compliance_periods(db, building_id)

    # Determine current status
    if not pollutant_states:
        current_status = "unknown"
    elif all(ps.compliant for ps in pollutant_states):
        current_status = "compliant"
    elif all(not ps.compliant for ps in pollutant_states if ps.requires_action):
        current_status = "non_compliant"
    else:
        # Mix of compliant and non-compliant
        any_non_compliant = any(not ps.compliant for ps in pollutant_states)
        current_status = "partially_compliant" if any_non_compliant else "compliant"

    return ComplianceTimeline(
        building_id=building_id,
        events=events,
        deadlines=deadlines,
        compliance_periods=compliance_periods,
        current_status=current_status,
        pollutant_states=pollutant_states,
    )


async def get_next_compliance_actions(db: AsyncSession, building_id: UUID) -> list[dict]:
    """Return prioritized list of next actions needed to reach full compliance."""
    gap_analysis = await analyze_compliance_gaps(db, building_id)
    deadlines = await get_compliance_deadlines(db, building_id)

    actions: list[dict] = []

    # Priority 1: Overdue deadlines
    for dl in deadlines:
        if dl.status == "overdue":
            actions.append(
                {
                    "priority": 1,
                    "action": f"Renew {dl.description}",
                    "reason": f"Deadline overdue since {dl.deadline_date.isoformat()}",
                    "regulation_ref": dl.regulation_ref,
                    "category": "deadline",
                }
            )

    # Priority 2: Untreated high-risk gaps
    for gap in gap_analysis.gaps:
        if gap["gap_type"] == "untreated_high_risk":
            actions.append(
                {
                    "priority": 2,
                    "action": f"Plan intervention for {gap['pollutant']}",
                    "reason": gap["description"],
                    "regulation_ref": _regulation_ref(gap["pollutant"]),
                    "category": "intervention",
                }
            )

    # Priority 3: Missing diagnostics
    for gap in gap_analysis.gaps:
        if gap["gap_type"] == "missing_diagnostic":
            actions.append(
                {
                    "priority": 3,
                    "action": f"Schedule {gap['pollutant']} diagnostic",
                    "reason": gap["description"],
                    "regulation_ref": _regulation_ref(gap["pollutant"]),
                    "category": "diagnostic",
                }
            )

    # Priority 4: Expired diagnostics (not already covered by overdue deadlines)
    for gap in gap_analysis.gaps:
        if gap["gap_type"] == "expired_diagnostic":
            actions.append(
                {
                    "priority": 4,
                    "action": f"Renew {gap['pollutant']} diagnostic",
                    "reason": gap["description"],
                    "regulation_ref": _regulation_ref(gap["pollutant"]),
                    "category": "diagnostic",
                }
            )

    # Priority 5: Upcoming deadlines
    for dl in deadlines:
        if dl.status == "upcoming":
            actions.append(
                {
                    "priority": 5,
                    "action": f"Prepare {dl.description}",
                    "reason": f"Due in {dl.days_remaining} days ({dl.deadline_date.isoformat()})",
                    "regulation_ref": dl.regulation_ref,
                    "category": "planning",
                }
            )

    actions.sort(key=lambda a: a["priority"])
    return actions
