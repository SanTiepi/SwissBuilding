import uuid
from datetime import date, datetime

from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.event import Event
from app.services.activity_service import get_building_activity


class TestActivityService:
    async def test_returns_diagnostics(self, db_session, sample_building, admin_user):
        diag = Diagnostic(
            id=uuid.uuid4(),
            building_id=sample_building.id,
            diagnostic_type="asbestos",
            status="draft",
            diagnostician_id=admin_user.id,
            created_at=datetime(2025, 1, 10, 12, 0, 0),
        )
        db_session.add(diag)
        await db_session.commit()

        items = await get_building_activity(db_session, sample_building.id)
        assert len(items) == 1
        assert items[0].kind == "diagnostic"
        assert items[0].title == "Diagnostic asbestos"
        assert items[0].status == "draft"
        assert items[0].actor_id == admin_user.id

    async def test_returns_documents(self, db_session, sample_building, admin_user):
        doc = Document(
            id=uuid.uuid4(),
            building_id=sample_building.id,
            file_path="/files/report.pdf",
            file_name="report.pdf",
            uploaded_by=admin_user.id,
            created_at=datetime(2025, 2, 15, 9, 0, 0),
        )
        db_session.add(doc)
        await db_session.commit()

        items = await get_building_activity(db_session, sample_building.id)
        assert len(items) == 1
        assert items[0].kind == "document"
        assert items[0].title == "report.pdf"
        assert items[0].actor_id == admin_user.id

    async def test_returns_events(self, db_session, sample_building, admin_user):
        evt = Event(
            id=uuid.uuid4(),
            building_id=sample_building.id,
            event_type="inspection",
            date=date(2025, 3, 20),
            title="Site inspection",
            description="Checked roof",
            created_by=admin_user.id,
            created_at=datetime(2025, 3, 20, 14, 0, 0),
        )
        db_session.add(evt)
        await db_session.commit()

        items = await get_building_activity(db_session, sample_building.id)
        assert len(items) == 1
        assert items[0].kind == "event"
        assert items[0].title == "Site inspection"
        assert items[0].description == "Checked roof"

    async def test_sorted_descending(self, db_session, sample_building, admin_user):
        diag = Diagnostic(
            id=uuid.uuid4(),
            building_id=sample_building.id,
            diagnostic_type="pcb",
            status="completed",
            created_at=datetime(2025, 1, 1, 10, 0, 0),
        )
        doc = Document(
            id=uuid.uuid4(),
            building_id=sample_building.id,
            file_path="/files/doc.pdf",
            file_name="doc.pdf",
            created_at=datetime(2025, 3, 1, 10, 0, 0),
        )
        evt = Event(
            id=uuid.uuid4(),
            building_id=sample_building.id,
            event_type="renovation",
            date=date(2025, 2, 1),
            title="Renovation started",
            created_at=datetime(2025, 2, 1, 10, 0, 0),
        )
        db_session.add_all([diag, doc, evt])
        await db_session.commit()

        items = await get_building_activity(db_session, sample_building.id)
        assert len(items) == 3
        # Most recent first: doc (March) > event (Feb) > diag (Jan)
        assert items[0].kind == "document"
        assert items[1].kind == "event"
        assert items[2].kind == "diagnostic"
        # Verify ordering
        for i in range(len(items) - 1):
            assert items[i].occurred_at >= items[i + 1].occurred_at

    async def test_limit_offset(self, db_session, sample_building, admin_user):
        for i in range(5):
            doc = Document(
                id=uuid.uuid4(),
                building_id=sample_building.id,
                file_path=f"/files/doc{i}.pdf",
                file_name=f"doc{i}.pdf",
                created_at=datetime(2025, 1, i + 1, 10, 0, 0),
            )
            db_session.add(doc)
        await db_session.commit()

        # Limit
        items = await get_building_activity(db_session, sample_building.id, limit=2)
        assert len(items) == 2

        # Offset
        items_offset = await get_building_activity(db_session, sample_building.id, limit=2, offset=2)
        assert len(items_offset) == 2
        # No overlap
        ids_first = {i.id for i in items}
        ids_second = {i.id for i in items_offset}
        assert ids_first.isdisjoint(ids_second)

    async def test_empty_building(self, db_session, sample_building):
        items = await get_building_activity(db_session, sample_building.id)
        assert items == []


class TestActivityEndpoint:
    async def test_get_activity_200(self, client, admin_user, auth_headers, sample_building, db_session):
        diag = Diagnostic(
            id=uuid.uuid4(),
            building_id=sample_building.id,
            diagnostic_type="lead",
            status="in_progress",
            diagnostician_id=admin_user.id,
            created_at=datetime(2025, 6, 1, 8, 0, 0),
        )
        db_session.add(diag)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/activity",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["kind"] == "diagnostic"
        assert data[0]["title"] == "Diagnostic lead"
        assert data[0]["status"] == "in_progress"

    async def test_get_activity_404(self, client, admin_user, auth_headers):
        fake_id = uuid.uuid4()
        response = await client.get(
            f"/api/v1/buildings/{fake_id}/activity",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_get_activity_unauthorized(self, client, sample_building):
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/activity",
        )
        assert response.status_code in (401, 403)
