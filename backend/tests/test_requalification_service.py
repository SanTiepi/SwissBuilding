"""Tests for the requalification replay timeline service and API."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.building_change import BuildingSignal
from app.models.building_snapshot import BuildingSnapshot
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.schemas.requalification import TriggerType, TriggerUrgency
from app.services.requalification_service import (
    detect_requalification_triggers,
    get_requalification_recommendations,
    get_requalification_timeline,
    get_state_change_summary,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_signal(
    building_id,
    *,
    signal_type="diagnostic_completed",
    severity="info",
    title="Signal",
    description=None,
    detected_at=None,
):
    return BuildingSignal(
        id=uuid.uuid4(),
        building_id=building_id,
        signal_type=signal_type,
        severity=severity,
        status="active",
        title=title,
        description=description or "",
        based_on_type="event",
        detected_at=detected_at or datetime.now(UTC),
    )


def _make_snapshot(building_id, *, passport_grade=None, snapshot_type="manual", trigger_event=None, captured_at=None):
    return BuildingSnapshot(
        id=uuid.uuid4(),
        building_id=building_id,
        snapshot_type=snapshot_type,
        trigger_event=trigger_event,
        passport_grade=passport_grade,
        captured_at=captured_at or datetime.now(UTC),
    )


def _make_intervention(
    building_id,
    *,
    title="Désamiantage",
    status="completed",
    intervention_type="removal",
    created_at=None,
    updated_at=None,
):
    ts = created_at or datetime.now(UTC)
    return Intervention(
        id=uuid.uuid4(),
        building_id=building_id,
        intervention_type=intervention_type,
        title=title,
        status=status,
        created_at=ts,
        updated_at=updated_at or ts,
    )


def _make_diagnostic(building_id, *, status="completed", date_report=None, created_at=None):
    return Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type="asbestos",
        status=status,
        date_report=date_report,
        created_at=created_at or datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_timeline(db_session, sample_building):
    """Timeline with no signals or snapshots returns empty entries."""
    result = await get_requalification_timeline(db_session, sample_building.id)
    assert result.building_id == sample_building.id
    assert result.entries == []
    assert result.current_grade is None
    assert result.grade_history == []


@pytest.mark.asyncio
async def test_timeline_with_signals(db_session, sample_building):
    """Signals appear as 'signal' entries in the timeline."""
    sig = _make_signal(sample_building.id, title="Positive sample detected", severity="warning")
    db_session.add(sig)
    await db_session.commit()

    result = await get_requalification_timeline(db_session, sample_building.id)
    assert len(result.entries) == 1
    entry = result.entries[0]
    assert entry.entry_type == "signal"
    assert entry.title == "Positive sample detected"
    assert entry.severity == "warning"


@pytest.mark.asyncio
async def test_timeline_with_snapshots(db_session, sample_building):
    """Snapshots appear as 'snapshot' entries in the timeline."""
    snap = _make_snapshot(sample_building.id, passport_grade="B", trigger_event="manual capture")
    db_session.add(snap)
    await db_session.commit()

    result = await get_requalification_timeline(db_session, sample_building.id)
    assert len(result.entries) == 1
    entry = result.entries[0]
    assert entry.entry_type == "snapshot"
    assert entry.metadata["passport_grade"] == "B"
    assert result.current_grade == "B"
    assert len(result.grade_history) == 1


@pytest.mark.asyncio
async def test_timeline_merged_chronological(db_session, sample_building):
    """Signals, snapshots, and interventions are merged in chronological order (newest first)."""
    now = datetime.now(UTC)
    sig = _make_signal(sample_building.id, title="S1", detected_at=now - timedelta(hours=3))
    snap = _make_snapshot(sample_building.id, passport_grade="C", captured_at=now - timedelta(hours=2))
    interv = _make_intervention(sample_building.id, title="I1", created_at=now - timedelta(hours=1))
    db_session.add_all([sig, snap, interv])
    await db_session.commit()

    result = await get_requalification_timeline(db_session, sample_building.id)
    assert len(result.entries) == 3
    # Newest first
    assert result.entries[0].entry_type == "intervention"
    assert result.entries[1].entry_type == "snapshot"
    assert result.entries[2].entry_type == "signal"


@pytest.mark.asyncio
async def test_timeline_grade_change_detection(db_session, sample_building):
    """Grade transitions between snapshots generate explicit grade_change entries."""
    now = datetime.now(UTC)
    snap1 = _make_snapshot(sample_building.id, passport_grade="D", captured_at=now - timedelta(days=2))
    snap2 = _make_snapshot(sample_building.id, passport_grade="B", captured_at=now - timedelta(days=1))
    db_session.add_all([snap1, snap2])
    await db_session.commit()

    result = await get_requalification_timeline(db_session, sample_building.id)

    grade_changes = [e for e in result.entries if e.entry_type == "grade_change"]
    assert len(grade_changes) == 1
    assert grade_changes[0].grade_before == "D"
    assert grade_changes[0].grade_after == "B"
    assert result.current_grade == "B"


@pytest.mark.asyncio
async def test_timeline_limit(db_session, sample_building):
    """Limit parameter caps the number of returned entries."""
    now = datetime.now(UTC)
    for i in range(10):
        db_session.add(_make_signal(sample_building.id, title=f"S{i}", detected_at=now - timedelta(minutes=i)))
    await db_session.commit()

    result = await get_requalification_timeline(db_session, sample_building.id, limit=3)
    assert len(result.entries) == 3


@pytest.mark.asyncio
async def test_state_change_summary(db_session, sample_building):
    """Summary returns correct counts."""
    now = datetime.now(UTC)
    db_session.add(_make_signal(sample_building.id, detected_at=now - timedelta(hours=1)))
    db_session.add(_make_signal(sample_building.id, detected_at=now))
    db_session.add(_make_snapshot(sample_building.id, passport_grade="D", captured_at=now - timedelta(days=2)))
    db_session.add(_make_snapshot(sample_building.id, passport_grade="C", captured_at=now - timedelta(days=1)))
    db_session.add(_make_snapshot(sample_building.id, passport_grade="C", captured_at=now))
    await db_session.commit()

    summary = await get_state_change_summary(db_session, sample_building.id)
    assert summary["total_signals"] == 2
    assert summary["total_snapshots"] == 3
    assert summary["grade_changes_count"] == 1
    assert summary["current_grade"] == "C"
    assert summary["last_signal_date"] is not None
    assert summary["last_snapshot_date"] is not None


@pytest.mark.asyncio
async def test_api_endpoint_returns_timeline(client, auth_headers, sample_building):
    """GET /buildings/{id}/requalification/timeline returns 200."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/requalification/timeline",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "entries" in data
    assert "current_grade" in data
    assert "grade_history" in data
    assert data["building_id"] == str(sample_building.id)


@pytest.mark.asyncio
async def test_api_summary_endpoint(client, auth_headers, sample_building):
    """GET /buildings/{id}/requalification/summary returns 200."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/requalification/summary",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_signals"] == 0
    assert data["total_snapshots"] == 0


@pytest.mark.asyncio
async def test_api_timeline_404_for_missing_building(client, auth_headers):
    """Timeline endpoint returns 404 for a non-existent building."""
    fake_id = uuid.uuid4()
    resp = await client.get(
        f"/api/v1/buildings/{fake_id}/requalification/timeline",
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Trigger detection tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_triggers_empty_building(db_session, sample_building):
    """A building with no data produces no triggers."""
    report = await detect_requalification_triggers(db_session, sample_building.id)
    assert report.building_id == sample_building.id
    assert report.triggers == []
    assert report.needs_requalification is False
    assert report.urgency == TriggerUrgency.low


@pytest.mark.asyncio
async def test_trigger_grade_degradation(db_session, sample_building):
    """Grade going from B to C triggers grade_degradation."""
    now = datetime.now(UTC)
    db_session.add(_make_snapshot(sample_building.id, passport_grade="B", captured_at=now - timedelta(days=2)))
    db_session.add(_make_snapshot(sample_building.id, passport_grade="C", captured_at=now - timedelta(days=1)))
    await db_session.commit()

    report = await detect_requalification_triggers(db_session, sample_building.id)
    trigger_types = [t.trigger_type for t in report.triggers]
    assert TriggerType.grade_degradation in trigger_types
    assert report.needs_requalification is True


@pytest.mark.asyncio
async def test_no_trigger_grade_improvement(db_session, sample_building):
    """Grade going from C to A does NOT trigger grade_degradation."""
    now = datetime.now(UTC)
    db_session.add(_make_snapshot(sample_building.id, passport_grade="C", captured_at=now - timedelta(days=2)))
    db_session.add(_make_snapshot(sample_building.id, passport_grade="A", captured_at=now - timedelta(days=1)))
    await db_session.commit()

    report = await detect_requalification_triggers(db_session, sample_building.id)
    trigger_types = [t.trigger_type for t in report.triggers]
    assert TriggerType.grade_degradation not in trigger_types


@pytest.mark.asyncio
async def test_trigger_grade_degradation_metadata(db_session, sample_building):
    """Grade degradation trigger includes before/after grades in metadata."""
    now = datetime.now(UTC)
    db_session.add(_make_snapshot(sample_building.id, passport_grade="A", captured_at=now - timedelta(days=2)))
    db_session.add(_make_snapshot(sample_building.id, passport_grade="D", captured_at=now - timedelta(days=1)))
    await db_session.commit()

    report = await detect_requalification_triggers(db_session, sample_building.id)
    trigger = next(t for t in report.triggers if t.trigger_type == TriggerType.grade_degradation)
    assert trigger.metadata["grade_before"] == "A"
    assert trigger.metadata["grade_after"] == "D"
    assert trigger.severity == TriggerUrgency.high


@pytest.mark.asyncio
async def test_trigger_stale_diagnostic(db_session, sample_building):
    """A completed diagnostic older than 5 years triggers stale_diagnostic."""
    from datetime import date

    old_date = date.today() - timedelta(days=6 * 365)
    db_session.add(_make_diagnostic(sample_building.id, date_report=old_date))
    await db_session.commit()

    report = await detect_requalification_triggers(db_session, sample_building.id)
    trigger_types = [t.trigger_type for t in report.triggers]
    assert TriggerType.stale_diagnostic in trigger_types


@pytest.mark.asyncio
async def test_no_trigger_recent_diagnostic(db_session, sample_building):
    """A recent completed diagnostic does NOT trigger stale_diagnostic."""
    from datetime import date

    recent_date = date.today() - timedelta(days=365)
    db_session.add(_make_diagnostic(sample_building.id, date_report=recent_date))
    await db_session.commit()

    report = await detect_requalification_triggers(db_session, sample_building.id)
    trigger_types = [t.trigger_type for t in report.triggers]
    assert TriggerType.stale_diagnostic not in trigger_types


@pytest.mark.asyncio
async def test_trigger_high_severity_accumulation(db_session, sample_building):
    """3+ high/critical signals without a subsequent snapshot triggers accumulation."""
    now = datetime.now(UTC)
    for i in range(4):
        db_session.add(
            _make_signal(
                sample_building.id, title=f"Critical {i}", severity="critical", detected_at=now - timedelta(hours=i)
            )
        )
    await db_session.commit()

    report = await detect_requalification_triggers(db_session, sample_building.id)
    trigger_types = [t.trigger_type for t in report.triggers]
    assert TriggerType.high_severity_accumulation in trigger_types
    trigger = next(t for t in report.triggers if t.trigger_type == TriggerType.high_severity_accumulation)
    assert trigger.metadata["signal_count"] == 4


@pytest.mark.asyncio
async def test_no_trigger_few_high_severity_signals(db_session, sample_building):
    """Fewer than 3 high severity signals does NOT trigger accumulation."""
    now = datetime.now(UTC)
    db_session.add(_make_signal(sample_building.id, severity="high", detected_at=now))
    db_session.add(_make_signal(sample_building.id, severity="critical", detected_at=now - timedelta(hours=1)))
    await db_session.commit()

    report = await detect_requalification_triggers(db_session, sample_building.id)
    trigger_types = [t.trigger_type for t in report.triggers]
    assert TriggerType.high_severity_accumulation not in trigger_types


@pytest.mark.asyncio
async def test_trigger_high_severity_only_after_last_snapshot(db_session, sample_building):
    """Only signals AFTER the last snapshot count toward accumulation."""
    now = datetime.now(UTC)
    # 3 signals before the snapshot
    for i in range(3):
        db_session.add(_make_signal(sample_building.id, severity="high", detected_at=now - timedelta(days=10 + i)))
    # Snapshot after those signals
    db_session.add(_make_snapshot(sample_building.id, passport_grade="B", captured_at=now - timedelta(days=5)))
    # Only 1 signal after snapshot
    db_session.add(_make_signal(sample_building.id, severity="high", detected_at=now - timedelta(days=1)))
    await db_session.commit()

    report = await detect_requalification_triggers(db_session, sample_building.id)
    trigger_types = [t.trigger_type for t in report.triggers]
    assert TriggerType.high_severity_accumulation not in trigger_types


@pytest.mark.asyncio
async def test_trigger_post_intervention(db_session, sample_building):
    """Completed intervention with no subsequent snapshot triggers post_intervention."""
    now = datetime.now(UTC)
    db_session.add(_make_intervention(sample_building.id, title="Removal", created_at=now - timedelta(days=1)))
    await db_session.commit()

    report = await detect_requalification_triggers(db_session, sample_building.id)
    trigger_types = [t.trigger_type for t in report.triggers]
    assert TriggerType.post_intervention in trigger_types


@pytest.mark.asyncio
async def test_no_trigger_post_intervention_with_snapshot(db_session, sample_building):
    """Completed intervention WITH a subsequent snapshot does NOT trigger."""
    now = datetime.now(UTC)
    db_session.add(_make_intervention(sample_building.id, title="Removal", created_at=now - timedelta(days=2)))
    db_session.add(_make_snapshot(sample_building.id, passport_grade="B", captured_at=now - timedelta(days=1)))
    await db_session.commit()

    report = await detect_requalification_triggers(db_session, sample_building.id)
    trigger_types = [t.trigger_type for t in report.triggers]
    assert TriggerType.post_intervention not in trigger_types


@pytest.mark.asyncio
async def test_trigger_trust_score_drop(db_session, sample_building):
    """Trust score below 0.5 triggers trust_score_drop."""
    snap = _make_snapshot(sample_building.id, passport_grade="C")
    snap.overall_trust = 0.3
    db_session.add(snap)
    await db_session.commit()

    report = await detect_requalification_triggers(db_session, sample_building.id)
    trigger_types = [t.trigger_type for t in report.triggers]
    assert TriggerType.trust_score_drop in trigger_types
    trigger = next(t for t in report.triggers if t.trigger_type == TriggerType.trust_score_drop)
    assert trigger.severity == TriggerUrgency.critical
    assert trigger.metadata["trust_score"] == 0.3


@pytest.mark.asyncio
async def test_no_trigger_trust_score_above_threshold(db_session, sample_building):
    """Trust score at or above 0.5 does NOT trigger trust_score_drop."""
    snap = _make_snapshot(sample_building.id, passport_grade="B")
    snap.overall_trust = 0.8
    db_session.add(snap)
    await db_session.commit()

    report = await detect_requalification_triggers(db_session, sample_building.id)
    trigger_types = [t.trigger_type for t in report.triggers]
    assert TriggerType.trust_score_drop not in trigger_types


@pytest.mark.asyncio
async def test_recommendations_from_triggers(db_session, sample_building):
    """Recommendations are generated for each unique trigger type."""
    now = datetime.now(UTC)
    # Grade degradation
    db_session.add(_make_snapshot(sample_building.id, passport_grade="A", captured_at=now - timedelta(days=2)))
    db_session.add(_make_snapshot(sample_building.id, passport_grade="C", captured_at=now - timedelta(days=1)))
    # Post-intervention
    db_session.add(_make_intervention(sample_building.id, title="Work", created_at=now))
    await db_session.commit()

    recs = await get_requalification_recommendations(db_session, sample_building.id)
    assert len(recs) >= 2
    rec_types = {r.trigger_type for r in recs}
    assert TriggerType.grade_degradation in rec_types
    assert TriggerType.post_intervention in rec_types
    # Recommendations are sorted by priority
    priorities = [r.priority for r in recs]
    assert priorities == sorted(priorities)


@pytest.mark.asyncio
async def test_recommendations_empty_when_no_triggers(db_session, sample_building):
    """No triggers means no recommendations."""
    recs = await get_requalification_recommendations(db_session, sample_building.id)
    assert recs == []


@pytest.mark.asyncio
async def test_urgency_is_max_severity(db_session, sample_building):
    """Report urgency equals the highest severity among triggers."""
    now = datetime.now(UTC)
    # Grade degradation = high
    db_session.add(_make_snapshot(sample_building.id, passport_grade="A", captured_at=now - timedelta(days=2)))
    snap2 = _make_snapshot(sample_building.id, passport_grade="D", captured_at=now - timedelta(days=1))
    snap2.overall_trust = 0.2  # trust_score_drop = critical
    db_session.add(snap2)
    await db_session.commit()

    report = await detect_requalification_triggers(db_session, sample_building.id)
    assert report.urgency == TriggerUrgency.critical


# ---------------------------------------------------------------------------
# API endpoint tests for triggers & recommendations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_triggers_endpoint(client, auth_headers, sample_building):
    """GET /buildings/{id}/requalification/triggers returns 200."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/requalification/triggers",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "triggers" in data
    assert "needs_requalification" in data
    assert "urgency" in data
    assert "recommendations" in data
    assert data["building_id"] == str(sample_building.id)


@pytest.mark.asyncio
async def test_api_recommendations_endpoint(client, auth_headers, sample_building):
    """GET /buildings/{id}/requalification/recommendations returns 200."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/requalification/recommendations",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_api_triggers_404_for_missing_building(client, auth_headers):
    """Triggers endpoint returns 404 for a non-existent building."""
    fake_id = uuid.uuid4()
    resp = await client.get(
        f"/api/v1/buildings/{fake_id}/requalification/triggers",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_recommendations_404_for_missing_building(client, auth_headers):
    """Recommendations endpoint returns 404 for a non-existent building."""
    fake_id = uuid.uuid4()
    resp = await client.get(
        f"/api/v1/buildings/{fake_id}/requalification/recommendations",
        headers=auth_headers,
    )
    assert resp.status_code == 404
