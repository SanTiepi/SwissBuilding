"""Tests for zone safety status and occupant notices."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.building import Building
from app.models.zone import Zone
from app.schemas.zone_safety import OccupantNoticeCreate, ZoneSafetyStatusCreate
from app.services.zone_safety_service import (
    assess_zone_safety,
    create_notice,
    get_active_notices,
    get_building_safety_summary,
    get_zone_safety,
    list_notices,
    publish_notice,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_building(db_session, *, building_id=None, created_by=None):
    b = Building(
        id=building_id or uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        created_by=created_by,
        status="active",
    )
    db_session.add(b)
    return b


def _make_zone(db_session, building_id, *, zone_id=None, zone_type="floor", name="Floor 1"):
    z = Zone(
        id=zone_id or uuid.uuid4(),
        building_id=building_id,
        zone_type=zone_type,
        name=name,
    )
    db_session.add(z)
    return z


# ---------------------------------------------------------------------------
# Zone Safety Status Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assess_zone_safety_creates_status(db_session, admin_user):
    """Assess zone safety creates a new current status."""
    building = _make_building(db_session, created_by=admin_user.id)
    zone = _make_zone(db_session, building.id)
    await db_session.commit()

    data = ZoneSafetyStatusCreate(
        safety_level="restricted",
        restriction_type="ppe_required",
        hazard_types=["asbestos"],
        assessment_notes="Asbestos found in ceiling tiles",
    )
    status = await assess_zone_safety(db_session, zone.id, building.id, data, assessed_by=admin_user.id)
    await db_session.commit()

    assert status.safety_level == "restricted"
    assert status.restriction_type == "ppe_required"
    assert status.hazard_types == ["asbestos"]
    assert status.is_current is True
    assert status.assessed_by == admin_user.id


@pytest.mark.asyncio
async def test_assess_zone_safety_replaces_previous(db_session, admin_user):
    """New assessment marks previous ones as non-current."""
    building = _make_building(db_session, created_by=admin_user.id)
    zone = _make_zone(db_session, building.id)
    await db_session.commit()

    data1 = ZoneSafetyStatusCreate(safety_level="hazardous", hazard_types=["pcb"])
    first = await assess_zone_safety(db_session, zone.id, building.id, data1)
    await db_session.commit()
    await db_session.refresh(first)

    data2 = ZoneSafetyStatusCreate(safety_level="safe")
    second = await assess_zone_safety(db_session, zone.id, building.id, data2)
    await db_session.commit()
    await db_session.refresh(first)
    await db_session.refresh(second)

    assert first.is_current is False
    assert second.is_current is True


@pytest.mark.asyncio
async def test_assess_zone_safety_invalid_level(db_session, admin_user):
    """Invalid safety level raises ValueError."""
    building = _make_building(db_session, created_by=admin_user.id)
    zone = _make_zone(db_session, building.id)
    await db_session.commit()

    data = ZoneSafetyStatusCreate(safety_level="unknown_level")
    with pytest.raises(ValueError, match="Invalid safety_level"):
        await assess_zone_safety(db_session, zone.id, building.id, data)


@pytest.mark.asyncio
async def test_get_zone_safety_returns_current(db_session, admin_user):
    """get_zone_safety returns only the current status."""
    building = _make_building(db_session, created_by=admin_user.id)
    zone = _make_zone(db_session, building.id)
    await db_session.commit()

    data = ZoneSafetyStatusCreate(safety_level="closed", restriction_type="no_access")
    await assess_zone_safety(db_session, zone.id, building.id, data)
    await db_session.commit()

    result = await get_zone_safety(db_session, zone.id)
    assert result is not None
    assert result.safety_level == "closed"
    assert result.is_current is True


@pytest.mark.asyncio
async def test_get_zone_safety_none_when_no_assessment(db_session, admin_user):
    """get_zone_safety returns None for a zone with no assessment."""
    result = await get_zone_safety(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_building_safety_summary(db_session, admin_user):
    """Building safety summary aggregates zone safety levels."""
    building = _make_building(db_session, created_by=admin_user.id)
    zone1 = _make_zone(db_session, building.id, name="Floor 1")
    zone2 = _make_zone(db_session, building.id, name="Floor 2")
    zone3 = _make_zone(db_session, building.id, name="Basement")
    await db_session.commit()

    await assess_zone_safety(db_session, zone1.id, building.id, ZoneSafetyStatusCreate(safety_level="safe"))
    await assess_zone_safety(db_session, zone2.id, building.id, ZoneSafetyStatusCreate(safety_level="restricted"))
    await assess_zone_safety(db_session, zone3.id, building.id, ZoneSafetyStatusCreate(safety_level="restricted"))
    await db_session.commit()

    summary = await get_building_safety_summary(db_session, building.id)
    assert summary["total_zones_assessed"] == 3
    assert summary["by_safety_level"]["safe"] == 1
    assert summary["by_safety_level"]["restricted"] == 2
    assert len(summary["zones"]) == 3


# ---------------------------------------------------------------------------
# Occupant Notice Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_notice(db_session, admin_user):
    """Create a draft notice."""
    building = _make_building(db_session, created_by=admin_user.id)
    await db_session.commit()

    data = OccupantNoticeCreate(
        notice_type="safety_alert",
        severity="warning",
        title="Asbestos Work in Progress",
        body="Floor 3 is under asbestos removal. Avoid the area.",
        audience="all_occupants",
    )
    notice = await create_notice(db_session, building.id, data, created_by=admin_user.id)
    await db_session.commit()

    assert notice.status == "draft"
    assert notice.title == "Asbestos Work in Progress"
    assert notice.severity == "warning"
    assert notice.published_at is None


@pytest.mark.asyncio
async def test_create_notice_invalid_type(db_session, admin_user):
    """Invalid notice type raises ValueError."""
    building = _make_building(db_session, created_by=admin_user.id)
    await db_session.commit()

    data = OccupantNoticeCreate(
        notice_type="invalid_type",
        severity="info",
        title="Test",
        body="Test body",
        audience="all_occupants",
    )
    with pytest.raises(ValueError, match="Invalid notice_type"):
        await create_notice(db_session, building.id, data, created_by=admin_user.id)


@pytest.mark.asyncio
async def test_create_notice_invalid_severity(db_session, admin_user):
    """Invalid severity raises ValueError."""
    building = _make_building(db_session, created_by=admin_user.id)
    await db_session.commit()

    data = OccupantNoticeCreate(
        notice_type="safety_alert",
        severity="extreme",
        title="Test",
        body="Test body",
        audience="all_occupants",
    )
    with pytest.raises(ValueError, match="Invalid severity"):
        await create_notice(db_session, building.id, data, created_by=admin_user.id)


@pytest.mark.asyncio
async def test_create_notice_invalid_audience(db_session, admin_user):
    """Invalid audience raises ValueError."""
    building = _make_building(db_session, created_by=admin_user.id)
    await db_session.commit()

    data = OccupantNoticeCreate(
        notice_type="safety_alert",
        severity="info",
        title="Test",
        body="Test body",
        audience="everyone",
    )
    with pytest.raises(ValueError, match="Invalid audience"):
        await create_notice(db_session, building.id, data, created_by=admin_user.id)


@pytest.mark.asyncio
async def test_publish_notice(db_session, admin_user):
    """Publish transitions draft to published with timestamp."""
    building = _make_building(db_session, created_by=admin_user.id)
    await db_session.commit()

    data = OccupantNoticeCreate(
        notice_type="access_restriction",
        severity="critical",
        title="Floor 2 Closed",
        body="Floor 2 is closed for hazardous material removal.",
        audience="floor_occupants",
    )
    notice = await create_notice(db_session, building.id, data, created_by=admin_user.id)
    await db_session.commit()

    published = await publish_notice(db_session, notice.id)
    await db_session.commit()

    assert published.status == "published"
    assert published.published_at is not None


@pytest.mark.asyncio
async def test_publish_notice_not_draft_raises(db_session, admin_user):
    """Cannot publish an already published notice."""
    building = _make_building(db_session, created_by=admin_user.id)
    await db_session.commit()

    data = OccupantNoticeCreate(
        notice_type="clearance",
        severity="info",
        title="Area Cleared",
        body="The area is now safe.",
        audience="all_occupants",
    )
    notice = await create_notice(db_session, building.id, data, created_by=admin_user.id)
    await db_session.commit()

    await publish_notice(db_session, notice.id)
    await db_session.commit()

    with pytest.raises(ValueError, match="Cannot publish notice"):
        await publish_notice(db_session, notice.id)


@pytest.mark.asyncio
async def test_list_notices(db_session, admin_user):
    """List notices for a building."""
    building = _make_building(db_session, created_by=admin_user.id)
    await db_session.commit()

    for i in range(3):
        data = OccupantNoticeCreate(
            notice_type="safety_alert",
            severity="info",
            title=f"Notice {i}",
            body=f"Body {i}",
            audience="all_occupants",
        )
        await create_notice(db_session, building.id, data, created_by=admin_user.id)
    await db_session.commit()

    all_notices = await list_notices(db_session, building.id)
    assert len(all_notices) == 3

    draft_notices = await list_notices(db_session, building.id, status="draft")
    assert len(draft_notices) == 3


@pytest.mark.asyncio
async def test_get_active_notices_filters_expired(db_session, admin_user):
    """Active notices excludes expired ones."""
    building = _make_building(db_session, created_by=admin_user.id)
    await db_session.commit()

    # Notice that expires in the future (active)
    data_active = OccupantNoticeCreate(
        notice_type="work_schedule",
        severity="info",
        title="Active Notice",
        body="This is active.",
        audience="all_occupants",
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    active_notice = await create_notice(db_session, building.id, data_active, created_by=admin_user.id)
    await db_session.commit()
    await publish_notice(db_session, active_notice.id)
    await db_session.commit()

    # Notice that already expired
    data_expired = OccupantNoticeCreate(
        notice_type="work_schedule",
        severity="info",
        title="Expired Notice",
        body="This has expired.",
        audience="all_occupants",
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )
    expired_notice = await create_notice(db_session, building.id, data_expired, created_by=admin_user.id)
    await db_session.commit()
    await publish_notice(db_session, expired_notice.id)
    await db_session.commit()

    # Notice with no expiry (always active)
    data_no_expiry = OccupantNoticeCreate(
        notice_type="safety_alert",
        severity="warning",
        title="Permanent Notice",
        body="No expiry.",
        audience="all_occupants",
    )
    perm_notice = await create_notice(db_session, building.id, data_no_expiry, created_by=admin_user.id)
    await db_session.commit()
    await publish_notice(db_session, perm_notice.id)
    await db_session.commit()

    # Draft notice (should not appear)
    data_draft = OccupantNoticeCreate(
        notice_type="clearance",
        severity="info",
        title="Draft Notice",
        body="Not published.",
        audience="management_only",
    )
    await create_notice(db_session, building.id, data_draft, created_by=admin_user.id)
    await db_session.commit()

    active = await get_active_notices(db_session, building.id)
    titles = {n.title for n in active}
    assert "Active Notice" in titles
    assert "Permanent Notice" in titles
    assert "Expired Notice" not in titles
    assert "Draft Notice" not in titles
    assert len(active) == 2


@pytest.mark.asyncio
async def test_zone_safety_with_notice(db_session, admin_user):
    """Zone safety + notice can be created for the same zone."""
    building = _make_building(db_session, created_by=admin_user.id)
    zone = _make_zone(db_session, building.id)
    await db_session.commit()

    # Create zone safety status
    safety_data = ZoneSafetyStatusCreate(
        safety_level="hazardous",
        restriction_type="evacuation",
        hazard_types=["asbestos", "lead"],
    )
    status = await assess_zone_safety(db_session, zone.id, building.id, safety_data)
    await db_session.commit()

    # Create a notice for the same zone
    notice_data = OccupantNoticeCreate(
        zone_id=zone.id,
        notice_type="safety_alert",
        severity="critical",
        title="Immediate Evacuation Required",
        body="Hazardous materials detected. Evacuate immediately.",
        audience="zone_occupants",
    )
    notice = await create_notice(db_session, building.id, notice_data, created_by=admin_user.id)
    await db_session.commit()

    assert status.safety_level == "hazardous"
    assert notice.zone_id == zone.id
    assert notice.severity == "critical"
