"""Tests for diagnostic quality service and API."""

import uuid
from datetime import date

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.models.zone import Zone
from app.services.diagnostic_quality_service import (
    ALL_POLLUTANTS,
    detect_diagnostic_deficiencies,
    evaluate_diagnostic_quality,
    get_diagnostic_benchmarks,
)

# Re-use conftest hashes
from tests.conftest import _HASH_DIAG


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_building(user_id: uuid.UUID) -> Building:
    return Building(
        id=uuid.uuid4(),
        address="Rue Diagnostic 10",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=user_id,
        status="active",
    )


def _make_diagnostic(
    building_id: uuid.UUID,
    diagnostician_id: uuid.UUID | None = None,
    *,
    methodology: str | None = None,
    summary: str | None = None,
    conclusion: str | None = None,
    laboratory: str | None = None,
    laboratory_report_number: str | None = None,
    report_file_path: str | None = None,
    status: str = "draft",
    date_inspection: date | None = None,
    date_report: date | None = None,
    diagnostic_context: str = "AvT",
) -> Diagnostic:
    return Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type="asbestos",
        diagnostic_context=diagnostic_context,
        status=status,
        diagnostician_id=diagnostician_id,
        methodology=methodology,
        summary=summary,
        conclusion=conclusion,
        laboratory=laboratory,
        laboratory_report_number=laboratory_report_number,
        report_file_path=report_file_path,
        date_inspection=date_inspection,
        date_report=date_report,
    )


def _make_sample(diagnostic_id: uuid.UUID, pollutant_type: str, location_floor: str = "1") -> Sample:
    return Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic_id,
        sample_number=f"S-{uuid.uuid4().hex[:6]}",
        pollutant_type=pollutant_type,
        location_floor=location_floor,
    )


def _make_zone(building_id: uuid.UUID, name: str, user_id: uuid.UUID) -> Zone:
    return Zone(
        id=uuid.uuid4(),
        building_id=building_id,
        zone_type="room",
        name=name,
        created_by=user_id,
    )


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_evaluate_quality_not_found(db_session):
    """Returns None for nonexistent diagnostic."""
    result = await evaluate_diagnostic_quality(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_evaluate_quality_empty_diagnostic(db_session, admin_user):
    """Minimal diagnostic with no samples, zones, or metadata yields low score."""
    building = _make_building(admin_user.id)
    db_session.add(building)
    diag = _make_diagnostic(building.id)
    db_session.add(diag)
    await db_session.commit()

    result = await evaluate_diagnostic_quality(db_session, diag.id)
    assert result is not None
    # diagnostic_context="AvT" default gives 25pts methodology * 0.15 weight = 3.75
    assert result["overall_score"] <= 5.0
    assert result["grade"] == "F"
    assert result["total_samples"] == 0
    assert len(result["pollutants_missing"]) == 5


@pytest.mark.asyncio
async def test_evaluate_quality_full_diagnostic(db_session, admin_user):
    """Fully populated diagnostic should score high."""
    building = _make_building(admin_user.id)
    db_session.add(building)
    zone1 = _make_zone(building.id, "1", admin_user.id)
    db_session.add(zone1)
    diag = _make_diagnostic(
        building.id,
        diagnostician_id=admin_user.id,
        methodology="SIA 2028",
        summary="Full summary",
        conclusion="positive",
        laboratory="LabSuisse SA",
        laboratory_report_number="LAB-2024-001",
        report_file_path="/reports/report.pdf",
        date_inspection=date(2024, 1, 10),
    )
    db_session.add(diag)
    # Add samples for all 5 pollutants (2 samples for 1 zone = density target)
    for p in ALL_POLLUTANTS:
        db_session.add(_make_sample(diag.id, p, "1"))
    # Extra sample for density
    db_session.add(_make_sample(diag.id, "asbestos", "1"))

    # Add a document
    doc = Document(
        id=uuid.uuid4(),
        building_id=building.id,
        file_path="/docs/test.pdf",
        file_name="test.pdf",
    )
    db_session.add(doc)
    await db_session.commit()

    result = await evaluate_diagnostic_quality(db_session, diag.id)
    assert result is not None
    assert result["overall_score"] >= 75.0
    assert result["grade"] in ("A", "B")
    assert result["pollutant_coverage_score"] == 100.0
    assert len(result["pollutants_missing"]) == 0
    assert result["total_samples"] == 6


@pytest.mark.asyncio
async def test_evaluate_quality_partial_pollutants(db_session, admin_user):
    """Only 2 pollutants tested yields 40% coverage."""
    building = _make_building(admin_user.id)
    db_session.add(building)
    diag = _make_diagnostic(building.id)
    db_session.add(diag)
    db_session.add(_make_sample(diag.id, "asbestos"))
    db_session.add(_make_sample(diag.id, "lead"))
    await db_session.commit()

    result = await evaluate_diagnostic_quality(db_session, diag.id)
    assert result["pollutant_coverage_score"] == 40.0
    assert set(result["pollutants_tested"]) == {"asbestos", "lead"}
    assert "pcb" in result["pollutants_missing"]


@pytest.mark.asyncio
async def test_evaluate_quality_methodology_score(db_session, admin_user):
    """Methodology score from methodology + date_inspection + context."""
    building = _make_building(admin_user.id)
    db_session.add(building)
    diag = _make_diagnostic(
        building.id,
        methodology="FACH",
        date_inspection=date(2024, 3, 1),
        diagnostic_context="AvT",
    )
    db_session.add(diag)
    await db_session.commit()

    result = await evaluate_diagnostic_quality(db_session, diag.id)
    assert result["methodology_score"] == 100.0


@pytest.mark.asyncio
async def test_evaluate_quality_lab_score(db_session, admin_user):
    """Lab accreditation from laboratory + report number."""
    building = _make_building(admin_user.id)
    db_session.add(building)
    diag = _make_diagnostic(building.id, laboratory="Lab AG", laboratory_report_number="R-123")
    db_session.add(diag)
    await db_session.commit()

    result = await evaluate_diagnostic_quality(db_session, diag.id)
    assert result["lab_accreditation_score"] == 100.0


# ---------------------------------------------------------------------------
# Deficiency tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_deficiencies_not_found(db_session):
    """Returns None for nonexistent diagnostic."""
    result = await detect_diagnostic_deficiencies(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_deficiencies_no_samples(db_session, admin_user):
    """Diagnostic with no samples has critical deficiency."""
    building = _make_building(admin_user.id)
    db_session.add(building)
    diag = _make_diagnostic(building.id)
    db_session.add(diag)
    await db_session.commit()

    result = await detect_diagnostic_deficiencies(db_session, diag.id)
    assert result is not None
    assert result["critical_count"] >= 1
    types = [d["deficiency_type"] for d in result["deficiencies"]]
    assert "insufficient_sampling" in types
    assert "missing_pollutant" in types


@pytest.mark.asyncio
async def test_deficiencies_missing_report_fields(db_session, admin_user):
    """Missing summary, conclusion, lab, report file -> incomplete_report."""
    building = _make_building(admin_user.id)
    db_session.add(building)
    diag = _make_diagnostic(building.id)
    db_session.add(diag)
    db_session.add(_make_sample(diag.id, "asbestos"))
    await db_session.commit()

    result = await detect_diagnostic_deficiencies(db_session, diag.id)
    report_defs = [d for d in result["deficiencies"] if d["deficiency_type"] == "incomplete_report"]
    assert len(report_defs) >= 3  # summary, conclusion, lab, report_file


@pytest.mark.asyncio
async def test_deficiencies_zone_without_samples(db_session, admin_user):
    """Zone with no matching samples flagged as insufficient_sampling."""
    building = _make_building(admin_user.id)
    db_session.add(building)
    zone = _make_zone(building.id, "Basement", admin_user.id)
    db_session.add(zone)
    diag = _make_diagnostic(building.id)
    db_session.add(diag)
    db_session.add(_make_sample(diag.id, "asbestos", "Floor1"))
    await db_session.commit()

    result = await detect_diagnostic_deficiencies(db_session, diag.id)
    zone_defs = [
        d
        for d in result["deficiencies"]
        if d["deficiency_type"] == "insufficient_sampling" and d["zone_id"] is not None
    ]
    assert len(zone_defs) >= 1
    assert zone_defs[0]["zone_id"] == zone.id


@pytest.mark.asyncio
async def test_deficiencies_no_methodology(db_session, admin_user):
    """Missing methodology flagged."""
    building = _make_building(admin_user.id)
    db_session.add(building)
    diag = _make_diagnostic(building.id)
    db_session.add(diag)
    await db_session.commit()

    result = await detect_diagnostic_deficiencies(db_session, diag.id)
    meth_defs = [d for d in result["deficiencies"] if d["deficiency_type"] == "outdated_methodology"]
    assert len(meth_defs) == 1


@pytest.mark.asyncio
async def test_deficiencies_complete_diagnostic(db_session, admin_user):
    """Well-populated diagnostic has fewer deficiencies."""
    building = _make_building(admin_user.id)
    db_session.add(building)
    diag = _make_diagnostic(
        building.id,
        methodology="SIA",
        summary="Summary",
        conclusion="positive",
        laboratory="Lab",
        report_file_path="/r.pdf",
    )
    db_session.add(diag)
    for p in ALL_POLLUTANTS:
        db_session.add(_make_sample(diag.id, p))
    await db_session.commit()

    result = await detect_diagnostic_deficiencies(db_session, diag.id)
    # Should have no incomplete_report, no missing_pollutant, no outdated_methodology, no no-samples
    types = {d["deficiency_type"] for d in result["deficiencies"]}
    assert "missing_pollutant" not in types
    assert "outdated_methodology" not in types
    assert "incomplete_report" not in types


# ---------------------------------------------------------------------------
# Benchmark tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_benchmarks_empty(db_session):
    """No diagnostics returns zero benchmarks."""
    result = await get_diagnostic_benchmarks(db_session)
    assert result["total_diagnostics"] == 0
    assert result["avg_quality_score"] == 0.0
    assert result["best_practice_threshold"] == 75.0


@pytest.mark.asyncio
async def test_benchmarks_with_diagnostics(db_session, admin_user):
    """Benchmarks computed over multiple diagnostics."""
    building = _make_building(admin_user.id)
    db_session.add(building)
    d1 = _make_diagnostic(building.id, methodology="SIA", summary="S", conclusion="C")
    d2 = _make_diagnostic(building.id)
    db_session.add_all([d1, d2])
    db_session.add(_make_sample(d1.id, "asbestos"))
    db_session.add(_make_sample(d1.id, "lead"))
    await db_session.commit()

    result = await get_diagnostic_benchmarks(db_session)
    assert result["total_diagnostics"] == 2
    assert result["avg_quality_score"] > 0.0
    assert isinstance(result["grade_distribution"], dict)
    assert isinstance(result["pollutant_coverage_rate"], dict)
    assert "asbestos" in result["pollutant_coverage_rate"]


@pytest.mark.asyncio
async def test_benchmarks_grade_distribution(db_session, admin_user):
    """Grade distribution sums to total diagnostics."""
    building = _make_building(admin_user.id)
    db_session.add(building)
    for _ in range(3):
        d = _make_diagnostic(building.id)
        db_session.add(d)
    await db_session.commit()

    result = await get_diagnostic_benchmarks(db_session)
    total_grades = sum(result["grade_distribution"].values())
    assert total_grades == result["total_diagnostics"]


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_api_quality_not_found(client, auth_headers):
    """404 for nonexistent diagnostic."""
    resp = await client.get(f"/api/v1/diagnostics/{uuid.uuid4()}/quality", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_quality_ok(client, db_session, admin_user, auth_headers):
    """200 with quality score."""
    building = _make_building(admin_user.id)
    db_session.add(building)
    diag = _make_diagnostic(building.id)
    db_session.add(diag)
    await db_session.commit()

    resp = await client.get(f"/api/v1/diagnostics/{diag.id}/quality", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "overall_score" in data
    assert "grade" in data


@pytest.mark.asyncio
async def test_api_deficiencies_not_found(client, auth_headers):
    """404 for nonexistent diagnostic."""
    resp = await client.get(f"/api/v1/diagnostics/{uuid.uuid4()}/deficiencies", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_deficiencies_ok(client, db_session, admin_user, auth_headers):
    """200 with deficiencies."""
    building = _make_building(admin_user.id)
    db_session.add(building)
    diag = _make_diagnostic(building.id)
    db_session.add(diag)
    await db_session.commit()

    resp = await client.get(f"/api/v1/diagnostics/{diag.id}/deficiencies", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "deficiencies" in data
    assert data["total_deficiencies"] > 0


@pytest.mark.asyncio
async def test_api_diagnostician_performance_empty(client, db_session, admin_user, auth_headers):
    """Empty org returns 0 diagnosticians."""
    org = Organization(id=uuid.uuid4(), name="TestOrg", type="diagnostic_lab")
    db_session.add(org)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/organizations/{org.id}/diagnostician-performance",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_diagnosticians"] == 0


@pytest.mark.asyncio
async def test_api_diagnostician_performance_with_data(client, db_session, admin_user, auth_headers):
    """Diagnostician with diagnostics returns performance data."""
    org = Organization(id=uuid.uuid4(), name="DiagLab", type="diagnostic_lab")
    db_session.add(org)
    diag_user = User(
        id=uuid.uuid4(),
        email="perf@test.ch",
        password_hash=_HASH_DIAG,
        first_name="Pierre",
        last_name="Test",
        role="diagnostician",
        is_active=True,
        language="fr",
        organization_id=org.id,
    )
    db_session.add(diag_user)
    building = _make_building(admin_user.id)
    db_session.add(building)
    diag = _make_diagnostic(
        building.id,
        diagnostician_id=diag_user.id,
        status="completed",
        date_inspection=date(2024, 1, 1),
        date_report=date(2024, 1, 15),
    )
    db_session.add(diag)
    db_session.add(_make_sample(diag.id, "asbestos"))
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/organizations/{org.id}/diagnostician-performance",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_diagnosticians"] == 1
    perf = data["diagnosticians"][0]
    assert perf["diagnostician_name"] == "Pierre Test"
    assert perf["diagnostic_count"] == 1
    assert perf["completeness_rate"] == 100.0
    assert perf["avg_days_to_completion"] == 14.0
    assert perf["rank"] == 1


@pytest.mark.asyncio
async def test_api_benchmarks(client, auth_headers):
    """200 with benchmark data (empty db)."""
    resp = await client.get("/api/v1/diagnostic-benchmarks", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_diagnostics" in data
    assert "best_practice_threshold" in data


@pytest.mark.asyncio
async def test_api_quality_unauthenticated(client):
    """401 without auth."""
    resp = await client.get(f"/api/v1/diagnostics/{uuid.uuid4()}/quality")
    assert resp.status_code == 401
