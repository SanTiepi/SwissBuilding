"""Tests for compliance calendar service and API."""

import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.compliance_artefact import ComplianceArtefact
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.user import User
from app.services.compliance_calendar_service import (
    detect_scheduling_conflicts,
    get_building_calendar,
    get_portfolio_calendar,
    get_upcoming_deadlines,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def cal_user(db_session):
    user = User(
        id=uuid.uuid4(),
        email="cal@test.ch",
        password_hash="$2b$12$LJ3m4ys3Lg2HEOi6N5eFJOr7Yap0C.KHleKGJT/w4W6IaN5ZU6fNi",
        first_name="Cal",
        last_name="Test",
        role="admin",
        is_active=True,
        language="fr",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def cal_building(db_session, cal_user):
    building = Building(
        id=uuid.uuid4(),
        address="Rue Calendar 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=cal_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def cal_diagnostic(db_session, cal_building):
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=cal_building.id,
        diagnostic_type="asbestos",
        status="completed",
        date_inspection=date(2025, 6, 15),
        date_report=date(2025, 7, 1),
    )
    db_session.add(diag)
    await db_session.commit()
    await db_session.refresh(diag)
    return diag


@pytest.fixture
async def cal_intervention_planned(db_session, cal_building, cal_user):
    intv = Intervention(
        id=uuid.uuid4(),
        building_id=cal_building.id,
        intervention_type="removal",
        title="Asbestos removal phase 1",
        status="planned",
        date_start=date(2026, 4, 1),
        date_end=date(2026, 4, 30),
        contractor_name="Sanacore AG",
        created_by=cal_user.id,
    )
    db_session.add(intv)
    await db_session.commit()
    await db_session.refresh(intv)
    return intv


@pytest.fixture
async def cal_action(db_session, cal_building, cal_user):
    action = ActionItem(
        id=uuid.uuid4(),
        building_id=cal_building.id,
        source_type="diagnostic",
        action_type="inspection",
        title="Schedule follow-up inspection",
        priority="high",
        status="open",
        due_date=date(2026, 5, 15),
        created_by=cal_user.id,
    )
    db_session.add(action)
    await db_session.commit()
    await db_session.refresh(action)
    return action


@pytest.fixture
async def cal_artefact(db_session, cal_building, cal_user):
    from datetime import UTC, datetime

    art = ComplianceArtefact(
        id=uuid.uuid4(),
        building_id=cal_building.id,
        artefact_type="suva_notification",
        status="submitted",
        title="SUVA notification for asbestos removal",
        submitted_at=datetime(2026, 1, 15, tzinfo=UTC),
        expires_at=datetime(2026, 12, 31, tzinfo=UTC),
        authority_name="SUVA",
        created_by=cal_user.id,
    )
    db_session.add(art)
    await db_session.commit()
    await db_session.refresh(art)
    return art


# ---------------------------------------------------------------------------
# Service tests: get_building_calendar
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_building_calendar_empty(db_session, cal_building):
    """Empty building returns 12 months with no events."""
    result = await get_building_calendar(db_session, cal_building.id, 2026)
    assert len(result.months) == 12
    assert result.total_events == 0
    assert result.building_id == cal_building.id


@pytest.mark.asyncio
async def test_building_calendar_nonexistent(db_session):
    """Non-existent building returns empty calendar."""
    fake_id = uuid.uuid4()
    result = await get_building_calendar(db_session, fake_id, 2026)
    assert result.total_events == 0
    assert result.building_id == fake_id


@pytest.mark.asyncio
async def test_building_calendar_with_diagnostic(db_session, cal_building, cal_diagnostic):
    """Diagnostic creates expiration event in correct month."""
    # asbestos validity = 3 years → 2025-07-01 + 3y = 2028-07-01
    result = await get_building_calendar(db_session, cal_building.id, 2028)
    july = result.months[6]  # month 7 = index 6
    assert july.month == 7
    assert len(july.events) >= 1
    exp_events = [e for e in july.events if e.event_type == "diagnostic_expiration"]
    assert len(exp_events) == 1
    assert exp_events[0].date == date(2028, 7, 1)


@pytest.mark.asyncio
async def test_building_calendar_with_intervention(db_session, cal_building, cal_intervention_planned):
    """Intervention creates start/end milestone events."""
    result = await get_building_calendar(db_session, cal_building.id, 2026)
    april = result.months[3]  # month 4 = index 3
    milestone_events = [e for e in april.events if e.event_type == "intervention_milestone"]
    assert len(milestone_events) == 2  # start + end


@pytest.mark.asyncio
async def test_building_calendar_with_action(db_session, cal_building, cal_action):
    """Action item creates deadline event."""
    result = await get_building_calendar(db_session, cal_building.id, 2026, today=date(2026, 3, 1))
    may = result.months[4]  # month 5 = index 4
    deadline_events = [e for e in may.events if e.event_type == "deadline"]
    assert len(deadline_events) == 1
    assert deadline_events[0].title == "Schedule follow-up inspection"


@pytest.mark.asyncio
async def test_building_calendar_with_artefact(db_session, cal_building, cal_artefact):
    """Compliance artefact creates submission + expiration events."""
    result = await get_building_calendar(db_session, cal_building.id, 2026)
    # Submission in January
    jan = result.months[0]
    sub_events = [e for e in jan.events if e.event_type == "authority_submission"]
    assert len(sub_events) == 1
    # Expiry in December
    dec = result.months[11]
    exp_events = [e for e in dec.events if e.event_type == "diagnostic_expiration"]
    assert len(exp_events) == 1


@pytest.mark.asyncio
async def test_building_calendar_overdue_count(db_session, cal_building, cal_action):
    """Overdue events are counted correctly."""
    # Set today to after the due date
    result = await get_building_calendar(db_session, cal_building.id, 2026, today=date(2026, 6, 1))
    assert result.overdue_count >= 1


# ---------------------------------------------------------------------------
# Service tests: get_portfolio_calendar
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_portfolio_calendar_empty(db_session):
    """Empty portfolio returns no weeks."""
    result = await get_portfolio_calendar(db_session, None, 2026)
    assert result.total_events == 0
    assert result.buildings_involved == 0


@pytest.mark.asyncio
async def test_portfolio_calendar_with_events(db_session, cal_building, cal_action, cal_intervention_planned):
    """Portfolio calendar groups events by week."""
    result = await get_portfolio_calendar(db_session, None, 2026, today=date(2026, 1, 1))
    assert result.total_events >= 2
    assert result.buildings_involved >= 1
    assert len(result.weeks) >= 1


@pytest.mark.asyncio
async def test_portfolio_calendar_month_filter(db_session, cal_building, cal_action, cal_intervention_planned):
    """Month filter restricts events to that month."""
    result = await get_portfolio_calendar(db_session, None, 2026, month=4, today=date(2026, 1, 1))
    for week in result.weeks:
        for event in week.events:
            assert event.date.month == 4


@pytest.mark.asyncio
async def test_portfolio_calendar_conflict_detection(db_session, cal_user):
    """Multiple deadlines in same week flag as conflict."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue Conflict 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1960,
        building_type="residential",
        created_by=cal_user.id,
        status="active",
    )
    db_session.add(building)
    # Add 3 action items in same week
    base_date = date(2026, 6, 1)  # Monday
    for i in range(3):
        action = ActionItem(
            id=uuid.uuid4(),
            building_id=building.id,
            source_type="manual",
            action_type="inspection",
            title=f"Task {i}",
            priority="high",
            status="open",
            due_date=base_date + timedelta(days=i),
            created_by=cal_user.id,
        )
        db_session.add(action)
    await db_session.commit()

    result = await get_portfolio_calendar(db_session, None, 2026, today=date(2026, 1, 1))
    assert result.conflict_weeks >= 1


# ---------------------------------------------------------------------------
# Service tests: get_upcoming_deadlines
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upcoming_deadlines_empty(db_session, cal_building):
    """No events yields empty deadlines."""
    result = await get_upcoming_deadlines(db_session, cal_building.id, today=date(2026, 1, 1))
    assert result.total_count == 0
    assert result.building_id == cal_building.id


@pytest.mark.asyncio
async def test_upcoming_deadlines_within_horizon(db_session, cal_building, cal_action):
    """Action due within horizon appears in deadlines."""
    result = await get_upcoming_deadlines(db_session, cal_building.id, days=90, today=date(2026, 4, 1))
    assert result.total_count >= 1
    dates = [d.date for d in result.deadlines]
    assert date(2026, 5, 15) in dates


@pytest.mark.asyncio
async def test_upcoming_deadlines_beyond_horizon(db_session, cal_building, cal_action):
    """Action due beyond horizon is excluded."""
    result = await get_upcoming_deadlines(db_session, cal_building.id, days=30, today=date(2026, 1, 1))
    # May 15 is >30 days from Jan 1 → should not appear
    dates = [d.date for d in result.deadlines]
    assert date(2026, 5, 15) not in dates


@pytest.mark.asyncio
async def test_upcoming_deadlines_reminders(db_session, cal_building, cal_action):
    """Reminders generated at 30/14/7 day thresholds."""
    # 8 days before due_date (May 15) → should get 14_day reminder
    result = await get_upcoming_deadlines(db_session, cal_building.id, days=90, today=date(2026, 5, 7))
    assert len(result.reminders) >= 1
    levels = [r.reminder_level for r in result.reminders]
    # 8 days until → within 14-day threshold but not within 7-day
    assert "14_day" in levels


@pytest.mark.asyncio
async def test_upcoming_deadlines_overdue_included(db_session, cal_building, cal_action):
    """Overdue events are included in deadlines."""
    result = await get_upcoming_deadlines(db_session, cal_building.id, days=90, today=date(2026, 6, 1))
    overdue = [d for d in result.deadlines if d.status == "overdue"]
    assert len(overdue) >= 1


# ---------------------------------------------------------------------------
# Service tests: detect_scheduling_conflicts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_conflicts_empty(db_session, cal_building):
    """No interventions → no conflicts."""
    result = await detect_scheduling_conflicts(db_session, cal_building.id)
    assert result.total_conflicts == 0


@pytest.mark.asyncio
async def test_overlapping_interventions(db_session, cal_building, cal_user):
    """Two overlapping planned interventions generate conflict."""
    intv1 = Intervention(
        id=uuid.uuid4(),
        building_id=cal_building.id,
        intervention_type="removal",
        title="Phase 1",
        status="planned",
        date_start=date(2026, 5, 1),
        date_end=date(2026, 5, 20),
        created_by=cal_user.id,
    )
    intv2 = Intervention(
        id=uuid.uuid4(),
        building_id=cal_building.id,
        intervention_type="encapsulation",
        title="Phase 2",
        status="planned",
        date_start=date(2026, 5, 15),
        date_end=date(2026, 6, 10),
        created_by=cal_user.id,
    )
    db_session.add_all([intv1, intv2])
    await db_session.commit()

    result = await detect_scheduling_conflicts(db_session, cal_building.id)
    overlap = [c for c in result.conflicts if c.conflict_type == "overlapping_interventions"]
    assert len(overlap) == 1
    assert result.high_severity_count >= 1


@pytest.mark.asyncio
async def test_contractor_double_booking(db_session, cal_building, cal_user):
    """Same contractor with overlapping interventions generates conflict."""
    intv1 = Intervention(
        id=uuid.uuid4(),
        building_id=cal_building.id,
        intervention_type="removal",
        title="Job A",
        status="planned",
        date_start=date(2026, 7, 1),
        date_end=date(2026, 7, 20),
        contractor_name="TestCorp",
        created_by=cal_user.id,
    )
    intv2 = Intervention(
        id=uuid.uuid4(),
        building_id=cal_building.id,
        intervention_type="removal",
        title="Job B",
        status="planned",
        date_start=date(2026, 7, 10),
        date_end=date(2026, 7, 25),
        contractor_name="TestCorp",
        created_by=cal_user.id,
    )
    db_session.add_all([intv1, intv2])
    await db_session.commit()

    result = await detect_scheduling_conflicts(db_session, cal_building.id)
    contractor_conflicts = [c for c in result.conflicts if c.conflict_type == "contractor_gap"]
    assert len(contractor_conflicts) >= 1


@pytest.mark.asyncio
async def test_deadline_cluster_detection(db_session, cal_building, cal_user):
    """3+ events in same week triggers deadline cluster."""
    base = date(2026, 9, 7)  # Monday
    for i in range(4):
        action = ActionItem(
            id=uuid.uuid4(),
            building_id=cal_building.id,
            source_type="manual",
            action_type="inspection",
            title=f"Cluster task {i}",
            priority="high",
            status="open",
            due_date=base + timedelta(days=i),
            created_by=cal_user.id,
        )
        db_session.add(action)
    await db_session.commit()

    result = await detect_scheduling_conflicts(db_session, cal_building.id, today=date(2026, 8, 1))
    clusters = [c for c in result.conflicts if c.conflict_type == "deadline_cluster"]
    assert len(clusters) >= 1


@pytest.mark.asyncio
async def test_resource_bottleneck(db_session, cal_building, cal_user):
    """3+ interventions in same month triggers resource bottleneck."""
    for i in range(3):
        intv = Intervention(
            id=uuid.uuid4(),
            building_id=cal_building.id,
            intervention_type="removal",
            title=f"Bottleneck {i}",
            status="planned",
            date_start=date(2026, 10, 1 + i * 5),
            date_end=date(2026, 10, 3 + i * 5),
            created_by=cal_user.id,
        )
        db_session.add(intv)
    await db_session.commit()

    result = await detect_scheduling_conflicts(db_session, cal_building.id)
    bottlenecks = [c for c in result.conflicts if c.conflict_type == "resource_bottleneck"]
    assert len(bottlenecks) >= 1


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_building_calendar(client: AsyncClient, auth_headers, sample_building):
    """GET /buildings/{id}/compliance-calendar/{year} returns 200."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/compliance-calendar/2026",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert data["year"] == 2026
    assert len(data["months"]) == 12


@pytest.mark.asyncio
async def test_api_portfolio_calendar(client: AsyncClient, auth_headers):
    """GET /portfolio/compliance-calendar/{year} returns 200."""
    resp = await client.get(
        "/api/v1/portfolio/compliance-calendar/2026",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["year"] == 2026
    assert "weeks" in data


@pytest.mark.asyncio
async def test_api_upcoming_deadlines(client: AsyncClient, auth_headers, sample_building):
    """GET /buildings/{id}/upcoming-deadlines returns 200."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/upcoming-deadlines",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert data["horizon_days"] == 90


@pytest.mark.asyncio
async def test_api_scheduling_conflicts(client: AsyncClient, auth_headers, sample_building):
    """GET /buildings/{id}/scheduling-conflicts returns 200."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/scheduling-conflicts",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert "conflicts" in data


@pytest.mark.asyncio
async def test_api_unauthorized(client: AsyncClient, sample_building):
    """Endpoints require authentication."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/compliance-calendar/2026",
    )
    assert resp.status_code == 403
