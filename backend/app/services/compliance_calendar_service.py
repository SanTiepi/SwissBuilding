"""Service for compliance calendar: building/portfolio calendars, deadlines, and conflict detection."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import DIAGNOSTIC_VALIDITY_YEARS
from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.compliance_artefact import ComplianceArtefact
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.schemas.compliance_calendar import (
    BuildingCalendar,
    CalendarEvent,
    ConflictReport,
    MonthView,
    PortfolioCalendar,
    Reminder,
    SchedulingConflict,
    UpcomingDeadlines,
    WeekGroup,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _urgency_from_days(days_until: int) -> str:
    if days_until < 0:
        return "critical"
    if days_until <= 7:
        return "high"
    if days_until <= 30:
        return "medium"
    return "low"


def _status_from_dates(event_date: date, today: date, completed: bool = False) -> str:
    if completed:
        return "completed"
    if event_date < today:
        return "overdue"
    return "upcoming"


def _make_event_id(*parts: str) -> str:
    return "-".join(str(p) for p in parts)


# ---------------------------------------------------------------------------
# Collect events for a single building
# ---------------------------------------------------------------------------


async def _collect_building_events(
    db: AsyncSession,
    building: Building,
    today: date,
) -> list[CalendarEvent]:
    """Gather all calendar events for a building from multiple sources."""
    building_id = building.id
    events: list[CalendarEvent] = []

    # 1. Diagnostic expirations
    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(diag_result.scalars().all())

    for diag in diagnostics:
        diag_date = diag.date_report or diag.date_inspection
        if diag_date is None:
            continue
        validity = DIAGNOSTIC_VALIDITY_YEARS.get(diag.diagnostic_type, 5)
        exp_date = date(diag_date.year + validity, diag_date.month, diag_date.day)
        days_until = (exp_date - today).days
        events.append(
            CalendarEvent(
                id=_make_event_id("diag-exp", diag.id),
                building_id=building_id,
                event_type="diagnostic_expiration",
                title=f"{diag.diagnostic_type.title()} diagnostic expires",
                date=exp_date,
                status=_status_from_dates(exp_date, today, diag.status == "validated"),
                urgency=_urgency_from_days(days_until),
                source_id=diag.id,
                source_type="diagnostic",
                description=f"Diagnostic {diag.diagnostic_type} from {diag_date.isoformat()} expires",
            )
        )

    # 2. Intervention milestones (start / end dates)
    intv_result = await db.execute(select(Intervention).where(Intervention.building_id == building_id))
    interventions = list(intv_result.scalars().all())

    for intv in interventions:
        completed = intv.status == "completed"
        if intv.date_start:
            days_until = (intv.date_start - today).days
            events.append(
                CalendarEvent(
                    id=_make_event_id("intv-start", intv.id),
                    building_id=building_id,
                    event_type="intervention_milestone",
                    title=f"Intervention start: {intv.title}",
                    date=intv.date_start,
                    status=_status_from_dates(intv.date_start, today, completed),
                    urgency=_urgency_from_days(days_until),
                    source_id=intv.id,
                    source_type="intervention",
                    description=f"{intv.intervention_type} intervention starts",
                )
            )
        if intv.date_end:
            days_until = (intv.date_end - today).days
            events.append(
                CalendarEvent(
                    id=_make_event_id("intv-end", intv.id),
                    building_id=building_id,
                    event_type="intervention_milestone",
                    title=f"Intervention end: {intv.title}",
                    date=intv.date_end,
                    status=_status_from_dates(intv.date_end, today, completed),
                    urgency=_urgency_from_days(days_until),
                    source_id=intv.id,
                    source_type="intervention",
                    description=f"{intv.intervention_type} intervention ends",
                )
            )

    # 3. Action item deadlines (due_date)
    action_result = await db.execute(select(ActionItem).where(ActionItem.building_id == building_id))
    actions = list(action_result.scalars().all())

    for action in actions:
        if action.due_date is None:
            continue
        days_until = (action.due_date - today).days
        completed = action.status in ("completed", "closed")
        events.append(
            CalendarEvent(
                id=_make_event_id("action", action.id),
                building_id=building_id,
                event_type="deadline",
                title=action.title,
                date=action.due_date,
                status=_status_from_dates(action.due_date, today, completed),
                urgency=_urgency_from_days(days_until),
                source_id=action.id,
                source_type="action",
                description=action.description,
            )
        )

    # 4. Compliance artefact submissions / expirations
    art_result = await db.execute(select(ComplianceArtefact).where(ComplianceArtefact.building_id == building_id))
    artefacts = list(art_result.scalars().all())

    for art in artefacts:
        # Submission event
        if art.submitted_at:
            sub_date = (
                art.submitted_at.date()
                if hasattr(art.submitted_at, "date") and callable(art.submitted_at.date)
                else art.submitted_at
            )
            events.append(
                CalendarEvent(
                    id=_make_event_id("art-sub", art.id),
                    building_id=building_id,
                    event_type="authority_submission",
                    title=f"Submission: {art.title}",
                    date=sub_date,
                    status="completed",
                    urgency="low",
                    source_id=art.id,
                    source_type="artefact",
                    description=f"Authority submission to {art.authority_name or 'authority'}",
                )
            )
        # Expiry event
        if art.expires_at:
            exp_date = (
                art.expires_at.date()
                if hasattr(art.expires_at, "date") and callable(art.expires_at.date)
                else art.expires_at
            )
            days_until = (exp_date - today).days
            events.append(
                CalendarEvent(
                    id=_make_event_id("art-exp", art.id),
                    building_id=building_id,
                    event_type="diagnostic_expiration",
                    title=f"Artefact expires: {art.title}",
                    date=exp_date,
                    status=_status_from_dates(exp_date, today),
                    urgency=_urgency_from_days(days_until),
                    source_id=art.id,
                    source_type="artefact",
                    description=f"Compliance artefact {art.artefact_type} expires",
                )
            )

    return events


# ---------------------------------------------------------------------------
# FN1: get_building_calendar
# ---------------------------------------------------------------------------


async def get_building_calendar(
    db: AsyncSession,
    building_id: uuid.UUID,
    year: int,
    today: date | None = None,
) -> BuildingCalendar:
    """Monthly calendar view for a single building."""
    today = today or date.today()

    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalars().first()

    all_events: list[CalendarEvent] = []
    if building:
        all_events = await _collect_building_events(db, building, today)

    months: list[MonthView] = []
    total_overdue = 0
    total_upcoming = 0

    for m in range(1, 13):
        month_events = sorted(
            [e for e in all_events if e.date.year == year and e.date.month == m],
            key=lambda e: e.date,
        )
        overdue = sum(1 for e in month_events if e.status == "overdue")
        upcoming = sum(1 for e in month_events if e.status == "upcoming")
        total_overdue += overdue
        total_upcoming += upcoming
        months.append(
            MonthView(
                month=m,
                year=year,
                events=month_events,
                overdue_count=overdue,
                upcoming_count=upcoming,
            )
        )

    year_events = [e for e in all_events if e.date.year == year]

    return BuildingCalendar(
        building_id=building_id,
        year=year,
        months=months,
        total_events=len(year_events),
        overdue_count=total_overdue,
        upcoming_count=total_upcoming,
    )


# ---------------------------------------------------------------------------
# FN2: get_portfolio_calendar
# ---------------------------------------------------------------------------


async def get_portfolio_calendar(
    db: AsyncSession,
    org_id: uuid.UUID | None,
    year: int,
    month: int | None = None,
    today: date | None = None,
) -> PortfolioCalendar:
    """Aggregated calendar across all org buildings, grouped by week."""
    today = today or date.today()

    # Find buildings for the org
    if org_id is not None:
        from app.services.building_data_loader import load_org_buildings

        buildings = await load_org_buildings(db, org_id)
    else:
        result = await db.execute(select(Building))
        buildings = list(result.scalars().all())

    all_events: list[CalendarEvent] = []
    building_ids_seen: set[uuid.UUID] = set()

    for building in buildings:
        events = await _collect_building_events(db, building, today)
        for e in events:
            # Filter to requested year (and month if given)
            if e.date.year != year:
                continue
            if month is not None and e.date.month != month:
                continue
            all_events.append(e)
            building_ids_seen.add(e.building_id)

    # Group by ISO week
    week_map: dict[int, list[CalendarEvent]] = defaultdict(list)
    for e in all_events:
        iso_week = e.date.isocalendar()[1]
        week_map[iso_week].append(e)

    weeks: list[WeekGroup] = []
    conflict_count = 0
    for wk in sorted(week_map.keys()):
        wk_events = sorted(week_map[wk], key=lambda e: e.date)
        # Conflict = multiple deadlines from different buildings in same week
        wk_building_ids = {e.building_id for e in wk_events}
        deadline_events = [e for e in wk_events if e.status != "completed"]
        has_conflict = len(deadline_events) >= 3 or (len(wk_building_ids) > 1 and len(deadline_events) >= 2)
        if has_conflict:
            conflict_count += 1
        weeks.append(
            WeekGroup(
                week_number=wk,
                year=year,
                events=wk_events,
                has_conflict=has_conflict,
                building_count=len(wk_building_ids),
            )
        )

    return PortfolioCalendar(
        org_id=org_id,
        year=year,
        month=month,
        weeks=weeks,
        total_events=len(all_events),
        conflict_weeks=conflict_count,
        buildings_involved=len(building_ids_seen),
    )


# ---------------------------------------------------------------------------
# FN3: get_upcoming_deadlines
# ---------------------------------------------------------------------------


async def get_upcoming_deadlines(
    db: AsyncSession,
    building_id: uuid.UUID,
    days: int = 90,
    today: date | None = None,
) -> UpcomingDeadlines:
    """Upcoming deadlines with auto-generated reminders at 30/14/7 days."""
    today = today or date.today()
    horizon = today + timedelta(days=days)

    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalars().first()

    all_events: list[CalendarEvent] = []
    if building:
        all_events = await _collect_building_events(db, building, today)

    # Filter to upcoming window (include overdue)
    deadlines = sorted(
        [e for e in all_events if e.date <= horizon and e.status != "completed"],
        key=lambda e: e.date,
    )

    # Generate reminders
    # Check from most urgent to least urgent; first match wins
    reminder_thresholds = [
        (7, "7_day"),
        (14, "14_day"),
        (30, "30_day"),
    ]

    reminders: list[Reminder] = []
    for event in deadlines:
        days_until = (event.date - today).days
        if days_until < 0:
            continue  # overdue, no reminder needed
        for threshold, level in reminder_thresholds:
            if days_until <= threshold:
                reminders.append(
                    Reminder(
                        event=event,
                        days_until=days_until,
                        reminder_level=level,
                    )
                )
                break  # only the most urgent reminder per event

    reminders.sort(key=lambda r: r.days_until)

    return UpcomingDeadlines(
        building_id=building_id,
        horizon_days=days,
        deadlines=deadlines,
        reminders=reminders,
        total_count=len(deadlines),
    )


# ---------------------------------------------------------------------------
# FN4: detect_scheduling_conflicts
# ---------------------------------------------------------------------------


async def detect_scheduling_conflicts(
    db: AsyncSession,
    building_id: uuid.UUID,
    today: date | None = None,
) -> ConflictReport:
    """Detect overlapping interventions, deadline clusters, contractor gaps."""
    today = today or date.today()

    conflicts: list[SchedulingConflict] = []

    # --- Overlapping interventions ---
    intv_result = await db.execute(
        select(Intervention).where(
            Intervention.building_id == building_id,
            Intervention.status.in_(["planned", "in_progress"]),
        )
    )
    interventions = list(intv_result.scalars().all())

    for i, a in enumerate(interventions):
        for b in interventions[i + 1 :]:
            if (
                a.date_start
                and a.date_end
                and b.date_start
                and b.date_end
                and a.date_start <= b.date_end
                and b.date_start <= a.date_end
            ):
                overlap_start = max(a.date_start, b.date_start)
                overlap_end = min(a.date_end, b.date_end)
                affected_dates = [
                    overlap_start + timedelta(days=d) for d in range((overlap_end - overlap_start).days + 1)
                ]
                conflicts.append(
                    SchedulingConflict(
                        conflict_type="overlapping_interventions",
                        severity="high",
                        description=f"Interventions overlap: '{a.title}' and '{b.title}'",
                        affected_dates=affected_dates[:30],  # cap for sanity
                        affected_ids=[a.id, b.id],
                    )
                )

    # --- Contractor availability gaps ---
    contractor_interventions: dict[str, list[Intervention]] = defaultdict(list)
    for intv in interventions:
        if intv.contractor_name and intv.date_start and intv.date_end:
            contractor_interventions[intv.contractor_name].append(intv)

    for contractor, intvs in contractor_interventions.items():
        sorted_intvs = sorted(intvs, key=lambda x: x.date_start)
        for i in range(len(sorted_intvs) - 1):
            current_end = sorted_intvs[i].date_end
            next_start = sorted_intvs[i + 1].date_start
            if current_end and next_start and next_start < current_end:
                conflicts.append(
                    SchedulingConflict(
                        conflict_type="contractor_gap",
                        severity="medium",
                        description=f"Contractor '{contractor}' double-booked",
                        affected_dates=[current_end, next_start],
                        affected_ids=[sorted_intvs[i].id, sorted_intvs[i + 1].id],
                    )
                )

    # --- Deadline clusters (3+ deadlines in same week) ---
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalars().first()
    if building:
        all_events = await _collect_building_events(db, building, today)
        future_events = [e for e in all_events if e.date >= today and e.status != "completed"]

        week_events: dict[int, list[CalendarEvent]] = defaultdict(list)
        for e in future_events:
            week_key = e.date.isocalendar()[1] + e.date.isocalendar()[0] * 100
            week_events[week_key].append(e)

        for _week_key, events in week_events.items():
            if len(events) >= 3:
                conflicts.append(
                    SchedulingConflict(
                        conflict_type="deadline_cluster",
                        severity="medium" if len(events) < 5 else "high",
                        description=f"{len(events)} events clustered in the same week",
                        affected_dates=[e.date for e in events],
                        affected_ids=[e.source_id for e in events if e.source_id],
                    )
                )

    # --- Resource bottleneck: too many planned interventions in same month ---
    planned_by_month: dict[str, list[Intervention]] = defaultdict(list)
    for intv in interventions:
        if intv.date_start:
            mk = intv.date_start.strftime("%Y-%m")
            planned_by_month[mk].append(intv)

    for month_key, intvs in planned_by_month.items():
        if len(intvs) >= 3:
            conflicts.append(
                SchedulingConflict(
                    conflict_type="resource_bottleneck",
                    severity="high",
                    description=f"{len(intvs)} interventions planned in {month_key}",
                    affected_dates=[i.date_start for i in intvs if i.date_start],
                    affected_ids=[i.id for i in intvs],
                )
            )

    high_count = sum(1 for c in conflicts if c.severity == "high")

    return ConflictReport(
        building_id=building_id,
        conflicts=conflicts,
        total_conflicts=len(conflicts),
        high_severity_count=high_count,
    )
