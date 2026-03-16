"""Tests for the Knowledge Gap service and API endpoints."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.models.zone import Zone
from app.services.knowledge_gap_service import (
    ALL_POLLUTANTS,
    REQUIRED_DOCUMENT_TYPES,
    analyze_knowledge_gaps,
    estimate_knowledge_completeness,
    get_investigation_priorities,
    get_portfolio_knowledge_overview,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_building(admin_id, **kwargs):
    defaults = dict(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        created_by=admin_id,
        status="active",
    )
    defaults.update(kwargs)
    return Building(**defaults)


def _make_diagnostic(building_id, **kwargs):
    defaults = dict(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type="asbestos",
        status="completed",
        date_report=datetime.now(UTC).date(),
    )
    defaults.update(kwargs)
    return Diagnostic(**defaults)


def _make_sample(diagnostic_id, pollutant_type="asbestos", **kwargs):
    defaults = dict(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic_id,
        sample_number=f"S-{uuid.uuid4().hex[:6]}",
        pollutant_type=pollutant_type,
        concentration=1.5,
        unit="percent_weight",
        risk_level="low",
    )
    defaults.update(kwargs)
    return Sample(**defaults)


# ---------------------------------------------------------------------------
# FN1: analyze_knowledge_gaps
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gaps_empty_building(db_session, admin_user, sample_building):
    """Building with no data should have gaps for all pollutants + documents."""
    result = await analyze_knowledge_gaps(db_session, sample_building.id)
    assert result.total_gaps > 0
    gap_types = {g.gap_type for g in result.gaps}
    assert "undiagnosed_pollutant" in gap_types
    assert "missing_document" in gap_types


@pytest.mark.asyncio
async def test_gaps_nonexistent_building(db_session):
    """Non-existent building returns empty gaps."""
    result = await analyze_knowledge_gaps(db_session, uuid.uuid4())
    assert result.total_gaps == 0
    assert result.gaps == []


@pytest.mark.asyncio
async def test_gaps_all_pollutants_covered(db_session, admin_user, sample_building):
    """When all 5 pollutants have samples, no undiagnosed_pollutant gaps."""
    diag = _make_diagnostic(sample_building.id)
    db_session.add(diag)
    await db_session.flush()

    for p in ALL_POLLUTANTS:
        db_session.add(_make_sample(diag.id, pollutant_type=p))
    await db_session.commit()

    result = await analyze_knowledge_gaps(db_session, sample_building.id)
    undiag_gaps = [g for g in result.gaps if g.gap_type == "undiagnosed_pollutant"]
    assert len(undiag_gaps) == 0


@pytest.mark.asyncio
async def test_gaps_unsampled_zones(db_session, admin_user, sample_building):
    """Zones without matching samples should be flagged."""
    zone = Zone(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        zone_type="room",
        name="Basement Storage",
    )
    db_session.add(zone)
    await db_session.commit()

    result = await analyze_knowledge_gaps(db_session, sample_building.id)
    zone_gaps = [g for g in result.gaps if g.gap_type == "unsampled_zone"]
    assert len(zone_gaps) >= 1
    assert any("Basement Storage" in g.description for g in zone_gaps)


@pytest.mark.asyncio
async def test_gaps_sampled_zone_not_flagged(db_session, admin_user, sample_building):
    """Zone that matches a sample's location_room should NOT be flagged."""
    zone = Zone(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        zone_type="room",
        name="Office A",
    )
    db_session.add(zone)

    diag = _make_diagnostic(sample_building.id)
    db_session.add(diag)
    await db_session.flush()

    db_session.add(_make_sample(diag.id, location_room="Office A"))
    await db_session.commit()

    result = await analyze_knowledge_gaps(db_session, sample_building.id)
    zone_gaps = [g for g in result.gaps if g.gap_type == "unsampled_zone"]
    assert all("Office A" not in g.description for g in zone_gaps)


@pytest.mark.asyncio
async def test_gaps_outdated_diagnostic(db_session, admin_user, sample_building):
    """Diagnostic older than 5 years should be flagged."""
    old_date = (datetime.now(UTC) - timedelta(days=6 * 365)).date()
    diag = _make_diagnostic(sample_building.id, date_report=old_date)
    db_session.add(diag)
    await db_session.commit()

    result = await analyze_knowledge_gaps(db_session, sample_building.id)
    outdated = [g for g in result.gaps if g.gap_type == "outdated_diagnostic"]
    assert len(outdated) >= 1


@pytest.mark.asyncio
async def test_gaps_conflicting_results(db_session, admin_user, sample_building):
    """Samples with conflicting risk levels should be flagged."""
    diag = _make_diagnostic(sample_building.id)
    db_session.add(diag)
    await db_session.flush()

    db_session.add(_make_sample(diag.id, pollutant_type="asbestos", risk_level="low"))
    db_session.add(_make_sample(diag.id, pollutant_type="asbestos", risk_level="critical"))
    await db_session.commit()

    result = await analyze_knowledge_gaps(db_session, sample_building.id)
    conflicts = [g for g in result.gaps if g.gap_type == "conflicting_results"]
    assert len(conflicts) >= 1


@pytest.mark.asyncio
async def test_gaps_missing_documents(db_session, admin_user, sample_building):
    """Missing required document types should be flagged."""
    result = await analyze_knowledge_gaps(db_session, sample_building.id)
    doc_gaps = [g for g in result.gaps if g.gap_type == "missing_document"]
    assert len(doc_gaps) == len(REQUIRED_DOCUMENT_TYPES)


@pytest.mark.asyncio
async def test_gaps_document_present_not_flagged(db_session, admin_user, sample_building):
    """Present document type should NOT be flagged."""
    doc = Document(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        file_path="/test.pdf",
        file_name="report.pdf",
        document_type="diagnostic_report",
    )
    db_session.add(doc)
    await db_session.commit()

    result = await analyze_knowledge_gaps(db_session, sample_building.id)
    doc_gaps = [g for g in result.gaps if g.gap_type == "missing_document"]
    assert all("diagnostic report" not in g.description for g in doc_gaps)


@pytest.mark.asyncio
async def test_gaps_severity_counts(db_session, admin_user, sample_building):
    """Critical and high counts should match gap severities."""
    result = await analyze_knowledge_gaps(db_session, sample_building.id)
    actual_critical = sum(1 for g in result.gaps if g.severity == "critical")
    actual_high = sum(1 for g in result.gaps if g.severity == "high")
    assert result.critical_count == actual_critical
    assert result.high_count == actual_high


# ---------------------------------------------------------------------------
# FN2: get_investigation_priorities
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_priorities_ranked_by_roi(db_session, admin_user, sample_building):
    """Priorities should be ranked by ROI descending."""
    result = await get_investigation_priorities(db_session, sample_building.id)
    assert len(result.priorities) > 0
    for i in range(len(result.priorities) - 1):
        assert result.priorities[i].roi_score >= result.priorities[i + 1].roi_score


@pytest.mark.asyncio
async def test_priorities_rank_numbering(db_session, admin_user, sample_building):
    """Ranks should be 1-based sequential."""
    result = await get_investigation_priorities(db_session, sample_building.id)
    for i, p in enumerate(result.priorities, start=1):
        assert p.rank == i


@pytest.mark.asyncio
async def test_priorities_total_cost(db_session, admin_user, sample_building):
    """Total cost should equal sum of individual costs."""
    result = await get_investigation_priorities(db_session, sample_building.id)
    expected = sum(p.estimated_cost_chf for p in result.priorities)
    assert abs(result.total_estimated_cost_chf - expected) < 0.01


# ---------------------------------------------------------------------------
# FN3: estimate_knowledge_completeness
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_completeness_empty_building(db_session, admin_user, sample_building):
    """Empty building should have low completeness."""
    result = await estimate_knowledge_completeness(db_session, sample_building.id)
    assert result.overall_score < 50.0
    assert len(result.pollutant_scores) == len(ALL_POLLUTANTS)
    assert len(result.document_scores) == len(REQUIRED_DOCUMENT_TYPES)
    assert len(result.radar_chart) == 5


@pytest.mark.asyncio
async def test_completeness_nonexistent_building(db_session):
    """Non-existent building returns 0 score with empty lists."""
    result = await estimate_knowledge_completeness(db_session, uuid.uuid4())
    assert result.overall_score == 0.0
    assert result.pollutant_scores == []


@pytest.mark.asyncio
async def test_completeness_all_pollutants_sampled(db_session, admin_user, sample_building):
    """All pollutants sampled with recent diagnostic should yield high pollutant score."""
    diag = _make_diagnostic(sample_building.id)
    db_session.add(diag)
    await db_session.flush()

    for p in ALL_POLLUTANTS:
        db_session.add(_make_sample(diag.id, pollutant_type=p))
    await db_session.commit()

    result = await estimate_knowledge_completeness(db_session, sample_building.id)
    for ps in result.pollutant_scores:
        assert ps.score == 100.0
        assert ps.has_samples is True


@pytest.mark.asyncio
async def test_completeness_radar_chart_axes(db_session, admin_user, sample_building):
    """Radar chart should have 5 named axes."""
    result = await estimate_knowledge_completeness(db_session, sample_building.id)
    axes = {r.axis for r in result.radar_chart}
    assert axes == {"Pollutants", "Zones", "Documents", "Diagnostics", "Samples"}


@pytest.mark.asyncio
async def test_completeness_zone_scores_with_zones(db_session, admin_user, sample_building):
    """Zones with samples score 100, without score 0."""
    z1 = Zone(id=uuid.uuid4(), building_id=sample_building.id, zone_type="room", name="Room1")
    z2 = Zone(id=uuid.uuid4(), building_id=sample_building.id, zone_type="room", name="Room2")
    db_session.add_all([z1, z2])

    diag = _make_diagnostic(sample_building.id)
    db_session.add(diag)
    await db_session.flush()
    db_session.add(_make_sample(diag.id, location_room="Room1"))
    await db_session.commit()

    result = await estimate_knowledge_completeness(db_session, sample_building.id)
    zs_map = {zs.zone_name: zs for zs in result.zone_scores}
    assert zs_map["Room1"].score == 100.0
    assert zs_map["Room2"].score == 0.0


# ---------------------------------------------------------------------------
# FN4: get_portfolio_knowledge_overview
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_portfolio_no_buildings(db_session):
    """Org with no buildings should return empty overview."""
    org_id = uuid.uuid4()
    org = Organization(id=org_id, name="Empty Org", type="property_management")
    db_session.add(org)
    await db_session.commit()

    result = await get_portfolio_knowledge_overview(db_session, org_id)
    assert result.building_count == 0
    assert result.avg_completeness == 0.0


@pytest.mark.asyncio
async def test_portfolio_with_buildings(db_session):
    """Org with buildings should return aggregated data."""
    org_id = uuid.uuid4()
    org = Organization(id=org_id, name="Test Regie", type="property_management")
    db_session.add(org)

    user = User(
        id=uuid.uuid4(),
        email="portfolio@test.ch",
        password_hash="hashed",
        first_name="Port",
        last_name="Folio",
        role="owner",
        is_active=True,
        organization_id=org_id,
    )
    db_session.add(user)
    await db_session.flush()

    b1 = _make_building(user.id, address="Addr 1")
    b2 = _make_building(user.id, address="Addr 2")
    db_session.add_all([b1, b2])
    await db_session.commit()

    result = await get_portfolio_knowledge_overview(db_session, org_id)
    assert result.building_count == 2
    assert result.avg_completeness >= 0.0
    assert len(result.worst_buildings) <= 5
    assert result.estimated_cost_to_100 >= result.estimated_cost_to_90
    assert result.estimated_cost_to_90 >= result.estimated_cost_to_80


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_knowledge_gaps(client, auth_headers, sample_building):
    """GET /buildings/{id}/knowledge-gaps returns 200."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/knowledge-gaps",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "gaps" in data
    assert "total_gaps" in data


@pytest.mark.asyncio
async def test_api_knowledge_gaps_404(client, auth_headers):
    """GET /buildings/{bad_id}/knowledge-gaps returns 404."""
    resp = await client.get(
        f"/api/v1/buildings/{uuid.uuid4()}/knowledge-gaps",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_investigation_priorities(client, auth_headers, sample_building):
    """GET /buildings/{id}/investigation-priorities returns 200."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/investigation-priorities",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "priorities" in data


@pytest.mark.asyncio
async def test_api_knowledge_completeness(client, auth_headers, sample_building):
    """GET /buildings/{id}/knowledge-completeness returns 200."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/knowledge-completeness",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "overall_score" in data
    assert "radar_chart" in data


@pytest.mark.asyncio
async def test_api_knowledge_completeness_404(client, auth_headers):
    """GET /buildings/{bad_id}/knowledge-completeness returns 404."""
    resp = await client.get(
        f"/api/v1/buildings/{uuid.uuid4()}/knowledge-completeness",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_portfolio_overview(client, auth_headers, db_session):
    """GET /organizations/{id}/knowledge-overview returns 200."""
    org_id = uuid.uuid4()
    org = Organization(id=org_id, name="API Org", type="property_management")
    db_session.add(org)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/organizations/{org_id}/knowledge-overview",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "building_count" in data
    assert "avg_completeness" in data


@pytest.mark.asyncio
async def test_api_requires_auth(client, sample_building):
    """Endpoints should reject unauthenticated requests."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/knowledge-gaps",
    )
    assert resp.status_code == 403
