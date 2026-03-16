"""Tests for the Lab Result Analysis service and API."""

import uuid
from datetime import date

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.models.user import User
from app.services.lab_result_service import (
    analyze_lab_results,
    detect_result_anomalies,
    generate_lab_summary_report,
    get_result_trends,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def lab_user(db_session):
    user = User(
        id=uuid.uuid4(),
        email="lab@test.ch",
        password_hash="$2b$12$LJ3m4ys3Lg2HEOrtXmMK.uPBJFBuK0FqAqoCqAYNKN4WYDq0Q6K/a",
        first_name="Lab",
        last_name="Tester",
        role="admin",
        is_active=True,
        language="fr",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def lab_building(db_session, lab_user):
    building = Building(
        id=uuid.uuid4(),
        address="Rue du Labo 10",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        created_by=lab_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def lab_diagnostic(db_session, lab_building, lab_user):
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=lab_building.id,
        diagnostic_type="asbestos",
        status="completed",
        diagnostician_id=lab_user.id,
        date_inspection=date(2025, 6, 15),
    )
    db_session.add(diag)
    await db_session.commit()
    await db_session.refresh(diag)
    return diag


@pytest.fixture
async def lab_samples(db_session, lab_diagnostic):
    """Create diverse samples for testing."""
    samples_data = [
        {
            "sample_number": "S001",
            "pollutant_type": "asbestos",
            "concentration": 2.5,
            "unit": "percent_weight",
            "location_floor": "1",
            "location_room": "Room A",
            "threshold_exceeded": True,
            "risk_level": "high",
        },
        {
            "sample_number": "S002",
            "pollutant_type": "asbestos",
            "concentration": 0.3,
            "unit": "percent_weight",
            "location_floor": "1",
            "location_room": "Room B",
            "threshold_exceeded": False,
            "risk_level": "low",
        },
        {
            "sample_number": "S003",
            "pollutant_type": "pcb",
            "concentration": 120.0,
            "unit": "mg_per_kg",
            "location_floor": "2",
            "location_room": "Room C",
            "threshold_exceeded": True,
            "risk_level": "high",
        },
        {
            "sample_number": "S004",
            "pollutant_type": "pcb",
            "concentration": 30.0,
            "unit": "mg_per_kg",
            "location_floor": "2",
            "location_room": "Room D",
            "threshold_exceeded": False,
            "risk_level": "low",
        },
        {
            "sample_number": "S005",
            "pollutant_type": "lead",
            "concentration": 8000.0,
            "unit": "mg_per_kg",
            "location_floor": "3",
            "location_room": "Room E",
            "threshold_exceeded": True,
            "risk_level": "high",
        },
        {
            "sample_number": "S006",
            "pollutant_type": "radon",
            "concentration": 450.0,
            "unit": "bq_per_m3",
            "location_floor": "0",
            "location_room": "Basement",
            "threshold_exceeded": True,
            "risk_level": "medium",
        },
        {
            "sample_number": "S007",
            "pollutant_type": "asbestos",
            "concentration": None,
            "unit": "percent_weight",
            "location_floor": "1",
            "location_room": "Room F",
            "threshold_exceeded": False,
            "risk_level": None,
        },
    ]
    created = []
    for data in samples_data:
        s = Sample(
            id=uuid.uuid4(),
            diagnostic_id=lab_diagnostic.id,
            **data,
        )
        db_session.add(s)
        created.append(s)
    await db_session.commit()
    for s in created:
        await db_session.refresh(s)
    return created


# ---------------------------------------------------------------------------
# Service tests: analyze_lab_results
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_analyze_returns_all_samples(db_session, lab_building, lab_samples):
    result = await analyze_lab_results(db_session, lab_building.id)
    assert result.total_samples == 7
    assert result.samples_with_results == 6
    assert result.building_id == lab_building.id


@pytest.mark.asyncio
async def test_analyze_stats_per_pollutant(db_session, lab_building, lab_samples):
    result = await analyze_lab_results(db_session, lab_building.id)
    stats_map = {s.pollutant_type: s for s in result.stats_by_pollutant}

    assert "asbestos" in stats_map
    asbestos = stats_map["asbestos"]
    assert asbestos.count == 2  # S001 + S002 (S007 has no concentration)
    assert asbestos.min_concentration == 0.3
    assert asbestos.max_concentration == 2.5
    assert asbestos.fail_count == 1  # S001 >= 1.0
    assert asbestos.pass_count == 1  # S002 < 1.0


@pytest.mark.asyncio
async def test_analyze_threshold_comparison(db_session, lab_building, lab_samples):
    result = await analyze_lab_results(db_session, lab_building.id)
    s001 = next(r for r in result.sample_results if r.sample_number == "S001")
    assert s001.threshold_exceeded is True
    assert s001.ratio_to_threshold is not None
    assert s001.ratio_to_threshold > 1.0

    s002 = next(r for r in result.sample_results if r.sample_number == "S002")
    assert s002.threshold_exceeded is False


@pytest.mark.asyncio
async def test_analyze_empty_building(db_session, lab_building):
    result = await analyze_lab_results(db_session, lab_building.id)
    assert result.total_samples == 0
    assert result.samples_with_results == 0
    assert result.sample_results == []
    assert result.stats_by_pollutant == []


# ---------------------------------------------------------------------------
# Service tests: detect_result_anomalies
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_anomalies_conflicting_adjacent(db_session, lab_building, lab_samples):
    """S001 (exceeds on floor 1) and S002 (passes on floor 1) should conflict."""
    report = await detect_result_anomalies(db_session, lab_building.id)
    conflicting = [a for a in report.anomalies if a.anomaly_type == "conflicting_adjacent"]
    assert len(conflicting) >= 1
    # The passing sample should be flagged
    flagged_numbers = {a.sample_number for a in conflicting}
    assert "S002" in flagged_numbers


@pytest.mark.asyncio
async def test_anomalies_at_threshold(db_session, lab_building, lab_diagnostic):
    """A sample with concentration exactly at threshold should be flagged."""
    s = Sample(
        id=uuid.uuid4(),
        diagnostic_id=lab_diagnostic.id,
        sample_number="S_EXACT",
        pollutant_type="asbestos",
        concentration=1.0,  # exactly at 1.0% threshold
        unit="percent_weight",
        location_floor="5",
        threshold_exceeded=True,
        risk_level="medium",
    )
    db_session.add(s)
    await db_session.commit()

    report = await detect_result_anomalies(db_session, lab_building.id)
    at_thresh = [a for a in report.anomalies if a.anomaly_type == "at_threshold"]
    assert len(at_thresh) >= 1
    assert any(a.sample_number == "S_EXACT" for a in at_thresh)


@pytest.mark.asyncio
async def test_anomalies_extreme_outlier(db_session, lab_building, lab_diagnostic):
    """An extreme outlier should be detected."""
    base_samples = []
    for i in range(20):
        base_samples.append(
            Sample(
                id=uuid.uuid4(),
                diagnostic_id=lab_diagnostic.id,
                sample_number=f"NORM_{i}",
                pollutant_type="hap",
                concentration=100.0 + (i % 5),
                unit="mg_per_kg",
                location_floor=str(i),
            )
        )
    outlier = Sample(
        id=uuid.uuid4(),
        diagnostic_id=lab_diagnostic.id,
        sample_number="OUTLIER",
        pollutant_type="hap",
        concentration=500000.0,
        unit="mg_per_kg",
        location_floor="99",
    )
    for s in base_samples:
        db_session.add(s)
    db_session.add(outlier)
    await db_session.commit()

    report = await detect_result_anomalies(db_session, lab_building.id)
    outliers = [a for a in report.anomalies if a.anomaly_type == "extreme_outlier"]
    assert len(outliers) >= 1
    assert any(a.sample_number == "OUTLIER" for a in outliers)


@pytest.mark.asyncio
async def test_anomalies_age_inconsistent(db_session, lab_user):
    """Post-1991 building with positive asbestos should flag age inconsistency."""
    modern_building = Building(
        id=uuid.uuid4(),
        address="Rue Moderne 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=2005,
        building_type="residential",
        created_by=lab_user.id,
        status="active",
    )
    db_session.add(modern_building)
    await db_session.commit()

    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=modern_building.id,
        diagnostic_type="asbestos",
        status="completed",
        diagnostician_id=lab_user.id,
    )
    db_session.add(diag)
    await db_session.commit()

    s = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="AGE_TEST",
        pollutant_type="asbestos",
        concentration=3.0,
        unit="percent_weight",
        location_floor="1",
        threshold_exceeded=True,
        risk_level="high",
    )
    db_session.add(s)
    await db_session.commit()

    report = await detect_result_anomalies(db_session, modern_building.id)
    age_flags = [a for a in report.anomalies if a.anomaly_type == "age_inconsistent"]
    assert len(age_flags) >= 1


@pytest.mark.asyncio
async def test_anomalies_empty_building(db_session, lab_building):
    report = await detect_result_anomalies(db_session, lab_building.id)
    assert report.total == 0
    assert report.anomalies == []


@pytest.mark.asyncio
async def test_anomalies_by_type_counts(db_session, lab_building, lab_samples):
    report = await detect_result_anomalies(db_session, lab_building.id)
    total_from_dict = sum(report.by_type.values())
    assert total_from_dict == report.total


# ---------------------------------------------------------------------------
# Service tests: get_result_trends
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trends_groups_by_pollutant(db_session, lab_building, lab_samples):
    result = await get_result_trends(db_session, lab_building.id)
    pollutant_types = {t.pollutant_type for t in result.trends}
    assert "asbestos" in pollutant_types
    assert "pcb" in pollutant_types


@pytest.mark.asyncio
async def test_trends_radon_seasonal(db_session, lab_building, lab_samples):
    result = await get_result_trends(db_session, lab_building.id)
    radon_trend = next((t for t in result.trends if t.pollutant_type == "radon"), None)
    assert radon_trend is not None
    assert radon_trend.is_seasonal is True


@pytest.mark.asyncio
async def test_trends_direction_stable(db_session, lab_building, lab_samples):
    """With limited data, trend should be stable."""
    result = await get_result_trends(db_session, lab_building.id)
    for t in result.trends:
        # Single data point → stable
        if len(t.data_points) == 1:
            assert t.trend_direction == "stable"


@pytest.mark.asyncio
async def test_trends_empty_building(db_session, lab_building):
    result = await get_result_trends(db_session, lab_building.id)
    assert result.trends == []


@pytest.mark.asyncio
async def test_trends_increasing(db_session, lab_building, lab_user):
    """Samples with increasing concentrations should yield increasing trend."""
    diag1 = Diagnostic(
        id=uuid.uuid4(),
        building_id=lab_building.id,
        diagnostic_type="radon",
        status="completed",
        diagnostician_id=lab_user.id,
        date_inspection=date(2024, 1, 15),
    )
    diag2 = Diagnostic(
        id=uuid.uuid4(),
        building_id=lab_building.id,
        diagnostic_type="radon",
        status="completed",
        diagnostician_id=lab_user.id,
        date_inspection=date(2025, 6, 15),
    )
    db_session.add_all([diag1, diag2])
    await db_session.commit()

    s1 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag1.id,
        sample_number="RAD_1",
        pollutant_type="radon",
        concentration=200.0,
        unit="bq_per_m3",
    )
    s2 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag2.id,
        sample_number="RAD_2",
        pollutant_type="radon",
        concentration=500.0,
        unit="bq_per_m3",
    )
    db_session.add_all([s1, s2])
    await db_session.commit()

    result = await get_result_trends(db_session, lab_building.id)
    radon_trend = next((t for t in result.trends if t.pollutant_type == "radon"), None)
    assert radon_trend is not None
    assert radon_trend.trend_direction == "increasing"


# ---------------------------------------------------------------------------
# Service tests: generate_lab_summary_report
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_summary_report_totals(db_session, lab_building, lab_samples):
    report = await generate_lab_summary_report(db_session, lab_building.id)
    assert report.total_samples == 7
    assert report.samples_with_results == 6
    assert report.samples_without_results == 1


@pytest.mark.asyncio
async def test_summary_report_compliance(db_session, lab_building, lab_samples):
    report = await generate_lab_summary_report(db_session, lab_building.id)
    assert report.overall_compliance is False  # We have non-compliant samples
    assert len(report.pollutant_summaries) >= 3


@pytest.mark.asyncio
async def test_summary_report_recommendations(db_session, lab_building, lab_samples):
    report = await generate_lab_summary_report(db_session, lab_building.id)
    assert len(report.recommendations) >= 1
    # Should mention samples without results
    assert any("no lab results" in r for r in report.recommendations)


@pytest.mark.asyncio
async def test_summary_empty_building(db_session, lab_building):
    report = await generate_lab_summary_report(db_session, lab_building.id)
    assert report.total_samples == 0
    assert report.overall_compliance is True
    assert any("No samples" in r for r in report.recommendations)


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_analysis_endpoint(client, auth_headers, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/lab-results/analysis",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert "sample_results" in data
    assert "stats_by_pollutant" in data


@pytest.mark.asyncio
async def test_api_anomalies_endpoint(client, auth_headers, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/lab-results/anomalies",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert "anomalies" in data


@pytest.mark.asyncio
async def test_api_trends_endpoint(client, auth_headers, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/lab-results/trends",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert "trends" in data


@pytest.mark.asyncio
async def test_api_summary_endpoint(client, auth_headers, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/lab-results/summary",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert "recommendations" in data


@pytest.mark.asyncio
async def test_api_404_for_unknown_building(client, auth_headers):
    fake_id = uuid.uuid4()
    resp = await client.get(
        f"/api/v1/buildings/{fake_id}/lab-results/analysis",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_401_without_auth(client, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/lab-results/analysis",
    )
    assert resp.status_code == 403
