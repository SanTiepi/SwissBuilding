"""Tests for reporting metrics: KPI dashboard, operational metrics, periodic reports, benchmarks."""

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.services.reporting_metrics_service import (
    generate_periodic_report,
    get_benchmark_comparison,
    get_kpi_dashboard,
    get_operational_metrics,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
async def org_building(db_session, org_user):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Report 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=org_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.commit()
    await db_session.refresh(b)
    return b


@pytest.fixture
async def org_diagnostic(db_session, org_building):
    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=org_building.id,
        diagnostic_type="asbestos",
        status="completed",
        date_report=date.today() - timedelta(days=5),
        created_at=datetime.now(UTC) - timedelta(days=20),
    )
    db_session.add(d)
    await db_session.commit()
    await db_session.refresh(d)
    return d


@pytest.fixture
async def org_sample(db_session, org_diagnostic):
    s = Sample(
        id=uuid.uuid4(),
        diagnostic_id=org_diagnostic.id,
        sample_number="S-001",
        pollutant_type="asbestos",
        threshold_exceeded=True,
        risk_level="high",
        created_at=datetime.now(UTC) - timedelta(days=10),
    )
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)
    return s


@pytest.fixture
async def org_intervention(db_session, org_building):
    iv = Intervention(
        id=uuid.uuid4(),
        building_id=org_building.id,
        intervention_type="remediation",
        title="Asbestos removal",
        status="completed",
        cost_chf=15000.0,
        date_start=date.today() - timedelta(days=30),
        date_end=date.today() - timedelta(days=10),
        created_at=datetime.now(UTC) - timedelta(days=30),
    )
    db_session.add(iv)
    await db_session.commit()
    await db_session.refresh(iv)
    return iv


@pytest.fixture
async def org_action(db_session, org_building):
    a = ActionItem(
        id=uuid.uuid4(),
        building_id=org_building.id,
        source_type="diagnostic",
        action_type="remediation",
        title="Remove asbestos",
        priority="high",
        status="completed",
        completed_at=datetime.now(UTC) - timedelta(days=5),
        created_at=datetime.now(UTC) - timedelta(days=15),
    )
    db_session.add(a)
    await db_session.commit()
    await db_session.refresh(a)
    return a


@pytest.fixture
async def org_document(db_session, org_building, org_user):
    doc = Document(
        id=uuid.uuid4(),
        building_id=org_building.id,
        file_path="/docs/report.pdf",
        file_name="report.pdf",
        document_type="diagnostic_report",
        uploaded_by=org_user.id,
        created_at=datetime.now(UTC) - timedelta(days=10),
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc


@pytest.fixture
async def org_risk_score(db_session, org_building):
    rs = BuildingRiskScore(
        id=uuid.uuid4(),
        building_id=org_building.id,
        asbestos_probability=0.8,
        pcb_probability=0.2,
        lead_probability=0.1,
        hap_probability=0.05,
        radon_probability=0.3,
        overall_risk_level="high",
        confidence=0.85,
    )
    db_session.add(rs)
    await db_session.commit()
    await db_session.refresh(rs)
    return rs


# ---------------------------------------------------------------------------
# FN1 — KPI Dashboard (service-level)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kpi_dashboard_empty_org(db_session, org):
    """KPI dashboard for org with no members returns zero trends."""
    result = await get_kpi_dashboard(db_session, org.id)
    assert result.organization_id == org.id
    assert result.buildings_assessed_pct.current == 0.0
    assert result.total_spent_chf == 0.0


@pytest.mark.asyncio
async def test_kpi_dashboard_with_data(
    db_session,
    org,
    org_user,
    org_building,
    org_diagnostic,
    org_sample,
    org_intervention,
    org_action,
    org_risk_score,
):
    """KPI dashboard with data returns meaningful values."""
    result = await get_kpi_dashboard(db_session, org.id)
    assert result.organization_id == org.id
    assert result.buildings_assessed_pct.current == 100.0
    assert result.total_spent_chf == 15000.0
    assert result.active_interventions_count.current == 0.0
    assert result.remediation_progress_pct.current == 100.0


@pytest.mark.asyncio
async def test_kpi_dashboard_not_found(db_session):
    """KPI dashboard raises ValueError for unknown org."""
    with pytest.raises(ValueError, match="not found"):
        await get_kpi_dashboard(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_kpi_compliance_rate(
    db_session,
    org,
    org_user,
    org_building,
    org_diagnostic,
    org_sample,
):
    """Compliance rate should be 0% when all assessed buildings have threshold exceeded."""
    result = await get_kpi_dashboard(db_session, org.id)
    assert result.compliance_rate_pct.current == 0.0


# ---------------------------------------------------------------------------
# FN2 — Operational Metrics (service-level)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_operational_metrics_empty(db_session, org):
    """Operational metrics for empty org return zeros."""
    result = await get_operational_metrics(db_session, org.id)
    assert result.organization_id == org.id
    assert result.avg_diagnostic_completion_days == 0.0
    assert result.total_diagnostics == 0


@pytest.mark.asyncio
async def test_operational_metrics_with_data(
    db_session,
    org,
    org_user,
    org_building,
    org_diagnostic,
    org_sample,
    org_intervention,
    org_action,
    org_document,
):
    """Operational metrics with data compute correct values."""
    result = await get_operational_metrics(db_session, org.id)
    assert result.organization_id == org.id
    assert result.total_diagnostics == 1
    assert result.total_samples == 1
    assert result.total_documents == 1
    assert result.total_actions == 1
    assert result.action_completion_rate_pct == 100.0
    assert result.avg_diagnostic_completion_days >= 0


@pytest.mark.asyncio
async def test_operational_metrics_not_found(db_session):
    """Operational metrics raises ValueError for unknown org."""
    with pytest.raises(ValueError, match="not found"):
        await get_operational_metrics(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_operational_sample_throughput(
    db_session,
    org,
    org_user,
    org_building,
    org_diagnostic,
    org_sample,
):
    """Sample throughput per month is computed."""
    result = await get_operational_metrics(db_session, org.id)
    assert result.sample_throughput_per_month > 0


# ---------------------------------------------------------------------------
# FN3 — Periodic Report (service-level)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_periodic_report_monthly(
    db_session,
    org,
    org_user,
    org_building,
    org_diagnostic,
    org_sample,
    org_intervention,
    org_action,
):
    """Monthly report includes correct counts."""
    result = await generate_periodic_report(db_session, org.id, "monthly")
    assert result.organization_id == org.id
    assert result.period == "monthly"
    assert result.buildings_count == 1
    assert result.new_diagnostics >= 0
    assert result.period_start < result.period_end


@pytest.mark.asyncio
async def test_periodic_report_quarterly(
    db_session,
    org,
    org_user,
    org_building,
    org_diagnostic,
):
    """Quarterly report uses 90-day window."""
    result = await generate_periodic_report(db_session, org.id, "quarterly")
    assert result.period == "quarterly"
    delta = (result.period_end - result.period_start).days
    assert 89 <= delta <= 91


@pytest.mark.asyncio
async def test_periodic_report_annual(
    db_session,
    org,
    org_user,
    org_building,
    org_diagnostic,
):
    """Annual report uses 365-day window."""
    result = await generate_periodic_report(db_session, org.id, "annual")
    assert result.period == "annual"
    delta = (result.period_end - result.period_start).days
    assert 364 <= delta <= 366


@pytest.mark.asyncio
async def test_periodic_report_empty_org(db_session, org):
    """Periodic report for empty org returns meaningful summary."""
    result = await generate_periodic_report(db_session, org.id, "monthly")
    assert "No buildings" in result.summary
    assert result.buildings_count == 0


@pytest.mark.asyncio
async def test_periodic_report_key_changes(
    db_session,
    org,
    org_user,
    org_building,
    org_diagnostic,
    org_sample,
    org_intervention,
    org_action,
):
    """Key changes list is populated when events occur."""
    result = await generate_periodic_report(db_session, org.id, "annual")
    assert isinstance(result.key_changes, list)


@pytest.mark.asyncio
async def test_periodic_report_not_found(db_session):
    """Periodic report raises ValueError for unknown org."""
    with pytest.raises(ValueError, match="not found"):
        await generate_periodic_report(db_session, uuid.uuid4())


# ---------------------------------------------------------------------------
# FN4 — Benchmark Comparison (service-level)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_benchmark_empty_org(db_session, org):
    """Benchmark for org with no data returns zero values."""
    result = await get_benchmark_comparison(db_session, org.id)
    assert result.organization_id == org.id
    assert result.compliance_rate.org_value == 0.0


@pytest.mark.asyncio
async def test_benchmark_with_data(
    db_session,
    org,
    org_user,
    org_building,
    org_diagnostic,
    org_sample,
    org_action,
    org_risk_score,
):
    """Benchmark with data returns computed metrics and percentiles."""
    result = await get_benchmark_comparison(db_session, org.id)
    assert result.organization_id == org.id
    assert result.avg_risk_score.org_value > 0
    assert 0.0 <= result.overall_percentile <= 100.0


@pytest.mark.asyncio
async def test_benchmark_not_found(db_session):
    """Benchmark raises ValueError for unknown org."""
    with pytest.raises(ValueError, match="not found"):
        await get_benchmark_comparison(db_session, uuid.uuid4())


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_kpi_dashboard(client, auth_headers, db_session, org, org_user, org_building):
    """GET /organizations/{org_id}/kpi-dashboard returns 200."""
    response = await client.get(f"/api/v1/organizations/{org.id}/kpi-dashboard", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["organization_id"] == str(org.id)
    assert "buildings_assessed_pct" in data


@pytest.mark.asyncio
async def test_api_kpi_dashboard_not_found(client, auth_headers):
    """GET /organizations/{org_id}/kpi-dashboard returns 404 for unknown org."""
    response = await client.get(f"/api/v1/organizations/{uuid.uuid4()}/kpi-dashboard", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_api_operational_metrics(client, auth_headers, db_session, org, org_user, org_building):
    """GET /organizations/{org_id}/operational-metrics returns 200."""
    response = await client.get(f"/api/v1/organizations/{org.id}/operational-metrics", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["organization_id"] == str(org.id)


@pytest.mark.asyncio
async def test_api_periodic_report(client, auth_headers, db_session, org, org_user, org_building):
    """GET /organizations/{org_id}/periodic-report returns 200."""
    response = await client.get(
        f"/api/v1/organizations/{org.id}/periodic-report?period=quarterly", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "quarterly"


@pytest.mark.asyncio
async def test_api_periodic_report_invalid_period(client, auth_headers, db_session, org, org_user, org_building):
    """GET /organizations/{org_id}/periodic-report with invalid period returns 422."""
    response = await client.get(f"/api/v1/organizations/{org.id}/periodic-report?period=weekly", headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_api_benchmark(client, auth_headers, db_session, org, org_user, org_building):
    """GET /organizations/{org_id}/benchmark returns 200."""
    response = await client.get(f"/api/v1/organizations/{org.id}/benchmark", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["organization_id"] == str(org.id)
    assert "compliance_rate" in data


@pytest.mark.asyncio
async def test_api_unauthenticated(client, db_session, org):
    """Unauthenticated requests return 403."""
    response = await client.get(f"/api/v1/organizations/{org.id}/kpi-dashboard")
    assert response.status_code == 403
