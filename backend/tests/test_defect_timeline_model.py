import uuid
from datetime import date, datetime

import pytest

from app.models import DefectTimeline, Building


@pytest.fixture
def test_building(db_session):
    """Create a test building."""
    building = Building(
        id=uuid.uuid4(),
        egid=1234567,
        egrid="CH123456789",
        address="123 Test Street",
        postal_code="1200",
        city="Geneva",
        canton="GE",
        building_type="residential",
        created_by=uuid.uuid4(),
    )
    db_session.add(building)
    db_session.commit()
    return building


def test_defect_timeline_creation(db_session, test_building):
    """Test creating a DefectTimeline instance."""
    defect = DefectTimeline(
        id=uuid.uuid4(),
        building_id=test_building.id,
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
    db_session.commit()

    retrieved = db_session.query(DefectTimeline).filter_by(id=defect.id).first()
    assert retrieved is not None
    assert retrieved.building_id == test_building.id
    assert retrieved.defect_type == "Asbestos in insulation"
    assert retrieved.status == "open"
    assert retrieved.severity == "high"


def test_defect_timeline_default_values(db_session, test_building):
    """Test default values for DefectTimeline."""
    defect = DefectTimeline(
        id=uuid.uuid4(),
        building_id=test_building.id,
        defect_type="Lead paint",
        discovery_date=date(2026, 4, 1),
        notification_deadline=date(2026, 5, 31),
    )
    db_session.add(defect)
    db_session.commit()

    retrieved = db_session.query(DefectTimeline).filter_by(id=defect.id).first()
    assert retrieved.status == "open"
    assert retrieved.severity == "medium"
    assert retrieved.legal_reference == "art. 367 al. 1bis CO"
    assert retrieved.notification_sent_at is None
    assert retrieved.responsible_party is None
    assert retrieved.description is None


def test_defect_timeline_timestamps(db_session, test_building):
    """Test that created_at and updated_at are set automatically."""
    before = datetime.utcnow()
    defect = DefectTimeline(
        id=uuid.uuid4(),
        building_id=test_building.id,
        defect_type="Mold",
        discovery_date=date(2026, 4, 1),
        notification_deadline=date(2026, 5, 31),
    )
    db_session.add(defect)
    db_session.commit()
    after = datetime.utcnow()

    retrieved = db_session.query(DefectTimeline).filter_by(id=defect.id).first()
    assert retrieved.created_at is not None
    assert retrieved.updated_at is not None
    assert before <= retrieved.created_at <= after


def test_defect_timeline_metadata_json(db_session, test_building):
    """Test metadata JSON field."""
    metadata = {"inspector_notes": "Further testing needed", "photo_count": 3}
    defect = DefectTimeline(
        id=uuid.uuid4(),
        building_id=test_building.id,
        defect_type="Structural crack",
        discovery_date=date(2026, 4, 1),
        notification_deadline=date(2026, 5, 31),
        metadata_json=metadata,
    )
    db_session.add(defect)
    db_session.commit()

    retrieved = db_session.query(DefectTimeline).filter_by(id=defect.id).first()
    assert retrieved.metadata_json == metadata
    assert retrieved.metadata_json["inspector_notes"] == "Further testing needed"


def test_defect_timeline_all_severity_levels(db_session, test_building):
    """Test all severity levels."""
    for severity in ["low", "medium", "high", "critical"]:
        defect = DefectTimeline(
            id=uuid.uuid4(),
            building_id=test_building.id,
            defect_type=f"Defect-{severity}",
            discovery_date=date(2026, 4, 1),
            notification_deadline=date(2026, 5, 31),
            severity=severity,
        )
        db_session.add(defect)

    db_session.commit()

    severities = [d.severity for d in db_session.query(DefectTimeline).filter_by().all()]
    assert "low" in severities
    assert "medium" in severities
    assert "high" in severities
    assert "critical" in severities


def test_defect_timeline_all_status_values(db_session, test_building):
    """Test all status values."""
    for status in ["open", "notified", "expired", "resolved"]:
        defect = DefectTimeline(
            id=uuid.uuid4(),
            building_id=test_building.id,
            defect_type=f"Defect-{status}",
            discovery_date=date(2026, 4, 1),
            notification_deadline=date(2026, 5, 31),
            status=status,
        )
        db_session.add(defect)

    db_session.commit()

    statuses = [d.status for d in db_session.query(DefectTimeline).filter_by().all()]
    assert "open" in statuses
    assert "notified" in statuses
    assert "expired" in statuses
    assert "resolved" in statuses


def test_defect_timeline_notification_sent_at(db_session, test_building):
    """Test notification_sent_at field."""
    now = datetime.utcnow()
    defect = DefectTimeline(
        id=uuid.uuid4(),
        building_id=test_building.id,
        defect_type="Test defect",
        discovery_date=date(2026, 4, 1),
        notification_deadline=date(2026, 5, 31),
        status="notified",
        notification_sent_at=now,
    )
    db_session.add(defect)
    db_session.commit()

    retrieved = db_session.query(DefectTimeline).filter_by(id=defect.id).first()
    assert retrieved.notification_sent_at is not None
    assert retrieved.status == "notified"
