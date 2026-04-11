import uuid
from datetime import UTC, date, datetime

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.diagnostic_publication import DiagnosticReportPublication
from app.models.event import Event
from app.models.intervention import Intervention
from app.models.sample import Sample


@pytest.mark.asyncio
async def test_timeline_empty_building(client, auth_headers, sample_building):
    """Empty building returns empty timeline (construction may appear if year is set)."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/timeline",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data
    # sample_building has construction_year=1965, so 1 item expected
    assert data["total"] == 1
    assert data["items"][0]["event_type"] == "construction"


@pytest.mark.asyncio
async def test_timeline_building_without_construction_year(client, auth_headers, db_session, admin_user):
    """Building without construction_year returns truly empty timeline."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue Vide 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=None,
        building_type="commercial",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/buildings/{building.id}/timeline",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_timeline_with_diagnostic(client, auth_headers, db_session, sample_building, admin_user):
    """Building with diagnostic shows diagnostic entries."""
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        diagnostic_type="asbestos",
        diagnostic_context="AvT",
        status="completed",
        diagnostician_id=admin_user.id,
        date_inspection=date(2024, 6, 15),
        summary="Asbestos found in ceiling tiles",
    )
    db_session.add(diag)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/timeline",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    # Should have construction + diagnostic = 2
    assert data["total"] == 2
    event_types = [item["event_type"] for item in data["items"]]
    assert "diagnostic" in event_types


@pytest.mark.asyncio
async def test_timeline_chronological_order(client, auth_headers, db_session, sample_building, admin_user):
    """Timeline entries are sorted newest first."""
    # Old diagnostic
    diag_old = Diagnostic(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        diagnostic_type="pcb",
        status="draft",
        diagnostician_id=admin_user.id,
        date_inspection=date(2020, 1, 1),
    )
    # Recent diagnostic
    diag_new = Diagnostic(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        diagnostic_type="lead",
        status="completed",
        diagnostician_id=admin_user.id,
        date_inspection=date(2025, 6, 1),
    )
    db_session.add_all([diag_old, diag_new])
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/timeline",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    dates = [item["date"] for item in data["items"]]
    # Verify sorted descending
    assert dates == sorted(dates, reverse=True)


@pytest.mark.asyncio
async def test_timeline_pagination(client, auth_headers, db_session, sample_building, admin_user):
    """Pagination works correctly."""
    # Create 5 events
    for i in range(5):
        evt = Event(
            id=uuid.uuid4(),
            building_id=sample_building.id,
            event_type="inspection",
            date=date(2024, i + 1, 1),
            title=f"Event {i}",
        )
        db_session.add(evt)
    await db_session.commit()

    # Page 1, size 3
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/timeline?page=1&size=3",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 3
    assert data["total"] == 6  # 5 events + 1 construction
    assert data["page"] == 1
    assert data["size"] == 3
    assert data["pages"] == 2

    # Page 2
    resp2 = await client.get(
        f"/api/v1/buildings/{sample_building.id}/timeline?page=2&size=3",
        headers=auth_headers,
    )
    data2 = resp2.json()
    assert len(data2["items"]) == 3
    assert data2["page"] == 2


@pytest.mark.asyncio
async def test_timeline_event_type_filter(client, auth_headers, db_session, sample_building, admin_user):
    """Event type filter works."""
    # Add a diagnostic and an event
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        diagnostic_type="asbestos",
        status="draft",
        diagnostician_id=admin_user.id,
        date_inspection=date(2024, 3, 1),
    )
    evt = Event(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        event_type="inspection",
        date=date(2024, 4, 1),
        title="Annual inspection",
    )
    db_session.add_all([diag, evt])
    await db_session.commit()

    # Filter for diagnostics only
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/timeline?event_type=diagnostic",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert all(item["event_type"] == "diagnostic" for item in data["items"])
    assert data["total"] == 1

    # Filter for events only
    resp2 = await client.get(
        f"/api/v1/buildings/{sample_building.id}/timeline?event_type=event",
        headers=auth_headers,
    )
    data2 = resp2.json()
    assert all(item["event_type"] == "event" for item in data2["items"])
    assert data2["total"] == 1


@pytest.mark.asyncio
async def test_timeline_not_found(client, auth_headers):
    """Non-existent building returns 404."""
    fake_id = uuid.uuid4()
    resp = await client.get(
        f"/api/v1/buildings/{fake_id}/timeline",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_timeline_with_samples(client, auth_headers, db_session, sample_building, admin_user):
    """Samples appear in the timeline."""
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        diagnostic_type="asbestos",
        status="completed",
        diagnostician_id=admin_user.id,
        date_inspection=date(2024, 6, 15),
    )
    db_session.add(diag)
    await db_session.flush()

    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S001",
        pollutant_type="asbestos",
        material_category="insulation",
        concentration=5.2,
        unit="percent_weight",
        threshold_exceeded=True,
        risk_level="high",
    )
    db_session.add(sample)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/timeline?event_type=sample",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["event_type"] == "sample"
    assert "asbestos" in data["items"][0]["title"]


@pytest.mark.asyncio
async def test_timeline_with_intervention(client, auth_headers, db_session, sample_building, admin_user):
    """Interventions appear in the timeline."""
    intv = Intervention(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        intervention_type="asbestos_removal",
        title="Asbestos removal in basement",
        status="completed",
        date_start=date(2024, 9, 1),
        cost_chf=15000.0,
        created_by=admin_user.id,
    )
    db_session.add(intv)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/timeline?event_type=intervention",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["event_type"] == "intervention"


@pytest.mark.asyncio
async def test_timeline_with_diagnostic_publication(client, auth_headers, db_session, sample_building):
    """Matched diagnostic publications appear in the timeline."""
    pub = DiagnosticReportPublication(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        source_system="batiscan",
        source_mission_id="MISS-001",
        current_version=1,
        match_state="auto_matched",
        match_key_type="egid",
        match_key="123",
        payload_hash="abc123def456",
        mission_type="asbestos_full",
        published_at=datetime(2025, 3, 15, tzinfo=UTC),
        source_type="import",
        confidence="verified",
        source_ref="batiscan:MISS-001",
    )
    db_session.add(pub)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/timeline?event_type=diagnostic_publication",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["event_type"] == "diagnostic_publication"
    assert "asbestos_full" in item["title"]
    assert "batiscan" in item["description"]
    assert item["metadata"]["mission_type"] == "asbestos_full"
    assert item["metadata"]["source_system"] == "batiscan"
    assert item["metadata"]["current_version"] == 1
    assert item["source_type"] == "diagnostic_publication"


@pytest.mark.asyncio
async def test_timeline_excludes_unmatched_publications(client, auth_headers, db_session, sample_building):
    """Unmatched/needs_review publications do NOT appear in the timeline."""
    for state in ("unmatched", "needs_review"):
        pub = DiagnosticReportPublication(
            id=uuid.uuid4(),
            building_id=sample_building.id,
            source_system="batiscan",
            source_mission_id=f"MISS-{state}",
            current_version=1,
            match_state=state,
            match_key_type="none",
            payload_hash=f"hash-{state}-xyz",
            mission_type="pcb",
            published_at=datetime(2025, 4, 1, tzinfo=UTC),
            source_type="import",
            confidence="verified",
            source_ref=f"batiscan:MISS-{state}",
        )
        db_session.add(pub)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/timeline?event_type=diagnostic_publication",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_timeline_publication_version_update(client, auth_headers, db_session, sample_building):
    """Updated publication (version > 1) shows correct version in timeline."""
    pub = DiagnosticReportPublication(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        source_system="batiscan",
        source_mission_id="MISS-V3",
        current_version=3,
        match_state="manual_matched",
        match_key_type="manual",
        match_key=str(sample_building.id),
        payload_hash="hash-v3-abc",
        mission_type="multi",
        published_at=datetime(2025, 5, 10, tzinfo=UTC),
        source_type="import",
        confidence="verified",
        source_ref="batiscan:MISS-V3",
    )
    db_session.add(pub)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/timeline?event_type=diagnostic_publication",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["metadata"]["current_version"] == 3
    assert "MISS-V3" in item["description"] or "version 3" in item["description"].lower()
