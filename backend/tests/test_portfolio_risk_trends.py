"""Tests for portfolio risk trends service and API endpoints."""

import uuid
from datetime import date, datetime, timedelta

import pytest

from app.models.building import Building
from app.models.building_change import BuildingSignal
from app.models.building_risk_score import BuildingRiskScore
from app.models.building_snapshot import BuildingSnapshot
from app.services.portfolio_risk_trends_service import (
    compare_portfolio_risk_periods,
    get_building_risk_trajectory,
    get_portfolio_risk_report,
    get_portfolio_risk_snapshot,
    get_portfolio_risk_trend,
    get_risk_hotspots,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_building(db, user_id, address="Rue Test 1", status="active"):
    b = Building(
        id=uuid.uuid4(),
        address=address,
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        created_by=user_id,
        status=status,
    )
    db.add(b)
    await db.flush()
    return b


async def _create_risk_score(db, building_id, level="medium", confidence=0.5):
    rs = BuildingRiskScore(
        id=uuid.uuid4(),
        building_id=building_id,
        overall_risk_level=level,
        confidence=confidence,
    )
    db.add(rs)
    await db.flush()
    return rs


async def _create_snapshot(db, building_id, captured_at, overall_trust=None, passport_grade=None):
    snap = BuildingSnapshot(
        id=uuid.uuid4(),
        building_id=building_id,
        snapshot_type="manual",
        overall_trust=overall_trust,
        passport_grade=passport_grade,
        captured_at=captured_at,
    )
    db.add(snap)
    await db.flush()
    return snap


async def _create_signal(db, building_id, severity="high", detected_at=None):
    sig = BuildingSignal(
        id=uuid.uuid4(),
        building_id=building_id,
        signal_type="risk_change",
        severity=severity,
        title="Risk signal",
        description="",
        based_on_type="event",
        status="active",
        detected_at=detected_at or datetime.now(),
    )
    db.add(sig)
    await db.flush()
    return sig


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_portfolio_trend_no_buildings(db_session, admin_user):
    """Portfolio trend with no buildings returns empty results."""
    result = await get_portfolio_risk_trend(db_session)
    assert result.total_buildings == 0
    assert result.data_points == []
    assert result.trend_direction == "stable"
    assert result.buildings_improving == 0
    assert result.buildings_deteriorating == 0
    assert result.buildings_stable == 0


@pytest.mark.asyncio
async def test_portfolio_trend_with_snapshots(db_session, admin_user):
    """Portfolio trend with buildings and snapshots returns data points."""
    b1 = await _create_building(db_session, admin_user.id)
    b2 = await _create_building(db_session, admin_user.id, address="Rue Test 2")

    now = datetime.now()
    # Create snapshots across 3 months
    await _create_snapshot(db_session, b1.id, now - timedelta(days=90), overall_trust=0.3)
    await _create_snapshot(db_session, b1.id, now - timedelta(days=30), overall_trust=0.5)
    await _create_snapshot(db_session, b2.id, now - timedelta(days=60), overall_trust=0.7)
    await db_session.commit()

    result = await get_portfolio_risk_trend(db_session, months=12)
    assert result.total_buildings == 2
    assert len(result.data_points) >= 2
    assert result.avg_risk_score is not None


@pytest.mark.asyncio
async def test_building_trajectory_improving(db_session, admin_user):
    """Building trajectory should detect improving trend."""
    b = await _create_building(db_session, admin_user.id)
    now = datetime.now()
    # High risk 3 months ago, low risk now
    await _create_snapshot(db_session, b.id, now - timedelta(days=90), overall_trust=0.9)
    await _create_snapshot(db_session, b.id, now - timedelta(days=1), overall_trust=0.1)
    await db_session.commit()

    result = await get_building_risk_trajectory(db_session, b.id, months=12)
    assert result.building_id == b.id
    assert result.trend_direction == "improving"
    assert result.change_rate is not None
    assert result.change_rate < 0


@pytest.mark.asyncio
async def test_building_trajectory_deteriorating(db_session, admin_user):
    """Building trajectory should detect deteriorating trend."""
    b = await _create_building(db_session, admin_user.id)
    now = datetime.now()
    await _create_snapshot(db_session, b.id, now - timedelta(days=90), overall_trust=0.1)
    await _create_snapshot(db_session, b.id, now - timedelta(days=1), overall_trust=0.9)
    await db_session.commit()

    result = await get_building_risk_trajectory(db_session, b.id, months=12)
    assert result.trend_direction == "deteriorating"
    assert result.change_rate is not None
    assert result.change_rate > 0


@pytest.mark.asyncio
async def test_building_trajectory_stable(db_session, admin_user):
    """Building trajectory should detect stable trend."""
    b = await _create_building(db_session, admin_user.id)
    now = datetime.now()
    await _create_snapshot(db_session, b.id, now - timedelta(days=90), overall_trust=0.5)
    await _create_snapshot(db_session, b.id, now - timedelta(days=1), overall_trust=0.5)
    await db_session.commit()

    result = await get_building_risk_trajectory(db_session, b.id, months=12)
    assert result.trend_direction == "stable"


@pytest.mark.asyncio
async def test_building_trajectory_no_snapshots(db_session, admin_user):
    """Building trajectory with no snapshots returns stable."""
    b = await _create_building(db_session, admin_user.id)
    await db_session.commit()

    result = await get_building_risk_trajectory(db_session, b.id, months=12)
    assert result.data_points == []
    assert result.trend_direction == "stable"
    assert result.change_rate is None


@pytest.mark.asyncio
async def test_risk_distribution_snapshot(db_session, admin_user):
    """Risk snapshot returns correct distribution."""
    b1 = await _create_building(db_session, admin_user.id)
    b2 = await _create_building(db_session, admin_user.id, address="Rue Test 2")
    b3 = await _create_building(db_session, admin_user.id, address="Rue Test 3")
    await _create_risk_score(db_session, b1.id, "high", 0.8)
    await _create_risk_score(db_session, b2.id, "low", 0.2)
    await _create_risk_score(db_session, b3.id, "high", 0.9)
    await db_session.commit()

    result = await get_portfolio_risk_snapshot(db_session)
    assert result.date == date.today()
    assert len(result.distribution) >= 1
    total_count = sum(d.count for d in result.distribution)
    assert total_count == 3
    # Check percentages sum to ~100
    total_pct = sum(d.percentage for d in result.distribution)
    assert abs(total_pct - 100.0) < 0.1


@pytest.mark.asyncio
async def test_median_and_average_computation(db_session, admin_user):
    """Snapshot computes correct avg and median."""
    b1 = await _create_building(db_session, admin_user.id)
    b2 = await _create_building(db_session, admin_user.id, address="Rue Test 2")
    b3 = await _create_building(db_session, admin_user.id, address="Rue Test 3")
    await _create_risk_score(db_session, b1.id, "low", 0.2)
    await _create_risk_score(db_session, b2.id, "medium", 0.5)
    await _create_risk_score(db_session, b3.id, "high", 0.8)
    await db_session.commit()

    result = await get_portfolio_risk_snapshot(db_session)
    assert result.avg_score is not None
    assert result.median_score is not None
    assert result.avg_score == round((0.2 + 0.5 + 0.8) / 3, 4)
    assert result.median_score == 0.5


@pytest.mark.asyncio
async def test_risk_hotspots_returns_worst(db_session, admin_user):
    """Hotspots returns buildings with high/critical risk, sorted by score."""
    b1 = await _create_building(db_session, admin_user.id, address="Low Risk")
    b2 = await _create_building(db_session, admin_user.id, address="High Risk")
    b3 = await _create_building(db_session, admin_user.id, address="Critical Risk")
    await _create_risk_score(db_session, b1.id, "low", 0.2)
    await _create_risk_score(db_session, b2.id, "high", 0.8)
    await _create_risk_score(db_session, b3.id, "critical", 0.95)
    await db_session.commit()

    result = await get_risk_hotspots(db_session, limit=10)
    # Should only include high and critical
    assert len(result) == 2
    assert result[0].building_id == b3.id
    assert result[1].building_id == b2.id


@pytest.mark.asyncio
async def test_hotspots_with_signals(db_session, admin_user):
    """Hotspots include signal counts."""
    b = await _create_building(db_session, admin_user.id)
    await _create_risk_score(db_session, b.id, "high", 0.8)
    await _create_signal(db_session, b.id, severity="high")
    await _create_signal(db_session, b.id, severity="critical")
    await db_session.commit()

    result = await get_risk_hotspots(db_session, limit=10)
    assert len(result) == 1
    assert result[0].signal_count == 2


@pytest.mark.asyncio
async def test_hotspots_limit(db_session, admin_user):
    """Hotspots respects limit parameter."""
    for i in range(5):
        b = await _create_building(db_session, admin_user.id, address=f"Building {i}")
        await _create_risk_score(db_session, b.id, "high", 0.8 + i * 0.01)
    await db_session.commit()

    result = await get_risk_hotspots(db_session, limit=3)
    assert len(result) == 3


@pytest.mark.asyncio
async def test_full_risk_report(db_session, admin_user):
    """Full risk report composes all sub-reports."""
    b1 = await _create_building(db_session, admin_user.id)
    b2 = await _create_building(db_session, admin_user.id, address="Rue Test 2")
    await _create_risk_score(db_session, b1.id, "high", 0.8)
    await _create_risk_score(db_session, b2.id, "low", 0.2)
    now = datetime.now()
    await _create_snapshot(db_session, b1.id, now - timedelta(days=30), overall_trust=0.8)
    await db_session.commit()

    result = await get_portfolio_risk_report(db_session, months=12)
    assert result.portfolio_trend.total_buildings == 2
    assert result.current_snapshot.date == date.today()
    assert isinstance(result.hotspots, list)
    assert result.at_risk_count == len(result.hotspots)
    assert len(result.high_risk_buildings) == result.at_risk_count


@pytest.mark.asyncio
async def test_period_comparison_improvement(db_session, admin_user):
    """Period comparison detects improvement."""
    b = await _create_building(db_session, admin_user.id)
    now = datetime.now()
    # Period 1: high risk
    await _create_snapshot(db_session, b.id, now - timedelta(days=90), overall_trust=0.9)
    # Period 2: low risk
    await _create_snapshot(db_session, b.id, now - timedelta(days=10), overall_trust=0.2)
    await db_session.commit()

    p1_start = (now - timedelta(days=120)).date()
    p1_end = (now - timedelta(days=60)).date()
    p2_start = (now - timedelta(days=30)).date()
    p2_end = now.date()

    result = await compare_portfolio_risk_periods(db_session, p1_start, p1_end, p2_start, p2_end)
    assert result["score_delta"] is not None
    assert result["score_delta"] < 0
    assert result["improvement"] is True


@pytest.mark.asyncio
async def test_period_comparison_no_data(db_session, admin_user):
    """Period comparison with no snapshots returns None delta."""
    result = await compare_portfolio_risk_periods(
        db_session,
        date(2020, 1, 1),
        date(2020, 6, 30),
        date(2021, 1, 1),
        date(2021, 6, 30),
    )
    assert result["score_delta"] is None
    assert result["improvement"] is False
    assert result["period1"]["building_count"] == 0
    assert result["period2"]["building_count"] == 0


@pytest.mark.asyncio
async def test_change_rate_computation(db_session, admin_user):
    """Change rate is computed as score change per month."""
    b = await _create_building(db_session, admin_user.id)
    now = datetime.now()
    # 60 days apart, score change of 0.4
    await _create_snapshot(db_session, b.id, now - timedelta(days=60), overall_trust=0.3)
    await _create_snapshot(db_session, b.id, now - timedelta(days=0), overall_trust=0.7)
    await db_session.commit()

    result = await get_building_risk_trajectory(db_session, b.id, months=12)
    assert result.change_rate is not None
    # 0.4 change over ~2 months = ~0.2 per month
    assert result.change_rate > 0.15
    assert result.change_rate < 0.25


@pytest.mark.asyncio
async def test_trend_direction_detection_from_data_points(db_session, admin_user):
    """Trend direction is correctly detected from multiple data points."""
    b = await _create_building(db_session, admin_user.id)
    now = datetime.now()
    # Multiple points showing deterioration
    await _create_snapshot(db_session, b.id, now - timedelta(days=90), overall_trust=0.2)
    await _create_snapshot(db_session, b.id, now - timedelta(days=60), overall_trust=0.4)
    await _create_snapshot(db_session, b.id, now - timedelta(days=30), overall_trust=0.6)
    await _create_snapshot(db_session, b.id, now - timedelta(days=1), overall_trust=0.8)
    await db_session.commit()

    result = await get_building_risk_trajectory(db_session, b.id, months=12)
    assert result.trend_direction == "deteriorating"
    assert len(result.data_points) == 4


@pytest.mark.asyncio
async def test_portfolio_trend_buildings_stable_without_snapshots(db_session, admin_user):
    """Buildings without snapshots are counted as stable."""
    await _create_building(db_session, admin_user.id)
    await _create_building(db_session, admin_user.id, address="Rue Test 2")
    await db_session.commit()

    result = await get_portfolio_risk_trend(db_session, months=12)
    assert result.total_buildings == 2
    assert result.buildings_stable == 2
    assert result.buildings_improving == 0
    assert result.buildings_deteriorating == 0


@pytest.mark.asyncio
async def test_snapshot_worst_and_best_building(db_session, admin_user):
    """Snapshot identifies worst and best buildings."""
    b1 = await _create_building(db_session, admin_user.id, address="Best")
    b2 = await _create_building(db_session, admin_user.id, address="Worst")
    await _create_risk_score(db_session, b1.id, "low", 0.1)
    await _create_risk_score(db_session, b2.id, "critical", 0.95)
    await db_session.commit()

    result = await get_portfolio_risk_snapshot(db_session)
    assert result.worst_building_id == b2.id
    assert result.best_building_id == b1.id


@pytest.mark.asyncio
async def test_snapshot_no_buildings(db_session, admin_user):
    """Snapshot with no buildings returns empty distribution."""
    result = await get_portfolio_risk_snapshot(db_session)
    assert result.distribution == []
    assert result.avg_score is None
    assert result.median_score is None
    assert result.worst_building_id is None
    assert result.best_building_id is None


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_risk_trend(client, db_session, admin_user, auth_headers):
    """GET /portfolio/risk-trend returns 200."""
    resp = await client.get("/api/v1/portfolio/risk-trend", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_buildings" in data
    assert "trend_direction" in data


@pytest.mark.asyncio
async def test_api_risk_snapshot(client, db_session, admin_user, auth_headers):
    """GET /portfolio/risk-snapshot returns 200."""
    resp = await client.get("/api/v1/portfolio/risk-snapshot", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "distribution" in data


@pytest.mark.asyncio
async def test_api_risk_hotspots(client, db_session, admin_user, auth_headers):
    """GET /portfolio/risk-hotspots returns 200."""
    resp = await client.get("/api/v1/portfolio/risk-hotspots", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_api_risk_report(client, db_session, admin_user, auth_headers):
    """GET /portfolio/risk-report returns 200."""
    resp = await client.get("/api/v1/portfolio/risk-report", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "portfolio_trend" in data
    assert "current_snapshot" in data
    assert "hotspots" in data


@pytest.mark.asyncio
async def test_api_building_trajectory(client, db_session, admin_user, auth_headers):
    """GET /buildings/{id}/risk-trajectory returns 200."""
    b = await _create_building(db_session, admin_user.id)
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{b.id}/risk-trajectory", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(b.id)
    assert data["trend_direction"] == "stable"


@pytest.mark.asyncio
async def test_api_risk_comparison(client, db_session, admin_user, auth_headers):
    """GET /portfolio/risk-comparison returns 200."""
    resp = await client.get(
        "/api/v1/portfolio/risk-comparison",
        params={
            "period1_start": "2024-01-01",
            "period1_end": "2024-06-30",
            "period2_start": "2024-07-01",
            "period2_end": "2024-12-31",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "period1" in data
    assert "period2" in data
    assert "score_delta" in data
