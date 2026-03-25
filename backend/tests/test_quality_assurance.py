"""Tests for the quality assurance service and API endpoints."""

import uuid
from datetime import date, timedelta

import pytest

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.models.zone import Zone
from app.services.quality_assurance_service import (
    get_portfolio_quality_report,
    get_quality_score,
    get_quality_trends,
    run_quality_checks,
)

# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
async def org(db_session):
    o = Organization(
        id=uuid.uuid4(),
        name="Test Org",
        type="diagnostic_lab",
    )
    db_session.add(o)
    await db_session.commit()
    await db_session.refresh(o)
    return o


@pytest.fixture
async def org_user(db_session, org):
    from tests.conftest import _HASH_ADMIN

    u = User(
        id=uuid.uuid4(),
        email="orguser@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Org",
        last_name="User",
        role="admin",
        is_active=True,
        language="fr",
        organization_id=org.id,
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest.fixture
async def rich_building(db_session, org_user):
    """A building with comprehensive data for QA checks."""
    b = Building(
        id=uuid.uuid4(),
        egid=12345,
        address="Rue Complète 10",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        renovation_year=2005,
        building_type="residential",
        latitude=46.52,
        longitude=6.63,
        surface_area_m2=500.0,
        created_by=org_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.commit()
    await db_session.refresh(b)
    return b


@pytest.fixture
async def minimal_building(db_session, admin_user):
    """A building with minimal data."""
    b = Building(
        id=uuid.uuid4(),
        address="Rue Vide 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.commit()
    await db_session.refresh(b)
    return b


@pytest.fixture
async def diagnostic_completed(db_session, rich_building):
    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=rich_building.id,
        diagnostic_type="asbestos",
        status="completed",
        date_inspection=date(2025, 1, 15),
        date_report=date(2025, 2, 1),
        conclusion="positive",
    )
    db_session.add(d)
    await db_session.commit()
    await db_session.refresh(d)
    return d


@pytest.fixture
async def diagnostic_bad_dates(db_session, rich_building):
    """Diagnostic with report date before inspection date."""
    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=rich_building.id,
        diagnostic_type="pcb",
        status="draft",
        date_inspection=date(2025, 3, 1),
        date_report=date(2025, 1, 1),  # before inspection
    )
    db_session.add(d)
    await db_session.commit()
    await db_session.refresh(d)
    return d


@pytest.fixture
async def sample_with_risk(db_session, diagnostic_completed):
    s = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic_completed.id,
        sample_number="S001",
        risk_level="high",
        pollutant_type="asbestos",
        concentration=1.5,
        unit="%",
    )
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)
    return s


@pytest.fixture
async def sample_no_risk(db_session, diagnostic_completed):
    s = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic_completed.id,
        sample_number="S002",
        pollutant_type="lead",
    )
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)
    return s


@pytest.fixture
async def zones(db_session, rich_building):
    zs = []
    for i, zt in enumerate(["floor", "room", "basement"]):
        z = Zone(
            id=uuid.uuid4(),
            building_id=rich_building.id,
            name=f"Zone {i}",
            zone_type=zt,
        )
        db_session.add(z)
        zs.append(z)
    await db_session.commit()
    return zs


@pytest.fixture
async def documents(db_session, rich_building, admin_user):
    docs = []
    for i in range(2):
        d = Document(
            id=uuid.uuid4(),
            building_id=rich_building.id,
            file_name=f"doc{i}.pdf",
            file_path=f"/docs/doc{i}.pdf",
            file_size_bytes=1024,
            mime_type="application/pdf",
            uploaded_by=admin_user.id,
        )
        db_session.add(d)
        docs.append(d)
    await db_session.commit()
    return docs


@pytest.fixture
async def action_item(db_session, rich_building):
    a = ActionItem(
        id=uuid.uuid4(),
        building_id=rich_building.id,
        title="Remove asbestos",
        description="Urgent removal needed",
        priority="high",
        status="pending",
        source_type="diagnostic",
        action_type="removal",
    )
    db_session.add(a)
    await db_session.commit()
    await db_session.refresh(a)
    return a


# ── Service tests: run_quality_checks ─────────────────────────────────────


@pytest.mark.asyncio
async def test_run_quality_checks_not_found(db_session):
    result = await run_quality_checks(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_run_quality_checks_minimal(db_session, minimal_building):
    result = await run_quality_checks(db_session, minimal_building.id)
    assert result is not None
    assert result["building_id"] == minimal_building.id
    assert result["total_checks"] >= 15
    assert result["passed"] + result["warnings"] + result["failures"] == result["total_checks"]


@pytest.mark.asyncio
async def test_run_quality_checks_rich(db_session, rich_building, diagnostic_completed, zones, documents):
    result = await run_quality_checks(db_session, rich_building.id)
    assert result["passed"] > 0
    # Rich building should pass structural checks
    structural = [c for c in result["checks"] if c["category"] == "structural"]
    assert all(c["status"] == "pass" for c in structural)


@pytest.mark.asyncio
async def test_run_quality_checks_bad_dates(db_session, rich_building, diagnostic_bad_dates):
    result = await run_quality_checks(db_session, rich_building.id)
    t3 = next(c for c in result["checks"] if c["check_id"] == "T3")
    assert t3["status"] == "fail"


@pytest.mark.asyncio
async def test_run_quality_checks_samples_no_risk(db_session, rich_building, diagnostic_completed, sample_no_risk):
    result = await run_quality_checks(db_session, rich_building.id)
    r1 = next(c for c in result["checks"] if c["check_id"] == "R1")
    assert r1["status"] == "warn"


@pytest.mark.asyncio
async def test_run_quality_checks_completed_no_conclusion(db_session, rich_building):
    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=rich_building.id,
        diagnostic_type="lead",
        status="completed",
        conclusion=None,
    )
    db_session.add(d)
    await db_session.commit()
    result = await run_quality_checks(db_session, rich_building.id)
    r4 = next(c for c in result["checks"] if c["check_id"] == "R4")
    assert r4["status"] == "fail"


@pytest.mark.asyncio
async def test_run_quality_checks_coverage_zones(db_session, rich_building, zones):
    result = await run_quality_checks(db_session, rich_building.id)
    c1 = next(c for c in result["checks"] if c["check_id"] == "C1")
    assert c1["status"] == "pass"
    assert "3" in c1["detail"]


@pytest.mark.asyncio
async def test_run_quality_checks_actions_for_high_risk(
    db_session, rich_building, diagnostic_completed, sample_with_risk, action_item
):
    result = await run_quality_checks(db_session, rich_building.id)
    r2 = next(c for c in result["checks"] if c["check_id"] == "R2")
    assert r2["status"] == "pass"


# ── Service tests: get_quality_score ──────────────────────────────────────


@pytest.mark.asyncio
async def test_quality_score_not_found(db_session):
    result = await get_quality_score(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_quality_score_minimal(db_session, minimal_building):
    result = await get_quality_score(db_session, minimal_building.id)
    assert result is not None
    assert 0 <= result["overall_score"] <= 100
    assert result["grade"] in ("A", "B", "C", "D", "E", "F")
    assert len(result["sub_scores"]) == 5


@pytest.mark.asyncio
async def test_quality_score_rich(db_session, rich_building, diagnostic_completed, zones, documents):
    result = await get_quality_score(db_session, rich_building.id)
    assert result["overall_score"] > 30  # Rich should have decent score
    # Check sub-score weights sum to 1.0
    total_weight = sum(s["weight"] for s in result["sub_scores"])
    assert abs(total_weight - 1.0) < 0.01


@pytest.mark.asyncio
async def test_quality_score_grade_boundaries(db_session, rich_building):
    # Verify the score computation works
    await get_quality_score(db_session, rich_building.id)
    from app.services.quality_assurance_service import _grade_from_score

    assert _grade_from_score(95) == "A"
    assert _grade_from_score(85) == "B"
    assert _grade_from_score(75) == "C"
    assert _grade_from_score(65) == "D"
    assert _grade_from_score(55) == "E"
    assert _grade_from_score(45) == "F"


@pytest.mark.asyncio
async def test_quality_score_freshness_recent(db_session, rich_building):
    """Recent diagnostic should give high freshness score."""
    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=rich_building.id,
        diagnostic_type="asbestos",
        status="completed",
        date_inspection=date.today() - timedelta(days=30),
        date_report=date.today(),
        conclusion="negative",
    )
    db_session.add(d)
    await db_session.commit()
    result = await get_quality_score(db_session, rich_building.id)
    freshness = next(s for s in result["sub_scores"] if s["name"] == "data_freshness")
    assert freshness["score"] == 100.0


@pytest.mark.asyncio
async def test_quality_score_freshness_old(db_session, rich_building):
    """Old diagnostic should give low freshness score."""
    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=rich_building.id,
        diagnostic_type="asbestos",
        status="draft",
        date_inspection=date.today() - timedelta(days=365 * 6),
    )
    db_session.add(d)
    await db_session.commit()
    result = await get_quality_score(db_session, rich_building.id)
    freshness = next(s for s in result["sub_scores"] if s["name"] == "data_freshness")
    assert freshness["score"] == 10.0


# ── Service tests: get_quality_trends ─────────────────────────────────────


@pytest.mark.asyncio
async def test_quality_trends_not_found(db_session):
    result = await get_quality_trends(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_quality_trends_minimal(db_session, minimal_building):
    result = await get_quality_trends(db_session, minimal_building.id)
    assert result is not None
    assert result["building_id"] == minimal_building.id
    assert result["trajectory"] in ("improving", "stable", "declining")


@pytest.mark.asyncio
async def test_quality_trends_with_data(db_session, rich_building, diagnostic_completed, documents):
    result = await get_quality_trends(db_session, rich_building.id)
    assert len(result["trend_points"]) > 0
    assert result["current_score"] > 0


@pytest.mark.asyncio
async def test_quality_trends_scores_increase(db_session, rich_building, diagnostic_completed, zones):
    result = await get_quality_trends(db_session, rich_building.id)
    scores = [p["score"] for p in result["trend_points"]]
    # Scores should be non-decreasing (cumulative)
    for i in range(1, len(scores)):
        assert scores[i] >= scores[i - 1]


# ── Service tests: get_portfolio_quality_report ───────────────────────────


@pytest.mark.asyncio
async def test_portfolio_report_no_users(db_session, org):
    # Remove all users from org — use a fresh org with no users
    empty_org = Organization(id=uuid.uuid4(), name="Empty Org", type="authority")
    db_session.add(empty_org)
    await db_session.commit()
    result = await get_portfolio_quality_report(db_session, empty_org.id)
    assert result["total_buildings"] == 0
    assert result["average_score"] == 0.0


@pytest.mark.asyncio
async def test_portfolio_report_with_buildings(db_session, org, org_user, rich_building):
    result = await get_portfolio_quality_report(db_session, org.id)
    assert result["organization_id"] == org.id
    assert result["total_buildings"] >= 1
    assert 0 <= result["average_score"] <= 100
    assert result["average_grade"] in ("A", "B", "C", "D", "E", "F")
    assert isinstance(result["score_distribution"], dict)


@pytest.mark.asyncio
async def test_portfolio_report_worst_buildings(db_session, org, org_user):
    # Create multiple buildings
    for i in range(3):
        b = Building(
            id=uuid.uuid4(),
            address=f"Rue Portfolio {i}",
            postal_code="1000",
            city="Lausanne",
            canton="VD",
            building_type="residential",
            created_by=org_user.id,
            status="active",
        )
        db_session.add(b)
    await db_session.commit()
    result = await get_portfolio_quality_report(db_session, org.id)
    assert len(result["worst_buildings"]) <= 5
    assert result["total_buildings"] >= 3


# ── API endpoint tests ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_api_qa_checks(client, auth_headers, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/quality-assurance/checks",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total_checks"] >= 15
    assert "checks" in data


@pytest.mark.asyncio
async def test_api_qa_checks_404(client, auth_headers):
    resp = await client.get(
        f"/api/v1/buildings/{uuid.uuid4()}/quality-assurance/checks",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_qa_score(client, auth_headers, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/quality-assurance/score",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "overall_score" in data
    assert "grade" in data
    assert "sub_scores" in data


@pytest.mark.asyncio
async def test_api_qa_score_404(client, auth_headers):
    resp = await client.get(
        f"/api/v1/buildings/{uuid.uuid4()}/quality-assurance/score",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_qa_trends(client, auth_headers, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/quality-assurance/trends",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "trajectory" in data
    assert "trend_points" in data


@pytest.mark.asyncio
async def test_api_qa_trends_404(client, auth_headers):
    resp = await client.get(
        f"/api/v1/buildings/{uuid.uuid4()}/quality-assurance/trends",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_portfolio_report(client, auth_headers, db_session, admin_user):
    o = Organization(id=uuid.uuid4(), name="API Org", type="property_management")
    db_session.add(o)
    await db_session.commit()
    resp = await client.get(
        f"/api/v1/organizations/{o.id}/quality-assurance/report",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_buildings" in data
    assert "score_distribution" in data


@pytest.mark.asyncio
async def test_api_qa_checks_unauthenticated(client, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/quality-assurance/checks",
    )
    assert resp.status_code == 401
