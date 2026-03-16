"""Tests for the Plan Heatmap proof-overlay service."""

import uuid
from datetime import datetime, timedelta

import pytest

from app.models.building import Building
from app.models.data_quality_issue import DataQualityIssue
from app.models.diagnostic import Diagnostic
from app.models.plan_annotation import PlanAnnotation
from app.models.sample import Sample
from app.models.technical_plan import TechnicalPlan
from app.models.unknown_issue import UnknownIssue
from app.models.zone import Zone
from app.services.plan_heatmap_service import (
    detect_coverage_gaps,
    generate_plan_heatmap,
    get_heatmap_at_date,
    get_zone_heatmap_stats,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BUILDING_ID = uuid.uuid4()
_PLAN_ID = uuid.uuid4()


def _make_building(db_session, *, building_id=None, created_by=None):
    b = Building(
        id=building_id or _BUILDING_ID,
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


def _make_plan(db_session, building_id, *, plan_id=None):
    p = TechnicalPlan(
        id=plan_id or _PLAN_ID,
        building_id=building_id,
        plan_type="floor_plan",
        title="Ground Floor",
        file_path="/plans/gf.pdf",
        file_name="gf.pdf",
    )
    db_session.add(p)
    return p


def _make_annotation(
    db_session,
    plan_id,
    building_id,
    *,
    annotation_type="marker",
    x=0.5,
    y=0.5,
    label="Test",
    zone_id=None,
    sample_id=None,
    element_id=None,
    created_at=None,
):
    ann = PlanAnnotation(
        id=uuid.uuid4(),
        plan_id=plan_id,
        building_id=building_id,
        annotation_type=annotation_type,
        x=x,
        y=y,
        label=label,
        zone_id=zone_id,
        sample_id=sample_id,
        element_id=element_id,
        created_at=created_at,
    )
    db_session.add(ann)
    return ann


def _make_zone(db_session, building_id, *, zone_id=None, name="Zone A"):
    z = Zone(
        id=zone_id or uuid.uuid4(),
        building_id=building_id,
        name=name,
        zone_type="room",
    )
    db_session.add(z)
    return z


def _make_diagnostic(db_session, building_id, *, diagnostic_id=None):
    d = Diagnostic(
        id=diagnostic_id or uuid.uuid4(),
        building_id=building_id,
        diagnostic_type="asbestos",
        status="completed",
    )
    db_session.add(d)
    return d


def _make_sample(db_session, diagnostic_id, *, sample_id=None, concentration=None, created_at=None):
    s = Sample(
        id=sample_id or uuid.uuid4(),
        diagnostic_id=diagnostic_id,
        sample_number=f"S-{uuid.uuid4().hex[:6]}",
        concentration=concentration,
        created_at=created_at,
    )
    db_session.add(s)
    return s


# ---------------------------------------------------------------------------
# Existing tests (preserved)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_plan_no_annotations(db_session, admin_user):
    """A plan with no annotations returns zero points and coverage 0."""
    building = _make_building(db_session, building_id=uuid.uuid4(), created_by=admin_user.id)
    plan = _make_plan(db_session, building.id, plan_id=uuid.uuid4())
    await db_session.commit()

    result = await generate_plan_heatmap(db_session, plan.id, building.id)

    assert result.plan_id == str(plan.id)
    assert result.building_id == str(building.id)
    assert result.total_points == 0
    assert result.coverage_score == 0.0
    assert result.points == []
    assert result.summary == {}


@pytest.mark.asyncio
async def test_various_annotation_types(db_session, admin_user):
    """Different annotation types map to the correct heatmap categories."""
    building = _make_building(db_session, building_id=uuid.uuid4(), created_by=admin_user.id)
    plan = _make_plan(db_session, building.id, plan_id=uuid.uuid4())

    now = datetime.utcnow()
    _make_annotation(db_session, plan.id, building.id, annotation_type="hazard_zone", label="Hazard", created_at=now)
    _make_annotation(
        db_session, plan.id, building.id, annotation_type="sample_location", label="Sample", created_at=now
    )
    _make_annotation(db_session, plan.id, building.id, annotation_type="observation", label="Obs", created_at=now)
    _make_annotation(db_session, plan.id, building.id, annotation_type="marker", label="Marker", created_at=now)
    _make_annotation(
        db_session, plan.id, building.id, annotation_type="zone_reference", label="ZoneRef", created_at=now
    )
    _make_annotation(
        db_session, plan.id, building.id, annotation_type="measurement_point", label="Measure", created_at=now
    )
    await db_session.commit()

    result = await generate_plan_heatmap(db_session, plan.id, building.id)

    assert result.total_points == 6
    categories = {p.category for p in result.points}
    assert categories == {"hazard", "sample", "trust"}

    # Check specific intensities
    by_label = {p.label: p for p in result.points}
    assert by_label["Hazard"].intensity == 0.9
    assert by_label["Hazard"].category == "hazard"
    assert by_label["Sample"].intensity == 0.7
    assert by_label["Sample"].category == "sample"
    assert by_label["Obs"].intensity == 0.5
    assert by_label["Obs"].category == "trust"
    assert by_label["Marker"].intensity == 0.3
    assert by_label["Marker"].category == "trust"
    assert by_label["ZoneRef"].intensity == 0.4
    assert by_label["ZoneRef"].category == "trust"
    assert by_label["Measure"].intensity == 0.6
    assert by_label["Measure"].category == "sample"


@pytest.mark.asyncio
async def test_annotation_linked_to_zone_with_unknowns(db_session, admin_user):
    """An annotation linked to a zone with open unknowns generates an extra 'unknown' point."""
    building = _make_building(db_session, building_id=uuid.uuid4(), created_by=admin_user.id)
    plan = _make_plan(db_session, building.id, plan_id=uuid.uuid4())
    zone = _make_zone(db_session, building.id)

    _make_annotation(
        db_session,
        plan.id,
        building.id,
        annotation_type="zone_reference",
        label="Zone Ann",
        zone_id=zone.id,
    )

    # Create an open unknown issue for this zone
    unknown = UnknownIssue(
        id=uuid.uuid4(),
        building_id=building.id,
        unknown_type="uninspected_zone",
        severity="medium",
        status="open",
        title="Uninspected zone",
        entity_type="zone",
        entity_id=zone.id,
        detected_by="unknown_generator",
    )
    db_session.add(unknown)
    await db_session.commit()

    result = await generate_plan_heatmap(db_session, plan.id, building.id)

    # Should have 2 points: the original trust + the unknown overlay
    assert result.total_points == 2
    categories = [p.category for p in result.points]
    assert "trust" in categories
    assert "unknown" in categories
    assert result.summary["unknown"] == 1


@pytest.mark.asyncio
async def test_annotation_linked_to_sample_with_contradiction(db_session, admin_user):
    """An annotation linked to a sample with contradictions generates an extra 'contradiction' point."""
    building = _make_building(db_session, building_id=uuid.uuid4(), created_by=admin_user.id)
    plan = _make_plan(db_session, building.id, plan_id=uuid.uuid4())
    sample_id = uuid.uuid4()

    _make_annotation(
        db_session,
        plan.id,
        building.id,
        annotation_type="sample_location",
        label="Sample X",
        sample_id=sample_id,
    )

    # Create a contradiction for this sample
    contradiction = DataQualityIssue(
        id=uuid.uuid4(),
        building_id=building.id,
        issue_type="contradiction",
        severity="high",
        status="open",
        entity_type="sample",
        entity_id=sample_id,
        field_name="conflicting_sample_results",
        description="Conflicting results",
        detected_by="contradiction_detector",
    )
    db_session.add(contradiction)
    await db_session.commit()

    result = await generate_plan_heatmap(db_session, plan.id, building.id)

    # Should have 2 points: sample + contradiction
    assert result.total_points == 2
    categories = [p.category for p in result.points]
    assert "sample" in categories
    assert "contradiction" in categories
    assert result.summary["contradiction"] == 1


@pytest.mark.asyncio
async def test_coverage_score_calculation(db_session, admin_user):
    """Coverage score = min(1.0, annotation_count / 10)."""
    building = _make_building(db_session, building_id=uuid.uuid4(), created_by=admin_user.id)
    plan = _make_plan(db_session, building.id, plan_id=uuid.uuid4())

    now = datetime.utcnow()
    # 5 annotations -> coverage = 0.5
    for i in range(5):
        _make_annotation(db_session, plan.id, building.id, label=f"Ann {i}", x=i * 0.2, y=0.5, created_at=now)
    await db_session.commit()

    result = await generate_plan_heatmap(db_session, plan.id, building.id)
    assert result.coverage_score == 0.5
    assert result.total_points == 5


@pytest.mark.asyncio
async def test_coverage_score_capped_at_one(db_session, admin_user):
    """Coverage score never exceeds 1.0 even with many annotations."""
    building = _make_building(db_session, building_id=uuid.uuid4(), created_by=admin_user.id)
    plan = _make_plan(db_session, building.id, plan_id=uuid.uuid4())

    now = datetime.utcnow()
    for i in range(15):
        _make_annotation(db_session, plan.id, building.id, label=f"Ann {i}", x=(i % 10) * 0.1, y=0.5, created_at=now)
    await db_session.commit()

    result = await generate_plan_heatmap(db_session, plan.id, building.id)
    assert result.coverage_score == 1.0


@pytest.mark.asyncio
async def test_summary_counts(db_session, admin_user):
    """Summary dict contains correct counts per category."""
    building = _make_building(db_session, building_id=uuid.uuid4(), created_by=admin_user.id)
    plan = _make_plan(db_session, building.id, plan_id=uuid.uuid4())

    now = datetime.utcnow()
    _make_annotation(db_session, plan.id, building.id, annotation_type="hazard_zone", label="H1", created_at=now)
    _make_annotation(db_session, plan.id, building.id, annotation_type="hazard_zone", label="H2", created_at=now)
    _make_annotation(db_session, plan.id, building.id, annotation_type="sample_location", label="S1", created_at=now)
    _make_annotation(db_session, plan.id, building.id, annotation_type="marker", label="M1", created_at=now)
    await db_session.commit()

    result = await generate_plan_heatmap(db_session, plan.id, building.id)

    assert result.summary == {"hazard": 2, "sample": 1, "trust": 1}
    assert result.total_points == 4


@pytest.mark.asyncio
async def test_boundary_positions(db_session, admin_user):
    """Annotations at boundary positions (0.0, 1.0) are correctly represented."""
    building = _make_building(db_session, building_id=uuid.uuid4(), created_by=admin_user.id)
    plan = _make_plan(db_session, building.id, plan_id=uuid.uuid4())

    _make_annotation(db_session, plan.id, building.id, x=0.0, y=0.0, label="Corner TL")
    _make_annotation(db_session, plan.id, building.id, x=1.0, y=1.0, label="Corner BR")
    _make_annotation(db_session, plan.id, building.id, x=0.0, y=1.0, label="Corner BL")
    _make_annotation(db_session, plan.id, building.id, x=1.0, y=0.0, label="Corner TR")
    await db_session.commit()

    result = await generate_plan_heatmap(db_session, plan.id, building.id)

    assert result.total_points == 4
    positions = [(p.x, p.y) for p in result.points]
    assert (0.0, 0.0) in positions
    assert (1.0, 1.0) in positions
    assert (0.0, 1.0) in positions
    assert (1.0, 0.0) in positions


@pytest.mark.asyncio
async def test_resolved_unknowns_not_included(db_session, admin_user):
    """Resolved unknown issues should NOT generate extra heatmap points."""
    building = _make_building(db_session, building_id=uuid.uuid4(), created_by=admin_user.id)
    plan = _make_plan(db_session, building.id, plan_id=uuid.uuid4())
    zone = _make_zone(db_session, building.id)

    _make_annotation(
        db_session,
        plan.id,
        building.id,
        annotation_type="zone_reference",
        label="Zone Ann",
        zone_id=zone.id,
    )

    # Create a resolved unknown issue (should be ignored)
    unknown = UnknownIssue(
        id=uuid.uuid4(),
        building_id=building.id,
        unknown_type="uninspected_zone",
        severity="medium",
        status="resolved",
        title="Resolved zone issue",
        entity_type="zone",
        entity_id=zone.id,
        detected_by="unknown_generator",
    )
    db_session.add(unknown)
    await db_session.commit()

    result = await generate_plan_heatmap(db_session, plan.id, building.id)

    # Only 1 point (the annotation itself), no unknown overlay
    assert result.total_points == 1
    assert "unknown" not in result.summary


@pytest.mark.asyncio
async def test_heatmap_api_endpoint(client, db_session, admin_user, auth_headers):
    """GET /buildings/{id}/plans/{id}/heatmap returns correct response."""
    building = _make_building(db_session, building_id=uuid.uuid4(), created_by=admin_user.id)
    plan = _make_plan(db_session, building.id, plan_id=uuid.uuid4())
    _make_annotation(db_session, plan.id, building.id, annotation_type="hazard_zone", label="H")
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/buildings/{building.id}/plans/{plan.id}/heatmap",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan_id"] == str(plan.id)
    assert data["total_points"] == 1
    assert data["coverage_score"] == 0.1
    assert len(data["points"]) == 1
    assert data["points"][0]["category"] == "hazard"
    assert data["summary"]["hazard"] == 1


# ---------------------------------------------------------------------------
# Temporal decay tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_decay_factor_recent_annotation(db_session, admin_user):
    """Annotation created now has decay_factor 1.0 and full intensity."""
    building = _make_building(db_session, building_id=uuid.uuid4(), created_by=admin_user.id)
    plan = _make_plan(db_session, building.id, plan_id=uuid.uuid4())
    now = datetime.utcnow()
    _make_annotation(db_session, plan.id, building.id, annotation_type="hazard_zone", label="Recent", created_at=now)
    await db_session.commit()

    result = await generate_plan_heatmap(db_session, plan.id, building.id, reference_date=now)
    pt = result.points[0]
    assert pt.decay_factor == 1.0
    assert pt.intensity == 0.9  # hazard_zone base intensity


@pytest.mark.asyncio
async def test_decay_factor_3_years_old(db_session, admin_user):
    """Annotation >2 years old gets decay_factor 0.5 and halved intensity."""
    building = _make_building(db_session, building_id=uuid.uuid4(), created_by=admin_user.id)
    plan = _make_plan(db_session, building.id, plan_id=uuid.uuid4())
    now = datetime.utcnow()
    old = now - timedelta(days=365 * 3)
    _make_annotation(db_session, plan.id, building.id, annotation_type="hazard_zone", label="3y", created_at=old)
    await db_session.commit()

    result = await generate_plan_heatmap(db_session, plan.id, building.id, reference_date=now)
    pt = result.points[0]
    assert pt.decay_factor == 0.5
    assert pt.intensity == pytest.approx(0.9 * 0.5, abs=0.01)


@pytest.mark.asyncio
async def test_decay_factor_6_years_old(db_session, admin_user):
    """Annotation >5 years old gets decay_factor 0.25 and quarter intensity."""
    building = _make_building(db_session, building_id=uuid.uuid4(), created_by=admin_user.id)
    plan = _make_plan(db_session, building.id, plan_id=uuid.uuid4())
    now = datetime.utcnow()
    very_old = now - timedelta(days=365 * 6)
    _make_annotation(db_session, plan.id, building.id, annotation_type="observation", label="6y", created_at=very_old)
    await db_session.commit()

    result = await generate_plan_heatmap(db_session, plan.id, building.id, reference_date=now)
    pt = result.points[0]
    assert pt.decay_factor == 0.25
    assert pt.intensity == pytest.approx(0.5 * 0.25, abs=0.01)


@pytest.mark.asyncio
async def test_decay_boundary_exactly_2_years(db_session, admin_user):
    """Annotation exactly at 2-year boundary (730 days) still has decay 1.0."""
    building = _make_building(db_session, building_id=uuid.uuid4(), created_by=admin_user.id)
    plan = _make_plan(db_session, building.id, plan_id=uuid.uuid4())
    now = datetime.utcnow()
    boundary = now - timedelta(days=365 * 2)
    _make_annotation(db_session, plan.id, building.id, annotation_type="marker", label="2y", created_at=boundary)
    await db_session.commit()

    result = await generate_plan_heatmap(db_session, plan.id, building.id, reference_date=now)
    pt = result.points[0]
    # Exactly at boundary: timedelta == threshold, not >, so decay is 1.0
    assert pt.decay_factor == 1.0


# ---------------------------------------------------------------------------
# Confidence overlay tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confidence_with_lab_sample(db_session, admin_user):
    """Annotation linked to a sample with concentration gets high confidence."""
    building = _make_building(db_session, building_id=uuid.uuid4(), created_by=admin_user.id)
    plan = _make_plan(db_session, building.id, plan_id=uuid.uuid4())
    diag = _make_diagnostic(db_session, building.id)
    now = datetime.utcnow()
    sample = _make_sample(db_session, diag.id, concentration=120.5, created_at=now)
    _make_annotation(
        db_session,
        plan.id,
        building.id,
        annotation_type="sample_location",
        label="Lab Sample",
        sample_id=sample.id,
        created_at=now,
    )
    await db_session.commit()

    result = await generate_plan_heatmap(db_session, plan.id, building.id, reference_date=now)
    pt = result.points[0]
    assert pt.confidence == 0.9  # lab base


@pytest.mark.asyncio
async def test_confidence_without_lab_results(db_session, admin_user):
    """Annotation linked to sample without concentration gets lower confidence."""
    building = _make_building(db_session, building_id=uuid.uuid4(), created_by=admin_user.id)
    plan = _make_plan(db_session, building.id, plan_id=uuid.uuid4())
    diag = _make_diagnostic(db_session, building.id)
    now = datetime.utcnow()
    sample = _make_sample(db_session, diag.id, concentration=None, created_at=now)
    _make_annotation(
        db_session,
        plan.id,
        building.id,
        annotation_type="sample_location",
        label="Visual Sample",
        sample_id=sample.id,
        created_at=now,
    )
    await db_session.commit()

    result = await generate_plan_heatmap(db_session, plan.id, building.id, reference_date=now)
    pt = result.points[0]
    assert pt.confidence == 0.5  # visual base


@pytest.mark.asyncio
async def test_confidence_none_without_sample(db_session, admin_user):
    """Annotation not linked to any sample has confidence=None."""
    building = _make_building(db_session, building_id=uuid.uuid4(), created_by=admin_user.id)
    plan = _make_plan(db_session, building.id, plan_id=uuid.uuid4())
    now = datetime.utcnow()
    _make_annotation(db_session, plan.id, building.id, annotation_type="marker", label="No sample", created_at=now)
    await db_session.commit()

    result = await generate_plan_heatmap(db_session, plan.id, building.id, reference_date=now)
    pt = result.points[0]
    assert pt.confidence is None


@pytest.mark.asyncio
async def test_confidence_decays_with_old_sample(db_session, admin_user):
    """Confidence decreases for old samples (>2y penalty)."""
    building = _make_building(db_session, building_id=uuid.uuid4(), created_by=admin_user.id)
    plan = _make_plan(db_session, building.id, plan_id=uuid.uuid4())
    diag = _make_diagnostic(db_session, building.id)
    now = datetime.utcnow()
    old = now - timedelta(days=365 * 3)
    sample = _make_sample(db_session, diag.id, concentration=80.0, created_at=old)
    _make_annotation(
        db_session,
        plan.id,
        building.id,
        annotation_type="sample_location",
        label="Old Lab",
        sample_id=sample.id,
        created_at=old,
    )
    await db_session.commit()

    result = await generate_plan_heatmap(db_session, plan.id, building.id, reference_date=now)
    pt = result.points[0]
    # 0.9 base - 0.15 age penalty = 0.75
    assert pt.confidence == 0.75


# ---------------------------------------------------------------------------
# Zone heatmap stats tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_zone_stats_empty_building(db_session, admin_user):
    """Building with no zones returns empty stats."""
    building = _make_building(db_session, building_id=uuid.uuid4(), created_by=admin_user.id)
    await db_session.commit()

    stats = await get_zone_heatmap_stats(db_session, building.id)
    assert stats == []


@pytest.mark.asyncio
async def test_zone_stats_zones_with_annotations(db_session, admin_user):
    """Zone stats correctly aggregate annotation data."""
    building = _make_building(db_session, building_id=uuid.uuid4(), created_by=admin_user.id)
    plan = _make_plan(db_session, building.id, plan_id=uuid.uuid4())
    zone_a = _make_zone(db_session, building.id, name="Zone A")
    _make_zone(db_session, building.id, name="Zone B")

    now = datetime.utcnow()
    # Zone A: 3 annotations
    _make_annotation(
        db_session, plan.id, building.id, annotation_type="hazard_zone", label="H1", zone_id=zone_a.id, created_at=now
    )
    _make_annotation(
        db_session, plan.id, building.id, annotation_type="marker", label="M1", zone_id=zone_a.id, created_at=now
    )
    _make_annotation(
        db_session, plan.id, building.id, annotation_type="observation", label="O1", zone_id=zone_a.id, created_at=now
    )
    # Zone B: 0 annotations
    await db_session.commit()

    stats = await get_zone_heatmap_stats(db_session, building.id)
    assert len(stats) == 2

    by_name = {s.zone_name: s for s in stats}
    assert by_name["Zone A"].point_count == 3
    assert by_name["Zone A"].avg_intensity > 0
    assert by_name["Zone A"].coverage_score == 0.6  # 3/5
    assert by_name["Zone B"].point_count == 0
    assert by_name["Zone B"].avg_intensity == 0.0
    assert by_name["Zone B"].coverage_score == 0.0


# ---------------------------------------------------------------------------
# Heatmap-at-date tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_heatmap_at_date_filters_future_annotations(db_session, admin_user):
    """Annotations created after target_date are excluded."""
    building = _make_building(db_session, building_id=uuid.uuid4(), created_by=admin_user.id)
    plan = _make_plan(db_session, building.id, plan_id=uuid.uuid4())

    now = datetime.utcnow()
    past = now - timedelta(days=100)
    future = now + timedelta(days=100)

    _make_annotation(db_session, plan.id, building.id, label="Past", created_at=past)
    _make_annotation(db_session, plan.id, building.id, label="Future", created_at=future)
    await db_session.commit()

    result = await get_heatmap_at_date(db_session, plan.id, building.id, now.date())
    assert result.total_points == 1
    assert result.points[0].label == "Past"


@pytest.mark.asyncio
async def test_heatmap_at_date_applies_decay_relative_to_target(db_session, admin_user):
    """Decay is computed relative to target_date, not utcnow."""
    building = _make_building(db_session, building_id=uuid.uuid4(), created_by=admin_user.id)
    plan = _make_plan(db_session, building.id, plan_id=uuid.uuid4())

    now = datetime.utcnow()
    # Annotation 1 year old relative to target_date => no decay
    ann_date = now - timedelta(days=365)
    _make_annotation(db_session, plan.id, building.id, label="1y", annotation_type="hazard_zone", created_at=ann_date)
    await db_session.commit()

    result = await get_heatmap_at_date(db_session, plan.id, building.id, now.date())
    pt = result.points[0]
    assert pt.decay_factor == 1.0

    # Now check with a target 4 years in the future — same annotation is >2y old then
    future_target = (now + timedelta(days=365 * 3)).date()
    result2 = await get_heatmap_at_date(db_session, plan.id, building.id, future_target)
    pt2 = result2.points[0]
    assert pt2.decay_factor == 0.5


@pytest.mark.asyncio
async def test_heatmap_at_date_empty_when_no_annotations_before(db_session, admin_user):
    """If no annotations exist before target_date, result is empty."""
    building = _make_building(db_session, building_id=uuid.uuid4(), created_by=admin_user.id)
    plan = _make_plan(db_session, building.id, plan_id=uuid.uuid4())

    now = datetime.utcnow()
    _make_annotation(db_session, plan.id, building.id, label="Future", created_at=now + timedelta(days=10))
    await db_session.commit()

    result = await get_heatmap_at_date(db_session, plan.id, building.id, now.date())
    assert result.total_points == 0
    assert result.points == []


# ---------------------------------------------------------------------------
# Coverage gap detection tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_coverage_gaps_no_zones(db_session, admin_user):
    """Building with no zones => no gaps, coverage 1.0."""
    building = _make_building(db_session, building_id=uuid.uuid4(), created_by=admin_user.id)
    plan = _make_plan(db_session, building.id, plan_id=uuid.uuid4())
    await db_session.commit()

    report = await detect_coverage_gaps(db_session, plan.id, building.id)
    assert report.gaps == []
    assert report.overall_coverage == 1.0


@pytest.mark.asyncio
async def test_coverage_gaps_no_annotations_gap(db_session, admin_user):
    """Zone with zero annotations is flagged as 'no_annotations' gap."""
    building = _make_building(db_session, building_id=uuid.uuid4(), created_by=admin_user.id)
    plan = _make_plan(db_session, building.id, plan_id=uuid.uuid4())
    _make_zone(db_session, building.id, name="Empty Zone")
    await db_session.commit()

    report = await detect_coverage_gaps(db_session, plan.id, building.id)
    assert len(report.gaps) == 1
    assert report.gaps[0].gap_type == "no_annotations"
    assert report.gaps[0].zone_name == "Empty Zone"
    assert report.overall_coverage == 0.0


@pytest.mark.asyncio
async def test_coverage_gaps_low_density(db_session, admin_user):
    """Zone with only 1 recent annotation is flagged as 'low_density' gap."""
    building = _make_building(db_session, building_id=uuid.uuid4(), created_by=admin_user.id)
    plan = _make_plan(db_session, building.id, plan_id=uuid.uuid4())
    zone = _make_zone(db_session, building.id, name="Sparse Zone")

    now = datetime.utcnow()
    _make_annotation(
        db_session, plan.id, building.id, annotation_type="marker", label="Only one", zone_id=zone.id, created_at=now
    )
    await db_session.commit()

    report = await detect_coverage_gaps(db_session, plan.id, building.id)
    assert len(report.gaps) == 1
    assert report.gaps[0].gap_type == "low_density"
    assert report.gaps[0].zone_name == "Sparse Zone"
    # low_density still counts as partially covered
    assert report.overall_coverage > 0.0


@pytest.mark.asyncio
async def test_coverage_gaps_stale_data(db_session, admin_user):
    """Zone where all annotations are >2y old is flagged as 'stale_data' gap."""
    building = _make_building(db_session, building_id=uuid.uuid4(), created_by=admin_user.id)
    plan = _make_plan(db_session, building.id, plan_id=uuid.uuid4())
    zone = _make_zone(db_session, building.id, name="Stale Zone")

    old = datetime.utcnow() - timedelta(days=365 * 3)
    _make_annotation(
        db_session, plan.id, building.id, annotation_type="marker", label="Old1", zone_id=zone.id, created_at=old
    )
    _make_annotation(
        db_session, plan.id, building.id, annotation_type="marker", label="Old2", zone_id=zone.id, created_at=old
    )
    await db_session.commit()

    report = await detect_coverage_gaps(db_session, plan.id, building.id)
    assert len(report.gaps) == 1
    assert report.gaps[0].gap_type == "stale_data"
    assert report.gaps[0].zone_name == "Stale Zone"


@pytest.mark.asyncio
async def test_coverage_gaps_well_covered_zone(db_session, admin_user):
    """Zone with >=2 recent annotations has no gap, coverage is 1.0."""
    building = _make_building(db_session, building_id=uuid.uuid4(), created_by=admin_user.id)
    plan = _make_plan(db_session, building.id, plan_id=uuid.uuid4())
    zone = _make_zone(db_session, building.id, name="Good Zone")

    now = datetime.utcnow()
    _make_annotation(
        db_session, plan.id, building.id, annotation_type="marker", label="A1", zone_id=zone.id, created_at=now
    )
    _make_annotation(
        db_session, plan.id, building.id, annotation_type="observation", label="A2", zone_id=zone.id, created_at=now
    )
    await db_session.commit()

    report = await detect_coverage_gaps(db_session, plan.id, building.id)
    assert len(report.gaps) == 0
    assert report.overall_coverage == 1.0
