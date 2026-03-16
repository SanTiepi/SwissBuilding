"""Pydantic schemas for the compliance calendar service."""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict


class CalendarEvent(BaseModel):
    """Single calendar event (deadline, inspection, expiration, milestone, submission)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    building_id: uuid.UUID
    event_type: str  # deadline | inspection | diagnostic_expiration | intervention_milestone | authority_submission
    title: str
    date: date
    status: str  # upcoming | overdue | completed
    urgency: str  # low | medium | high | critical
    source_id: uuid.UUID | None = None
    source_type: str | None = None  # diagnostic | intervention | action | artefact
    description: str | None = None


class MonthView(BaseModel):
    """Events grouped by month."""

    model_config = ConfigDict(from_attributes=True)

    month: int
    year: int
    events: list[CalendarEvent]
    overdue_count: int = 0
    upcoming_count: int = 0


class BuildingCalendar(BaseModel):
    """Full year calendar for a single building."""

    model_config = ConfigDict(from_attributes=True)

    building_id: uuid.UUID
    year: int
    months: list[MonthView]
    total_events: int
    overdue_count: int
    upcoming_count: int


class WeekGroup(BaseModel):
    """Events grouped by ISO week."""

    model_config = ConfigDict(from_attributes=True)

    week_number: int
    year: int
    events: list[CalendarEvent]
    has_conflict: bool = False
    building_count: int = 0


class PortfolioCalendar(BaseModel):
    """Aggregated calendar across an organization's buildings."""

    model_config = ConfigDict(from_attributes=True)

    org_id: uuid.UUID | None = None
    year: int
    month: int | None = None
    weeks: list[WeekGroup]
    total_events: int
    conflict_weeks: int
    buildings_involved: int


class Reminder(BaseModel):
    """Auto-generated reminder for an upcoming deadline."""

    model_config = ConfigDict(from_attributes=True)

    event: CalendarEvent
    days_until: int
    reminder_level: str  # 30_day | 14_day | 7_day


class UpcomingDeadlines(BaseModel):
    """Sorted upcoming deadlines with reminders."""

    model_config = ConfigDict(from_attributes=True)

    building_id: uuid.UUID
    horizon_days: int
    deadlines: list[CalendarEvent]
    reminders: list[Reminder]
    total_count: int


class SchedulingConflict(BaseModel):
    """A detected scheduling conflict."""

    model_config = ConfigDict(from_attributes=True)

    conflict_type: str  # overlapping_interventions | deadline_cluster | contractor_gap | resource_bottleneck
    severity: str  # low | medium | high
    description: str
    affected_dates: list[date]
    affected_ids: list[uuid.UUID]


class ConflictReport(BaseModel):
    """Full conflict report for a building."""

    model_config = ConfigDict(from_attributes=True)

    building_id: uuid.UUID
    conflicts: list[SchedulingConflict]
    total_conflicts: int
    high_severity_count: int
