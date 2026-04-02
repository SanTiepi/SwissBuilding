"""Tests for DefectTimeline model."""

from datetime import date, datetime, timedelta
from uuid import uuid4

import pytest

from app.models.building import Building
from app.models.defect_timeline import DefectTimeline


@pytest.fixture
async def building(db_session):
    b = Building(
        egrid="1234567890123",
        address="123 Test Street",
        postal_code="1000",
        city="Test City",
        canton="VD",
        building_type="house",
        created_by=uuid4(),
    )
    db_session.add(b)
    await db_session.flush()
    return b


class TestDefectTimelineModel:
    async def test_create_with_required_fields(self, db_session, building):
        discovery = date(2026, 3, 1)
        deadline = discovery + timedelta(days=60)
        dt = DefectTimeline(
            building_id=building.id,
            defect_type="structural_crack",
            discovery_date=discovery,
            notification_deadline=deadline,
            severity="high",
        )
        db_session.add(dt)
        await db_session.flush()

        assert dt.id is not None
        assert dt.building_id == building.id
        assert dt.defect_type == "structural_crack"
        assert dt.discovery_date == discovery
        assert dt.notification_deadline == deadline
        assert dt.severity == "high"

    async def test_default_status(self, db_session, building):
        dt = DefectTimeline(
            building_id=building.id,
            defect_type="water_damage",
            discovery_date=date(2026, 1, 15),
            notification_deadline=date(2026, 3, 16),
            severity="medium",
        )
        db_session.add(dt)
        await db_session.flush()

        assert dt.status in ("open", "active")

    async def test_default_legal_reference(self, db_session, building):
        dt = DefectTimeline(
            building_id=building.id,
            defect_type="insulation_defect",
            discovery_date=date(2026, 2, 1),
            notification_deadline=date(2026, 4, 2),
            severity="low",
        )
        db_session.add(dt)
        await db_session.flush()

        assert dt.legal_reference == "art. 367 al. 1bis CO"

    async def test_default_severity_is_medium(self, db_session, building):
        dt = DefectTimeline(
            building_id=building.id,
            defect_type="plumbing",
            discovery_date=date(2026, 1, 1),
            notification_deadline=date(2026, 3, 2),
        )
        db_session.add(dt)
        await db_session.flush()

        assert dt.severity == "medium"

    async def test_nullable_fields(self, db_session, building):
        dt = DefectTimeline(
            building_id=building.id,
            defect_type="crack",
            discovery_date=date(2026, 1, 1),
            notification_deadline=date(2026, 3, 2),
            severity="low",
        )
        db_session.add(dt)
        await db_session.flush()

        assert dt.notification_sent_at is None
        assert dt.description is None
        assert dt.responsible_party is None
        assert dt.metadata_json is None

    async def test_all_fields_populated(self, db_session, building):
        discovery = date(2026, 4, 1)
        deadline = discovery + timedelta(days=60)
        dt = DefectTimeline(
            building_id=building.id,
            defect_type="facade_detachment",
            discovery_date=discovery,
            notification_deadline=deadline,
            notification_sent_at=datetime(2026, 4, 10, 14, 30),
            status="notified",
            description="Facade tiles detaching on north wall",
            severity="critical",
            responsible_party="Baufirma AG",
            legal_reference="art. 367 al. 1bis CO",
            metadata_json={"floor": 3, "area_m2": 12.5},
        )
        db_session.add(dt)
        await db_session.flush()

        assert dt.status == "notified"
        assert dt.description == "Facade tiles detaching on north wall"
        assert dt.responsible_party == "Baufirma AG"
        assert dt.metadata_json["floor"] == 3

    async def test_notification_deadline_not_auto_computed(self, db_session, building):
        """notification_deadline must be set explicitly — no model-level auto-computation."""
        discovery = date(2026, 1, 1)
        wrong_deadline = date(2099, 12, 31)
        dt = DefectTimeline(
            building_id=building.id,
            defect_type="test",
            discovery_date=discovery,
            notification_deadline=wrong_deadline,
            severity="low",
        )
        db_session.add(dt)
        await db_session.flush()

        # Model stores exactly what was given — no magic correction
        assert dt.notification_deadline == wrong_deadline

    def test_tablename(self):
        assert DefectTimeline.__tablename__ == "defect_timelines"
