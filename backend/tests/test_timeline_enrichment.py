import uuid
from datetime import date, datetime

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.schemas.timeline import TimelineEntryRead
from app.services.timeline_enrichment_service import (
    _assign_importance,
    _assign_lifecycle_phase,
    _enrich_entries,
    _generate_links,
)

# ---------------------------------------------------------------------------
# Unit tests for _assign_lifecycle_phase
# ---------------------------------------------------------------------------


def _make_entry(**kwargs) -> TimelineEntryRead:
    defaults = {
        "id": str(uuid.uuid4()),
        "date": datetime(2024, 6, 1),
        "event_type": "diagnostic",
        "title": "Test",
        "icon_hint": "microscope",
        "metadata": {},
    }
    defaults.update(kwargs)
    return TimelineEntryRead(**defaults)


def test_lifecycle_phase_diagnostic_draft():
    entry = _make_entry(event_type="diagnostic", metadata={"status": "draft"})
    assert _assign_lifecycle_phase(entry) == "discovery"


def test_lifecycle_phase_diagnostic_in_progress():
    entry = _make_entry(event_type="diagnostic", metadata={"status": "in_progress"})
    assert _assign_lifecycle_phase(entry) == "discovery"


def test_lifecycle_phase_diagnostic_completed():
    entry = _make_entry(event_type="diagnostic", metadata={"status": "completed"})
    assert _assign_lifecycle_phase(entry) == "assessment"


def test_lifecycle_phase_diagnostic_validated():
    entry = _make_entry(event_type="diagnostic", metadata={"status": "validated"})
    assert _assign_lifecycle_phase(entry) == "assessment"


def test_lifecycle_phase_sample():
    entry = _make_entry(event_type="sample", icon_hint="flask", metadata={"threshold_exceeded": True})
    assert _assign_lifecycle_phase(entry) == "discovery"


def test_lifecycle_phase_intervention_planned():
    entry = _make_entry(event_type="intervention", icon_hint="wrench", metadata={"status": "planned"})
    assert _assign_lifecycle_phase(entry) == "remediation"


def test_lifecycle_phase_intervention_completed():
    entry = _make_entry(event_type="intervention", icon_hint="wrench", metadata={"status": "completed"})
    assert _assign_lifecycle_phase(entry) == "verification"


def test_lifecycle_phase_intervention_cancelled():
    entry = _make_entry(event_type="intervention", icon_hint="wrench", metadata={"status": "cancelled"})
    assert _assign_lifecycle_phase(entry) == "closed"


def test_lifecycle_phase_risk_change():
    entry = _make_entry(event_type="risk_change", icon_hint="shield", metadata={"overall_risk_level": "high"})
    assert _assign_lifecycle_phase(entry) == "assessment"


def test_lifecycle_phase_construction_is_none():
    entry = _make_entry(event_type="construction", icon_hint="building")
    assert _assign_lifecycle_phase(entry) is None


def test_lifecycle_phase_document_is_none():
    entry = _make_entry(event_type="document", icon_hint="file")
    assert _assign_lifecycle_phase(entry) is None


def test_lifecycle_phase_plan():
    entry = _make_entry(event_type="plan", icon_hint="map")
    assert _assign_lifecycle_phase(entry) == "remediation"


# ---------------------------------------------------------------------------
# Unit tests for _assign_importance
# ---------------------------------------------------------------------------


def test_importance_risk_change():
    entry = _make_entry(event_type="risk_change", icon_hint="shield")
    assert _assign_importance(entry) == "high"


def test_importance_sample_threshold_exceeded():
    entry = _make_entry(event_type="sample", icon_hint="flask", metadata={"threshold_exceeded": True})
    assert _assign_importance(entry) == "critical"


def test_importance_sample_normal():
    entry = _make_entry(event_type="sample", icon_hint="flask", metadata={"threshold_exceeded": False})
    assert _assign_importance(entry) == "medium"


def test_importance_sample_high_risk():
    entry = _make_entry(event_type="sample", icon_hint="flask", metadata={"risk_level": "high"})
    assert _assign_importance(entry) == "high"


def test_importance_diagnostic_validated():
    entry = _make_entry(event_type="diagnostic", metadata={"status": "validated"})
    assert _assign_importance(entry) == "high"


def test_importance_diagnostic_draft():
    entry = _make_entry(event_type="diagnostic", metadata={"status": "draft"})
    assert _assign_importance(entry) == "medium"


def test_importance_document():
    entry = _make_entry(event_type="document", icon_hint="file")
    assert _assign_importance(entry) == "low"


def test_importance_construction():
    entry = _make_entry(event_type="construction", icon_hint="building")
    assert _assign_importance(entry) == "low"


# ---------------------------------------------------------------------------
# Unit tests for _generate_links
# ---------------------------------------------------------------------------


def test_generate_links_sample_to_diagnostic():
    diag_id = str(uuid.uuid4())
    sample_id = str(uuid.uuid4())
    entries = _enrich_entries(
        [
            _make_entry(
                id=diag_id, event_type="diagnostic", date=datetime(2024, 1, 1), metadata={"status": "completed"}
            ),
            _make_entry(
                id=sample_id,
                event_type="sample",
                icon_hint="flask",
                date=datetime(2024, 1, 2),
                metadata={"threshold_exceeded": False},
                source_id=sample_id,
                source_type="sample",
            ),
        ]
    )
    links = _generate_links(entries)
    caused_by = [lnk for lnk in links if lnk.link_type == "caused_by"]
    assert len(caused_by) == 1
    assert caused_by[0].source_event_id == sample_id
    assert caused_by[0].target_event_id == diag_id


def test_generate_links_intervention_follows_diagnostic():
    diag_id = str(uuid.uuid4())
    intv_id = str(uuid.uuid4())
    entries = _enrich_entries(
        [
            _make_entry(
                id=diag_id, event_type="diagnostic", date=datetime(2024, 1, 1), metadata={"status": "completed"}
            ),
            _make_entry(
                id=intv_id,
                event_type="intervention",
                icon_hint="wrench",
                date=datetime(2024, 3, 1),
                metadata={"status": "planned"},
            ),
        ]
    )
    links = _generate_links(entries)
    followed = [lnk for lnk in links if lnk.link_type == "followed_by"]
    assert len(followed) == 1
    assert followed[0].source_event_id == intv_id
    assert followed[0].target_event_id == diag_id


def test_generate_links_risk_triggered_by_intervention():
    intv_id = str(uuid.uuid4())
    risk_id = str(uuid.uuid4())
    entries = _enrich_entries(
        [
            _make_entry(
                id=intv_id,
                event_type="intervention",
                icon_hint="wrench",
                date=datetime(2024, 3, 1),
                metadata={"status": "completed"},
            ),
            _make_entry(
                id=risk_id,
                event_type="risk_change",
                icon_hint="shield",
                date=datetime(2024, 4, 1),
                metadata={"overall_risk_level": "low"},
            ),
        ]
    )
    links = _generate_links(entries)
    triggered = [lnk for lnk in links if lnk.link_type == "triggered"]
    assert len(triggered) == 1
    assert triggered[0].source_event_id == risk_id
    assert triggered[0].target_event_id == intv_id


def test_generate_links_empty():
    links = _generate_links([])
    assert links == []


def test_generate_links_no_links_for_unrelated():
    entries = _enrich_entries(
        [
            _make_entry(event_type="construction", icon_hint="building", date=datetime(1965, 1, 1)),
            _make_entry(event_type="document", icon_hint="file", date=datetime(2024, 5, 1)),
        ]
    )
    links = _generate_links(entries)
    assert links == []


# ---------------------------------------------------------------------------
# Integration tests via HTTP endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enriched_timeline_empty_building(client, auth_headers, db_session, admin_user):
    """Building without data returns empty enriched timeline."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue Vide 99",
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
        f"/api/v1/buildings/{building.id}/timeline/enriched",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["entries"] == []
    assert data["links"] == []
    assert data["lifecycle_summary"] == {}


@pytest.mark.asyncio
async def test_enriched_timeline_with_diagnostic_and_sample(
    client, auth_headers, db_session, sample_building, admin_user
):
    """Enriched timeline includes lifecycle phases and links for diagnostic + sample."""
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        diagnostic_type="asbestos",
        diagnostic_context="AvT",
        status="completed",
        diagnostician_id=admin_user.id,
        date_inspection=date(2024, 6, 15),
        summary="Asbestos found",
    )
    db_session.add(diag)
    await db_session.flush()

    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S001",
        pollutant_type="asbestos",
        material_category="ceiling_tile",
        location_room="Room 101",
        threshold_exceeded=True,
        risk_level="critical",
    )
    db_session.add(sample)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/timeline/enriched",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2  # at least diagnostic + sample (+ construction)
    # Check lifecycle phases are present
    phases = {e["lifecycle_phase"] for e in data["entries"] if e["lifecycle_phase"]}
    assert "assessment" in phases or "discovery" in phases
    # Check links exist
    assert len(data["links"]) >= 1


@pytest.mark.asyncio
async def test_enriched_timeline_with_intervention(client, auth_headers, db_session, sample_building, admin_user):
    """Intervention after diagnostic generates followed_by link."""
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        diagnostic_type="asbestos",
        diagnostic_context="AvT",
        status="validated",
        diagnostician_id=admin_user.id,
        date_inspection=date(2024, 1, 15),
        summary="Asbestos confirmed",
    )
    db_session.add(diag)
    await db_session.flush()

    intv = Intervention(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        title="Remove asbestos ceiling",
        intervention_type="removal",
        status="planned",
        date_start=date(2024, 6, 1),
        created_by=admin_user.id,
    )
    db_session.add(intv)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/timeline/enriched",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    link_types = [lnk["link_type"] for lnk in data["links"]]
    assert "followed_by" in link_types


@pytest.mark.asyncio
async def test_enriched_timeline_pagination(client, auth_headers, sample_building):
    """Pagination limits entries returned."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/timeline/enriched?page=1&size=1",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["entries"]) <= 1


@pytest.mark.asyncio
async def test_enriched_timeline_event_type_filter(client, auth_headers, db_session, sample_building, admin_user):
    """Event type filter narrows results."""
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        diagnostic_type="pcb",
        diagnostic_context="AvT",
        status="draft",
        diagnostician_id=admin_user.id,
        summary="PCB check",
    )
    db_session.add(diag)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/timeline/enriched?event_type=diagnostic",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    for entry in data["entries"]:
        assert entry["event_type"] == "diagnostic"


@pytest.mark.asyncio
async def test_lifecycle_summary_endpoint(client, auth_headers, db_session, sample_building, admin_user):
    """Lifecycle summary returns phase counts."""
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        diagnostic_type="asbestos",
        diagnostic_context="AvT",
        status="completed",
        diagnostician_id=admin_user.id,
        date_inspection=date(2024, 6, 15),
        summary="Asbestos found",
    )
    db_session.add(diag)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/timeline/lifecycle-summary",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert "assessment" in data
    assert data["assessment"] >= 1


@pytest.mark.asyncio
async def test_enriched_timeline_404_building(client, auth_headers):
    """Non-existent building returns 404."""
    fake_id = uuid.uuid4()
    resp = await client.get(
        f"/api/v1/buildings/{fake_id}/timeline/enriched",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_lifecycle_summary_404_building(client, auth_headers):
    """Non-existent building returns 404 for lifecycle summary."""
    fake_id = uuid.uuid4()
    resp = await client.get(
        f"/api/v1/buildings/{fake_id}/timeline/lifecycle-summary",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_enriched_timeline_no_auth(client, sample_building):
    """Unauthenticated request returns 403."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/timeline/enriched",
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_lifecycle_summary_no_auth(client, sample_building):
    """Unauthenticated request to lifecycle-summary returns 403."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/timeline/lifecycle-summary",
    )
    assert resp.status_code == 403
