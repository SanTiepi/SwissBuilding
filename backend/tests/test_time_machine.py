"""Tests for the Building Time Machine (snapshots) service and API."""

import uuid

import pytest

from app.models.building_trust_score_v2 import BuildingTrustScore
from app.models.readiness_assessment import ReadinessAssessment
from app.services.time_machine_service import capture_snapshot, compare_snapshots, list_snapshots

# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_capture_snapshot_stores_passport_data(db_session, sample_building):
    """Snapshot captures passport state (even if empty)."""
    snapshot = await capture_snapshot(
        db_session,
        building_id=sample_building.id,
        snapshot_type="manual",
        trigger_event="Test capture",
    )

    assert snapshot.id is not None
    assert snapshot.building_id == sample_building.id
    assert snapshot.snapshot_type == "manual"
    assert snapshot.trigger_event == "Test capture"
    # Passport state should be captured (may have default/empty values)
    assert snapshot.passport_state_json is not None
    assert snapshot.passport_grade is not None  # Will be F for empty building


@pytest.mark.asyncio
async def test_capture_snapshot_stores_trust_and_readiness(db_session, sample_building, admin_user):
    """Snapshot captures trust and readiness when they exist."""
    # Create a trust score
    trust = BuildingTrustScore(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        overall_score=0.75,
        percent_proven=0.5,
        percent_inferred=0.2,
        percent_declared=0.05,
        percent_obsolete=0.0,
        percent_contradictory=0.0,
        total_data_points=10,
        trend="improving",
    )
    db_session.add(trust)

    # Create a readiness assessment
    readiness = ReadinessAssessment(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        readiness_type="safe_to_start",
        status="ready",
        score=0.8,
    )
    db_session.add(readiness)
    await db_session.commit()

    snapshot = await capture_snapshot(
        db_session,
        building_id=sample_building.id,
        snapshot_type="diagnostic_completed",
        captured_by=admin_user.id,
    )

    assert snapshot.trust_state_json is not None
    assert snapshot.trust_state_json.get("overall_trust") == 0.75
    assert snapshot.readiness_state_json is not None
    assert "safe_to_start" in snapshot.readiness_state_json
    assert snapshot.overall_trust == 0.75
    assert snapshot.captured_by == admin_user.id


@pytest.mark.asyncio
async def test_list_snapshots_returns_all(db_session, sample_building):
    """List returns all snapshots for a building."""
    snap1 = await capture_snapshot(db_session, sample_building.id, snapshot_type="manual", trigger_event="First")
    snap2 = await capture_snapshot(db_session, sample_building.id, snapshot_type="manual", trigger_event="Second")
    snap3 = await capture_snapshot(db_session, sample_building.id, snapshot_type="manual", trigger_event="Third")

    results = await list_snapshots(db_session, sample_building.id)

    assert len(results) == 3
    result_ids = {r.id for r in results}
    assert result_ids == {snap1.id, snap2.id, snap3.id}


@pytest.mark.asyncio
async def test_compare_snapshots_returns_correct_deltas(db_session, sample_building):
    """Compare returns trust/completeness deltas and grade changes."""
    # Create first snapshot (empty building -> grade F)
    snap_a = await capture_snapshot(db_session, sample_building.id, snapshot_type="manual", trigger_event="Before")

    # Add trust score to improve the building state
    trust = BuildingTrustScore(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        overall_score=0.85,
        percent_proven=0.7,
        total_data_points=20,
    )
    db_session.add(trust)

    readiness = ReadinessAssessment(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        readiness_type="safe_to_start",
        status="ready",
        score=0.9,
    )
    db_session.add(readiness)
    await db_session.commit()

    snap_b = await capture_snapshot(db_session, sample_building.id, snapshot_type="manual", trigger_event="After")

    result = await compare_snapshots(db_session, sample_building.id, snap_a.id, snap_b.id)

    assert result is not None
    assert result["building_id"] == str(sample_building.id)
    assert result["snapshot_a"]["id"] == str(snap_a.id)
    assert result["snapshot_b"]["id"] == str(snap_b.id)
    assert result["changes"]["trust_delta"] > 0
    assert "completeness_delta" in result["changes"]


@pytest.mark.asyncio
async def test_compare_with_nonexistent_snapshot(db_session, sample_building):
    """Compare returns None if a snapshot doesn't exist."""
    snap = await capture_snapshot(db_session, sample_building.id, snapshot_type="manual")
    fake_id = uuid.uuid4()

    result = await compare_snapshots(db_session, sample_building.id, snap.id, fake_id)
    assert result is None


@pytest.mark.asyncio
async def test_snapshot_for_building_with_no_data(db_session, sample_building):
    """Snapshot for a building with no diagnostics/trust/readiness still captures."""
    snapshot = await capture_snapshot(
        db_session,
        building_id=sample_building.id,
        snapshot_type="manual",
        notes="Empty building test",
    )

    assert snapshot.id is not None
    assert snapshot.building_id == sample_building.id
    assert snapshot.notes == "Empty building test"
    # Should still capture passport (with defaults)
    assert snapshot.passport_state_json is not None
    assert snapshot.passport_grade == "F"  # Empty building = grade F
    assert snapshot.overall_trust == 0.0
    assert snapshot.completeness_score == 0.0


# ---------------------------------------------------------------------------
# API-level tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_create_snapshot(client, auth_headers, sample_building):
    """POST /buildings/{id}/snapshots creates a snapshot."""
    response = await client.post(
        f"/api/v1/buildings/{sample_building.id}/snapshots",
        json={"snapshot_type": "manual", "trigger_event": "API test", "notes": "Testing"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["building_id"] == str(sample_building.id)
    assert data["snapshot_type"] == "manual"
    assert data["trigger_event"] == "API test"
    assert data["notes"] == "Testing"
    assert data["passport_state_json"] is not None


@pytest.mark.asyncio
async def test_api_list_snapshots_with_pagination(client, auth_headers, sample_building):
    """GET /buildings/{id}/snapshots returns paginated results."""
    # Create multiple snapshots
    for i in range(3):
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/snapshots",
            json={"snapshot_type": "manual", "trigger_event": f"Snapshot {i}"},
            headers=auth_headers,
        )

    response = await client.get(
        f"/api/v1/buildings/{sample_building.id}/snapshots?page=1&size=2",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["size"] == 2
    assert data["pages"] == 2


@pytest.mark.asyncio
async def test_api_get_single_snapshot(client, auth_headers, sample_building):
    """GET /buildings/{id}/snapshots/{snapshot_id} returns a single snapshot."""
    create_resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/snapshots",
        json={"snapshot_type": "manual"},
        headers=auth_headers,
    )
    snapshot_id = create_resp.json()["id"]

    response = await client.get(
        f"/api/v1/buildings/{sample_building.id}/snapshots/{snapshot_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["id"] == snapshot_id


@pytest.mark.asyncio
async def test_api_compare_snapshots(client, auth_headers, sample_building):
    """GET /buildings/{id}/snapshots/compare returns a diff."""
    resp_a = await client.post(
        f"/api/v1/buildings/{sample_building.id}/snapshots",
        json={"snapshot_type": "manual", "trigger_event": "Before"},
        headers=auth_headers,
    )
    resp_b = await client.post(
        f"/api/v1/buildings/{sample_building.id}/snapshots",
        json={"snapshot_type": "manual", "trigger_event": "After"},
        headers=auth_headers,
    )

    id_a = resp_a.json()["id"]
    id_b = resp_b.json()["id"]

    response = await client.get(
        f"/api/v1/buildings/{sample_building.id}/snapshots/compare?a={id_a}&b={id_b}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["building_id"] == str(sample_building.id)
    assert "changes" in data
    assert "trust_delta" in data["changes"]


@pytest.mark.asyncio
async def test_api_compare_nonexistent_snapshot_returns_404(client, auth_headers, sample_building):
    """Compare with non-existent snapshot returns 404."""
    resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/snapshots",
        json={"snapshot_type": "manual"},
        headers=auth_headers,
    )
    snap_id = resp.json()["id"]
    fake_id = str(uuid.uuid4())

    response = await client.get(
        f"/api/v1/buildings/{sample_building.id}/snapshots/compare?a={snap_id}&b={fake_id}",
        headers=auth_headers,
    )
    assert response.status_code == 404
