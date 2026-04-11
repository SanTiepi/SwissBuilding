"""DefectShield — DefectTimeline model tests.

Tests CRUD, defaults, and field behavior for the DefectTimeline model.
"""

import uuid
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select

from app.models.defect_timeline import DefectTimeline


@pytest.mark.asyncio
async def test_defect_timeline_creation(db_session, sample_building):
    """Test creating a DefectTimeline instance with all fields."""
    defect = DefectTimeline(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        defect_type="Asbestos in insulation",
        discovery_date=date(2026, 4, 1),
        notification_deadline=date(2026, 5, 31),
        status="open",
        severity="high",
        description="Asbestos detected in roof insulation during diagnostic",
        responsible_party="Building owner",
        legal_reference="art. 367 al. 1bis CO",
    )
    db_session.add(defect)
    await db_session.commit()

    result = await db_session.execute(select(DefectTimeline).where(DefectTimeline.id == defect.id))
    retrieved = result.scalar_one()
    assert retrieved.building_id == sample_building.id
    assert retrieved.defect_type == "Asbestos in insulation"
    assert retrieved.discovery_date == date(2026, 4, 1)
    assert retrieved.notification_deadline == date(2026, 5, 31)
    assert retrieved.status == "open"
    assert retrieved.severity == "high"
    assert retrieved.description == "Asbestos detected in roof insulation during diagnostic"
    assert retrieved.responsible_party == "Building owner"
    assert retrieved.legal_reference == "art. 367 al. 1bis CO"


@pytest.mark.asyncio
async def test_defect_timeline_default_values(db_session, sample_building):
    """Test default values: status=open, severity=medium, legal_reference=art. 367."""
    defect = DefectTimeline(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        defect_type="Lead paint",
        discovery_date=date(2026, 4, 1),
        notification_deadline=date(2026, 5, 31),
    )
    db_session.add(defect)
    await db_session.commit()

    result = await db_session.execute(select(DefectTimeline).where(DefectTimeline.id == defect.id))
    retrieved = result.scalar_one()
    assert retrieved.status == "open"
    assert retrieved.severity == "medium"
    assert retrieved.legal_reference == "art. 367 al. 1bis CO"
    assert retrieved.notification_sent_at is None
    assert retrieved.responsible_party is None
    assert retrieved.description is None
    assert retrieved.metadata_json is None


@pytest.mark.asyncio
async def test_defect_timeline_timestamps(db_session, sample_building):
    """Test that created_at and updated_at are set automatically."""
    defect = DefectTimeline(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        defect_type="Mold",
        discovery_date=date(2026, 4, 1),
        notification_deadline=date(2026, 5, 31),
    )
    db_session.add(defect)
    await db_session.commit()

    result = await db_session.execute(select(DefectTimeline).where(DefectTimeline.id == defect.id))
    retrieved = result.scalar_one()
    assert retrieved.created_at is not None
    assert retrieved.updated_at is not None


@pytest.mark.asyncio
async def test_defect_timeline_metadata_json(db_session, sample_building):
    """Test metadata JSON field stores and retrieves correctly."""
    metadata = {"inspector_notes": "Further testing needed", "photo_count": 3}
    defect = DefectTimeline(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        defect_type="Structural crack",
        discovery_date=date(2026, 4, 1),
        notification_deadline=date(2026, 5, 31),
        metadata_json=metadata,
    )
    db_session.add(defect)
    await db_session.commit()

    result = await db_session.execute(select(DefectTimeline).where(DefectTimeline.id == defect.id))
    retrieved = result.scalar_one()
    assert retrieved.metadata_json == metadata
    assert retrieved.metadata_json["inspector_notes"] == "Further testing needed"


@pytest.mark.asyncio
async def test_defect_timeline_all_severity_levels(db_session, sample_building):
    """Test all severity levels: low, medium, high, critical."""
    ids = {}
    for severity in ["low", "medium", "high", "critical"]:
        did = uuid.uuid4()
        ids[severity] = did
        db_session.add(
            DefectTimeline(
                id=did,
                building_id=sample_building.id,
                defect_type=f"Defect-{severity}",
                discovery_date=date(2026, 4, 1),
                notification_deadline=date(2026, 5, 31),
                severity=severity,
            )
        )
    await db_session.commit()

    result = await db_session.execute(select(DefectTimeline))
    all_defects = result.scalars().all()
    severities = {d.severity for d in all_defects}
    assert severities == {"low", "medium", "high", "critical"}


@pytest.mark.asyncio
async def test_defect_timeline_all_status_values(db_session, sample_building):
    """Test all status values: open, notified, expired, resolved."""
    for status in ["open", "notified", "expired", "resolved"]:
        db_session.add(
            DefectTimeline(
                id=uuid.uuid4(),
                building_id=sample_building.id,
                defect_type=f"Defect-{status}",
                discovery_date=date(2026, 4, 1),
                notification_deadline=date(2026, 5, 31),
                status=status,
            )
        )
    await db_session.commit()

    result = await db_session.execute(select(DefectTimeline))
    statuses = {d.status for d in result.scalars().all()}
    assert statuses == {"open", "notified", "expired", "resolved"}


@pytest.mark.asyncio
async def test_defect_timeline_notification_sent_at(db_session, sample_building):
    """Test notification_sent_at field."""
    now = datetime.now(UTC)
    defect = DefectTimeline(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        defect_type="Test defect",
        discovery_date=date(2026, 4, 1),
        notification_deadline=date(2026, 5, 31),
        status="notified",
        notification_sent_at=now,
    )
    db_session.add(defect)
    await db_session.commit()

    result = await db_session.execute(select(DefectTimeline).where(DefectTimeline.id == defect.id))
    retrieved = result.scalar_one()
    assert retrieved.notification_sent_at is not None
    assert retrieved.status == "notified"


@pytest.mark.asyncio
async def test_notification_deadline_not_auto_computed(db_session, sample_building):
    """notification_deadline is a plain field, NOT auto-computed from discovery_date.

    The 60-day computation belongs in the service layer, not the model.
    """
    defect = DefectTimeline(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        defect_type="PCB contamination",
        discovery_date=date(2026, 1, 1),
        notification_deadline=date(2099, 12, 31),  # deliberately wrong — model must accept it
    )
    db_session.add(defect)
    await db_session.commit()

    result = await db_session.execute(select(DefectTimeline).where(DefectTimeline.id == defect.id))
    retrieved = result.scalar_one()
    # Model stores exactly what we gave it — no auto-computation
    assert retrieved.notification_deadline == date(2099, 12, 31)
