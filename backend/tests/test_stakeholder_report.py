"""Tests for stakeholder report service and API endpoints."""

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.compliance_artefact import ComplianceArtefact
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.services.stakeholder_report_service import (
    generate_authority_report,
    generate_contractor_briefing,
    generate_owner_report,
    generate_portfolio_executive_summary,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def org(db_session: AsyncSession) -> Organization:
    o = Organization(
        id=uuid.uuid4(),
        name="Test Regie SA",
        type="property_management",
    )
    db_session.add(o)
    await db_session.commit()
    await db_session.refresh(o)
    return o


@pytest.fixture
async def org_user(db_session: AsyncSession, org: Organization) -> User:
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
async def rich_building(db_session: AsyncSession, org_user: User) -> Building:
    """Building with diagnostics, samples, risk scores, actions, artefacts."""
    b = Building(
        id=uuid.uuid4(),
        address="Rue de la Gare 10",
        postal_code="1003",
        city="Lausanne",
        canton="VD",
        construction_year=1960,
        building_type="residential",
        created_by=org_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.flush()

    # Risk score
    rs = BuildingRiskScore(
        id=uuid.uuid4(),
        building_id=b.id,
        asbestos_probability=0.85,
        pcb_probability=0.3,
        lead_probability=0.1,
        hap_probability=0.0,
        radon_probability=0.55,
        overall_risk_level="critical",
    )
    db_session.add(rs)

    # Diagnostic
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=b.id,
        diagnostic_type="asbestos",
        status="completed",
        date_report=date(2025, 6, 15),
    )
    db_session.add(diag)
    await db_session.flush()

    # Samples
    s1 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S001",
        pollutant_type="asbestos",
        concentration=5.2,
        unit="percent_weight",
        threshold_exceeded=True,
        risk_level="critical",
        cfst_work_category="major",
        waste_disposal_type="special",
        location_floor="2nd",
        location_room="Corridor",
        location_detail="Ceiling tiles",
        material_description="Flocage plafond",
    )
    s2 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S002",
        pollutant_type="asbestos",
        concentration=0.1,
        unit="percent_weight",
        threshold_exceeded=False,
        risk_level="low",
    )
    s3 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S003",
        pollutant_type="pcb",
        concentration=120.0,
        unit="mg/kg",
        threshold_exceeded=True,
        risk_level="high",
        cfst_work_category="medium",
        waste_disposal_type="type_e",
        location_floor="Basement",
        location_room="Technical room",
        material_description="Joint de fenetre",
    )
    db_session.add_all([s1, s2, s3])

    # Actions
    a1 = ActionItem(
        id=uuid.uuid4(),
        building_id=b.id,
        diagnostic_id=diag.id,
        source_type="diagnostic",
        action_type="remediation",
        title="Remove asbestos ceiling tiles in corridor",
        description="Professional removal with full containment.",
        priority="critical",
        status="open",
        due_date=date(2026, 1, 15),
    )
    a2 = ActionItem(
        id=uuid.uuid4(),
        building_id=b.id,
        diagnostic_id=diag.id,
        source_type="diagnostic",
        action_type="testing",
        title="Additional PCB sampling in basement",
        priority="high",
        status="open",
    )
    db_session.add_all([a1, a2])

    # Compliance artefact
    ca = ComplianceArtefact(
        id=uuid.uuid4(),
        building_id=b.id,
        artefact_type="waste_elimination_plan",
        status="submitted",
        title="Plan d'elimination des dechets (PED)",
    )
    db_session.add(ca)

    # Intervention in progress
    interv = Intervention(
        id=uuid.uuid4(),
        building_id=b.id,
        intervention_type="remediation",
        title="Asbestos removal phase 1",
        status="in_progress",
        cost_chf=25000.0,
    )
    db_session.add(interv)

    await db_session.commit()
    await db_session.refresh(b)
    return b


@pytest.fixture
async def empty_building(db_session: AsyncSession, admin_user: User) -> Building:
    """Building with no diagnostics, no samples, no risk data."""
    b = Building(
        id=uuid.uuid4(),
        address="Rue Vide 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=2020,
        building_type="commercial",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.commit()
    await db_session.refresh(b)
    return b


# ---------------------------------------------------------------------------
# Service-level tests: Owner report
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_owner_report_rich_building(db_session: AsyncSession, rich_building: Building):
    report = await generate_owner_report(db_session, rich_building.id)
    assert report is not None
    assert report.building_id == rich_building.id
    assert "Rue de la Gare 10" in report.executive_summary
    assert len(report.risk_overview) == 5
    # Asbestos should be critical
    asbestos = next(r for r in report.risk_overview if r.pollutant == "asbestos")
    assert asbestos.risk_level == "critical"
    assert "immediate" in asbestos.plain_language.lower() or "dangerous" in asbestos.plain_language.lower()


@pytest.mark.asyncio
async def test_owner_report_financial_impact(db_session: AsyncSession, rich_building: Building):
    report = await generate_owner_report(db_session, rich_building.id)
    assert report is not None
    assert report.financial_impact.estimated_total_chf > 0
    assert report.financial_impact.cost_range_low_chf < report.financial_impact.estimated_total_chf
    assert report.financial_impact.cost_range_high_chf > report.financial_impact.estimated_total_chf
    assert report.financial_impact.breakdown is not None
    assert len(report.financial_impact.breakdown) >= 1


@pytest.mark.asyncio
async def test_owner_report_action_plan(db_session: AsyncSession, rich_building: Building):
    report = await generate_owner_report(db_session, rich_building.id)
    assert report is not None
    assert len(report.action_plan) == 2
    assert any("asbestos" in a.title.lower() for a in report.action_plan)


@pytest.mark.asyncio
async def test_owner_report_next_steps(db_session: AsyncSession, rich_building: Building):
    report = await generate_owner_report(db_session, rich_building.id)
    assert report is not None
    assert len(report.next_steps) >= 1


@pytest.mark.asyncio
async def test_owner_report_empty_building(db_session: AsyncSession, empty_building: Building):
    report = await generate_owner_report(db_session, empty_building.id)
    assert report is not None
    assert report.building_id == empty_building.id
    assert len(report.risk_overview) == 0
    assert report.financial_impact.estimated_total_chf == 0.0
    assert len(report.action_plan) == 0
    assert "diagnostic" in report.next_steps[0].lower() or "diagnostic" in report.executive_summary.lower()


@pytest.mark.asyncio
async def test_owner_report_nonexistent_building(db_session: AsyncSession):
    report = await generate_owner_report(db_session, uuid.uuid4())
    assert report is None


# ---------------------------------------------------------------------------
# Service-level tests: Authority report
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_authority_report_rich_building(db_session: AsyncSession, rich_building: Building):
    report = await generate_authority_report(db_session, rich_building.id)
    assert report is not None
    assert report.overall_compliance_status == "non_compliant"
    assert report.diagnostic_coverage["asbestos"] is True
    assert report.diagnostic_coverage["pcb"] is True
    assert report.diagnostic_coverage["lead"] is False
    assert len(report.pollutant_statuses) == 5


@pytest.mark.asyncio
async def test_authority_report_pollutant_details(db_session: AsyncSession, rich_building: Building):
    report = await generate_authority_report(db_session, rich_building.id)
    assert report is not None
    asbestos = next(ps for ps in report.pollutant_statuses if ps.pollutant == "asbestos")
    assert asbestos.threshold_exceeded is True
    assert asbestos.sample_count == 2
    assert asbestos.max_concentration == 5.2
    assert asbestos.legal_threshold == 1.0


@pytest.mark.asyncio
async def test_authority_report_artefacts(db_session: AsyncSession, rich_building: Building):
    report = await generate_authority_report(db_session, rich_building.id)
    assert report is not None
    assert len(report.artefact_statuses) == 1
    assert report.artefact_statuses[0].artefact_type == "waste_elimination_plan"


@pytest.mark.asyncio
async def test_authority_report_empty_building(db_session: AsyncSession, empty_building: Building):
    report = await generate_authority_report(db_session, empty_building.id)
    assert report is not None
    assert report.overall_compliance_status == "unknown"
    assert all(not v for v in report.diagnostic_coverage.values())
    assert len(report.artefact_statuses) == 0


@pytest.mark.asyncio
async def test_authority_report_nonexistent(db_session: AsyncSession):
    report = await generate_authority_report(db_session, uuid.uuid4())
    assert report is None


# ---------------------------------------------------------------------------
# Service-level tests: Contractor briefing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_contractor_briefing_rich_building(db_session: AsyncSession, rich_building: Building):
    briefing = await generate_contractor_briefing(db_session, rich_building.id)
    assert briefing is not None
    assert len(briefing.pollutant_locations) == 2  # 2 threshold-exceeded samples
    assert "asbestos" in briefing.work_scope_summary.lower() or "pcb" in briefing.work_scope_summary.lower()


@pytest.mark.asyncio
async def test_contractor_briefing_safety_requirements(db_session: AsyncSession, rich_building: Building):
    briefing = await generate_contractor_briefing(db_session, rich_building.id)
    assert briefing is not None
    assert len(briefing.safety_requirements) >= 1
    categories = [sr.category for sr in briefing.safety_requirements]
    assert "major" in categories  # asbestos sample has major category


@pytest.mark.asyncio
async def test_contractor_briefing_access_constraints(db_session: AsyncSession, rich_building: Building):
    briefing = await generate_contractor_briefing(db_session, rich_building.id)
    assert briefing is not None
    assert len(briefing.access_constraints) >= 1
    assert any("intervention" in c.lower() for c in briefing.access_constraints)


@pytest.mark.asyncio
async def test_contractor_briefing_estimated_quantities(db_session: AsyncSession, rich_building: Building):
    briefing = await generate_contractor_briefing(db_session, rich_building.id)
    assert briefing is not None
    assert briefing.estimated_quantities.get("asbestos", 0) == 1
    assert briefing.estimated_quantities.get("pcb", 0) == 1


@pytest.mark.asyncio
async def test_contractor_briefing_empty_building(db_session: AsyncSession, empty_building: Building):
    briefing = await generate_contractor_briefing(db_session, empty_building.id)
    assert briefing is not None
    assert len(briefing.pollutant_locations) == 0
    assert len(briefing.safety_requirements) == 0
    assert "No confirmed" in briefing.work_scope_summary or "diagnostic" in briefing.work_scope_summary.lower()


@pytest.mark.asyncio
async def test_contractor_briefing_nonexistent(db_session: AsyncSession):
    briefing = await generate_contractor_briefing(db_session, uuid.uuid4())
    assert briefing is None


# ---------------------------------------------------------------------------
# Service-level tests: Portfolio executive summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_portfolio_summary_with_buildings(db_session: AsyncSession, org: Organization, rich_building: Building):
    report = await generate_portfolio_executive_summary(db_session, org.id)
    assert report is not None
    assert report.organization_id == org.id
    assert report.kpis.total_buildings == 1
    assert report.kpis.buildings_at_risk == 1  # critical
    assert report.kpis.estimated_total_cost_chf > 0
    assert len(report.top_priorities) == 1
    assert report.top_priorities[0].building_id == rich_building.id


@pytest.mark.asyncio
async def test_portfolio_summary_empty_org(db_session: AsyncSession):
    empty_org = Organization(id=uuid.uuid4(), name="Empty Org", type="property_management")
    db_session.add(empty_org)
    await db_session.commit()
    report = await generate_portfolio_executive_summary(db_session, empty_org.id)
    assert report is not None
    assert report.kpis.total_buildings == 0
    assert report.kpis.compliance_percentage == 100.0
    assert len(report.top_priorities) == 0


@pytest.mark.asyncio
async def test_portfolio_summary_nonexistent_org(db_session: AsyncSession):
    report = await generate_portfolio_executive_summary(db_session, uuid.uuid4())
    assert report is None


@pytest.mark.asyncio
async def test_portfolio_summary_trend_arrows(db_session: AsyncSession, org: Organization, rich_building: Building):
    report = await generate_portfolio_executive_summary(db_session, org.id)
    assert report is not None
    assert "risk" in report.trend_arrows
    assert "compliance" in report.trend_arrows
    assert "cost" in report.trend_arrows
    assert all(v in ("up", "down", "stable") for v in report.trend_arrows.values())


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_owner_report(client: AsyncClient, auth_headers: dict, sample_building: Building):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/report/owner", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert "executive_summary" in data
    assert "risk_overview" in data
    assert "financial_impact" in data


@pytest.mark.asyncio
async def test_api_authority_report(client: AsyncClient, auth_headers: dict, sample_building: Building):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/report/authority", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert "pollutant_statuses" in data
    assert "diagnostic_coverage" in data


@pytest.mark.asyncio
async def test_api_contractor_report(client: AsyncClient, auth_headers: dict, sample_building: Building):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/report/contractor", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert "pollutant_locations" in data
    assert "safety_requirements" in data


@pytest.mark.asyncio
async def test_api_owner_report_not_found(client: AsyncClient, auth_headers: dict):
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/buildings/{fake_id}/report/owner", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_authority_report_not_found(client: AsyncClient, auth_headers: dict):
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/buildings/{fake_id}/report/authority", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_contractor_report_not_found(client: AsyncClient, auth_headers: dict):
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/buildings/{fake_id}/report/contractor", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_executive_report_not_found(client: AsyncClient, auth_headers: dict):
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/organizations/{fake_id}/report/executive", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_owner_report_unauthenticated(client: AsyncClient, sample_building: Building):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/report/owner")
    assert resp.status_code == 403
