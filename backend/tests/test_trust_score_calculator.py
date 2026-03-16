"""Tests for the BuildingTrustScore calculation service."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.evidence_link import EvidenceLink
from app.models.sample import Sample
from app.models.zone import Zone
from app.services.trust_score_calculator import calculate_trust_score

# ── Helpers ────────────────────────────────────────────────────────


async def _create_building(db, admin_user, *, source_dataset=None):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=admin_user.id,
        owner_id=admin_user.id,
        status="active",
        source_dataset=source_dataset,
    )
    db.add(b)
    await db.flush()
    return b


async def _create_diagnostic(db, building_id, *, status="completed", old=False):
    inspection_date = date(2018, 1, 15) if old else date(2024, 6, 1)
    created_at = datetime(2018, 1, 15, tzinfo=UTC) if old else datetime(2024, 6, 1, tzinfo=UTC)
    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type="asbestos",
        status=status,
        date_inspection=inspection_date,
        created_at=created_at,
    )
    db.add(d)
    await db.flush()
    return d


async def _create_sample(
    db,
    diagnostic_id,
    *,
    concentration=None,
    unit=None,
    location_room="Room A",
    pollutant_type="asbestos",
    threshold_exceeded=None,
):
    s = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic_id,
        sample_number=f"S-{uuid.uuid4().hex[:6]}",
        location_room=location_room,
        pollutant_type=pollutant_type,
        concentration=concentration,
        unit=unit,
        threshold_exceeded=threshold_exceeded,
    )
    db.add(s)
    await db.flush()
    return s


async def _create_document(db, building_id, *, document_type="other"):
    d = Document(
        id=uuid.uuid4(),
        building_id=building_id,
        file_path="/fake/path.pdf",
        file_name="report.pdf",
        document_type=document_type,
    )
    db.add(d)
    await db.flush()
    return d


async def _create_evidence_link(db, source_type, source_id, target_type, target_id):
    el = EvidenceLink(
        id=uuid.uuid4(),
        source_type=source_type,
        source_id=source_id,
        target_type=target_type,
        target_id=target_id,
        relationship="supports",
    )
    db.add(el)
    await db.flush()
    return el


async def _create_zone(db, building_id, *, zone_type="floor", name="Ground floor"):
    z = Zone(
        id=uuid.uuid4(),
        building_id=building_id,
        zone_type=zone_type,
        name=name,
    )
    db.add(z)
    await db.flush()
    return z


# ── Tests ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_empty_building_trust_score(db_session, admin_user):
    """Building with no data → low score, all declared (just building metadata)."""
    building = await _create_building(db_session, admin_user)

    result = await calculate_trust_score(db_session, building.id, assessed_by="test")

    assert result.building_id == building.id
    # Only building metadata (3 declared points, no official source)
    assert result.total_data_points == 3
    assert result.declared_count == 3
    assert result.proven_count == 0
    assert result.overall_score == pytest.approx(0.3, abs=0.01)
    assert result.assessed_by == "test"


@pytest.mark.asyncio
async def test_building_with_diagnostics_and_samples(db_session, admin_user):
    """Building + completed diagnostic + samples with lab results → higher proven count."""
    building = await _create_building(db_session, admin_user)
    diag = await _create_diagnostic(db_session, building.id, status="completed")
    await _create_sample(
        db_session, diag.id, concentration=0.5, unit="mg/kg", location_room="Room A", threshold_exceeded=False
    )
    await _create_sample(
        db_session, diag.id, concentration=1.2, unit="mg/kg", location_room="Room B", threshold_exceeded=True
    )

    result = await calculate_trust_score(db_session, building.id)

    # 1 proven diagnostic + 2 proven samples + 3 declared building meta = 6 total
    assert result.proven_count == 3  # diag + 2 samples
    assert result.declared_count == 3  # building metadata
    assert result.total_data_points == 6
    assert result.overall_score > 0.3  # better than empty building


@pytest.mark.asyncio
async def test_building_with_evidence_links(db_session, admin_user):
    """Evidence links increase proven count."""
    building = await _create_building(db_session, admin_user)
    target_id = uuid.uuid4()
    await _create_evidence_link(db_session, "building", building.id, "document", target_id)
    await _create_evidence_link(db_session, "building", building.id, "sample", uuid.uuid4())

    result = await calculate_trust_score(db_session, building.id)

    # 2 evidence links (proven) + 3 building metadata (declared)
    assert result.proven_count == 2
    assert result.declared_count == 3
    assert result.total_data_points == 5


@pytest.mark.asyncio
async def test_building_with_documents(db_session, admin_user):
    """Documents contribute to trust score based on document_type."""
    building = await _create_building(db_session, admin_user)
    await _create_document(db_session, building.id, document_type="lab_report")
    await _create_document(db_session, building.id, document_type="official_report")
    await _create_document(db_session, building.id, document_type="photo")

    result = await calculate_trust_score(db_session, building.id)

    # 2 proven docs + 1 declared doc + 3 declared building meta
    assert result.proven_count == 2
    assert result.declared_count == 4
    assert result.total_data_points == 6


@pytest.mark.asyncio
async def test_obsolete_diagnostic(db_session, admin_user):
    """Old diagnostic (>5 years) → obsolete data points."""
    building = await _create_building(db_session, admin_user)
    diag = await _create_diagnostic(db_session, building.id, status="completed", old=True)
    await _create_sample(db_session, diag.id, concentration=0.5, unit="mg/kg")

    result = await calculate_trust_score(db_session, building.id)

    # Old diag + old sample = 2 obsolete, 3 declared building meta
    assert result.obsolete_count == 2
    assert result.declared_count == 3
    assert result.total_data_points == 5
    # Obsolete points have weight 0.1, so score should be low
    assert result.overall_score < 0.3


@pytest.mark.asyncio
async def test_trend_detection(db_session, admin_user):
    """Run twice, add data between runs → trend detected."""
    building = await _create_building(db_session, admin_user)

    # First calculation — empty building, low score
    result1 = await calculate_trust_score(db_session, building.id)
    assert result1.trend is None  # no previous
    assert result1.previous_score is None

    # Add proven data to improve the score
    diag = await _create_diagnostic(db_session, building.id, status="completed")
    await _create_sample(db_session, diag.id, concentration=1.0, unit="mg/kg")
    await _create_sample(db_session, diag.id, concentration=2.0, unit="mg/kg")
    await _create_document(db_session, building.id, document_type="lab_report")
    await _create_document(db_session, building.id, document_type="official_report")

    # Second calculation — should see improvement
    result2 = await calculate_trust_score(db_session, building.id)
    assert result2.previous_score == result1.overall_score
    assert result2.overall_score > result1.overall_score
    assert result2.trend == "improving"


@pytest.mark.asyncio
async def test_contradictory_samples(db_session, admin_user):
    """Same pollutant/location with conflicting threshold_exceeded → contradictory."""
    building = await _create_building(db_session, admin_user)
    diag = await _create_diagnostic(db_session, building.id, status="completed")

    # Two samples for same location+pollutant with conflicting threshold_exceeded
    await _create_sample(
        db_session,
        diag.id,
        concentration=0.1,
        unit="mg/kg",
        location_room="Room B",
        pollutant_type="pcb",
        threshold_exceeded=False,
    )
    await _create_sample(
        db_session,
        diag.id,
        concentration=100.0,
        unit="mg/kg",
        location_room="Room B",
        pollutant_type="pcb",
        threshold_exceeded=True,
    )

    result = await calculate_trust_score(db_session, building.id)

    assert result.contradictory_count == 2
    assert result.percent_contradictory > 0.0


@pytest.mark.asyncio
async def test_overall_score_range(db_session, admin_user):
    """Score always between 0.0 and 1.0."""
    building = await _create_building(db_session, admin_user)

    # Empty building
    r1 = await calculate_trust_score(db_session, building.id)
    assert 0.0 <= r1.overall_score <= 1.0

    # Building with lots of proven data
    building2 = await _create_building(db_session, admin_user, source_dataset="vd-public-rcb")
    diag = await _create_diagnostic(db_session, building2.id, status="validated")
    for i in range(10):
        await _create_sample(db_session, diag.id, concentration=float(i), unit="mg/kg", location_room=f"Room {i}")
    for _ in range(5):
        await _create_document(db_session, building2.id, document_type="lab_report")

    r2 = await calculate_trust_score(db_session, building2.id)
    assert 0.0 <= r2.overall_score <= 1.0


@pytest.mark.asyncio
async def test_upsert_preserves_previous(db_session, admin_user):
    """Second calculation stores previous_score from first."""
    building = await _create_building(db_session, admin_user)

    first = await calculate_trust_score(db_session, building.id, assessed_by="auto")
    assert first.previous_score is None

    second = await calculate_trust_score(db_session, building.id, assessed_by="auto")
    assert second.previous_score == first.overall_score
    assert second.id != first.id
