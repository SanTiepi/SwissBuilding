"""Tests for the compliance gap analysis service and API."""

from __future__ import annotations

import uuid

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.services.compliance_gap_service import (
    estimate_compliance_cost,
    generate_compliance_roadmap,
    get_portfolio_compliance_gaps,
    identify_compliance_gaps,
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
        address="Rue Org 10",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=org_user.id,
        status="active",
        surface_area_m2=500.0,
    )
    db_session.add(b)
    await db_session.commit()
    await db_session.refresh(b)
    return b


@pytest.fixture
async def building_with_asbestos(db_session, admin_user):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Amiante 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
        surface_area_m2=200.0,
    )
    db_session.add(b)
    await db_session.commit()

    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=b.id,
        diagnostic_type="full",
        status="completed",
    )
    db_session.add(d)
    await db_session.commit()

    s = Sample(
        id=uuid.uuid4(),
        diagnostic_id=d.id,
        sample_number="A-001",
        pollutant_type="asbestos",
        concentration=3.5,
        unit="percent_weight",
        threshold_exceeded=True,
        risk_level="high",
        material_category="flocage",
        material_state="degraded",
        cfst_work_category="major",
        waste_disposal_type="special",
    )
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(b)
    return b


@pytest.fixture
async def building_with_multi_pollutants(db_session, admin_user):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Multi 5",
        postal_code="1200",
        city="Geneva",
        canton="GE",
        construction_year=1975,
        building_type="commercial",
        created_by=admin_user.id,
        status="active",
        surface_area_m2=400.0,
    )
    db_session.add(b)
    await db_session.commit()

    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=b.id,
        diagnostic_type="full",
        status="validated",
    )
    db_session.add(d)
    await db_session.commit()

    samples = [
        Sample(
            id=uuid.uuid4(),
            diagnostic_id=d.id,
            sample_number="M-001",
            pollutant_type="asbestos",
            concentration=2.0,
            unit="percent_weight",
            threshold_exceeded=True,
            risk_level="high",
            cfst_work_category="medium",
            waste_disposal_type="type_e",
        ),
        Sample(
            id=uuid.uuid4(),
            diagnostic_id=d.id,
            sample_number="M-002",
            pollutant_type="pcb",
            concentration=120.0,
            unit="mg_per_kg",
            threshold_exceeded=True,
            risk_level="high",
            waste_disposal_type="special",
        ),
        Sample(
            id=uuid.uuid4(),
            diagnostic_id=d.id,
            sample_number="M-003",
            pollutant_type="lead",
            concentration=8000.0,
            unit="mg_per_kg",
            threshold_exceeded=True,
            risk_level="high",
            waste_disposal_type="type_e",
        ),
        Sample(
            id=uuid.uuid4(),
            diagnostic_id=d.id,
            sample_number="M-004",
            pollutant_type="radon",
            concentration=450.0,
            unit="bq_per_m3",
            threshold_exceeded=True,
            risk_level="medium",
        ),
    ]
    for s in samples:
        db_session.add(s)
    await db_session.commit()
    await db_session.refresh(b)
    return b


@pytest.fixture
async def building_clean(db_session, admin_user):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Propre 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=2010,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.commit()

    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=b.id,
        diagnostic_type="full",
        status="completed",
    )
    db_session.add(d)
    await db_session.commit()

    s = Sample(
        id=uuid.uuid4(),
        diagnostic_id=d.id,
        sample_number="C-001",
        pollutant_type="asbestos",
        concentration=0.2,
        unit="percent_weight",
        threshold_exceeded=False,
        risk_level="low",
    )
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(b)
    return b


# ---------------------------------------------------------------------------
# FN1: identify_compliance_gaps — service tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_identify_gaps_asbestos(db_session, building_with_asbestos):
    report = await identify_compliance_gaps(db_session, building_with_asbestos.id)
    assert report.building_id == building_with_asbestos.id
    assert report.total_gaps >= 1
    gap = report.gaps[0]
    assert gap.pollutant_type == "asbestos"
    assert "OTConst" in gap.regulation_ref
    assert gap.severity in ("medium", "high", "critical")
    assert gap.sample_count == 1


@pytest.mark.anyio
async def test_identify_gaps_multi_pollutants(db_session, building_with_multi_pollutants):
    report = await identify_compliance_gaps(db_session, building_with_multi_pollutants.id)
    assert report.total_gaps >= 3
    pollutants = {g.pollutant_type for g in report.gaps}
    assert "asbestos" in pollutants
    assert "pcb" in pollutants
    assert "lead" in pollutants


@pytest.mark.anyio
async def test_identify_gaps_clean_building(db_session, building_clean):
    report = await identify_compliance_gaps(db_session, building_clean.id)
    assert report.total_gaps == 0
    assert len(report.gaps) == 0
    assert len(report.compliant_regulations) > 0


@pytest.mark.anyio
async def test_identify_gaps_building_not_found(db_session):
    with pytest.raises(ValueError, match="not found"):
        await identify_compliance_gaps(db_session, uuid.uuid4())


@pytest.mark.anyio
async def test_identify_gaps_no_diagnostics(db_session, admin_user):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Vide 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1980,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.commit()

    report = await identify_compliance_gaps(db_session, b.id)
    assert report.total_gaps == 0


@pytest.mark.anyio
async def test_identify_gaps_sorted_by_severity(db_session, building_with_multi_pollutants):
    report = await identify_compliance_gaps(db_session, building_with_multi_pollutants.id)
    severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    severities = [severity_order.get(g.severity, 0) for g in report.gaps]
    assert severities == sorted(severities, reverse=True)


# ---------------------------------------------------------------------------
# FN2: generate_compliance_roadmap — service tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_roadmap_asbestos(db_session, building_with_asbestos):
    roadmap = await generate_compliance_roadmap(db_session, building_with_asbestos.id)
    assert roadmap.building_id == building_with_asbestos.id
    assert len(roadmap.steps) >= 1
    step = roadmap.steps[0]
    assert step.step_number == 1
    assert step.pollutant_type == "asbestos"
    assert step.estimated_weeks > 0
    assert step.responsible_party != ""


@pytest.mark.anyio
async def test_roadmap_multi_pollutants(db_session, building_with_multi_pollutants):
    roadmap = await generate_compliance_roadmap(db_session, building_with_multi_pollutants.id)
    assert len(roadmap.steps) >= 3
    assert roadmap.total_weeks > 0
    assert roadmap.critical_path_weeks > 0
    assert roadmap.critical_path_weeks <= roadmap.total_weeks


@pytest.mark.anyio
async def test_roadmap_clean_building(db_session, building_clean):
    roadmap = await generate_compliance_roadmap(db_session, building_clean.id)
    assert len(roadmap.steps) == 0
    assert roadmap.total_weeks == 0


@pytest.mark.anyio
async def test_roadmap_critical_path_flagged(db_session, building_with_multi_pollutants):
    roadmap = await generate_compliance_roadmap(db_session, building_with_multi_pollutants.id)
    critical_steps = [s for s in roadmap.steps if s.is_critical_path]
    assert len(critical_steps) >= 1


# ---------------------------------------------------------------------------
# FN3: estimate_compliance_cost — service tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_cost_estimate_asbestos(db_session, building_with_asbestos):
    cost = await estimate_compliance_cost(db_session, building_with_asbestos.id)
    assert cost.building_id == building_with_asbestos.id
    assert cost.total.expected_chf > 0
    assert cost.total.min_chf < cost.total.expected_chf < cost.total.max_chf
    assert len(cost.by_regulation) >= 1
    assert len(cost.by_pollutant) >= 1
    assert cost.by_category.labor_chf.expected_chf > 0
    assert cost.by_category.materials_chf.expected_chf > 0
    assert cost.by_category.disposal_chf.expected_chf > 0


@pytest.mark.anyio
async def test_cost_estimate_multi(db_session, building_with_multi_pollutants):
    cost = await estimate_compliance_cost(db_session, building_with_multi_pollutants.id)
    assert cost.total.expected_chf > 0
    pollutant_types = {p.pollutant_type for p in cost.by_pollutant}
    assert len(pollutant_types) >= 3


@pytest.mark.anyio
async def test_cost_estimate_clean(db_session, building_clean):
    cost = await estimate_compliance_cost(db_session, building_clean.id)
    assert cost.total.expected_chf == 0.0
    assert len(cost.by_regulation) == 0


@pytest.mark.anyio
async def test_cost_labor_materials_disposal_sum(db_session, building_with_asbestos):
    cost = await estimate_compliance_cost(db_session, building_with_asbestos.id)
    category_sum = (
        cost.by_category.labor_chf.expected_chf
        + cost.by_category.materials_chf.expected_chf
        + cost.by_category.disposal_chf.expected_chf
    )
    assert abs(category_sum - cost.total.expected_chf) < 0.02


# ---------------------------------------------------------------------------
# FN4: get_portfolio_compliance_gaps — service tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_portfolio_gaps_empty_org(db_session, org):
    result = await get_portfolio_compliance_gaps(db_session, org.id)
    assert result.organization_id == org.id
    assert result.total_buildings == 0
    assert result.total_gap_count == 0


@pytest.mark.anyio
async def test_portfolio_gaps_with_buildings(db_session, org, org_user, org_building):
    # Add a diagnostic with exceeded sample to org_building
    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=org_building.id,
        diagnostic_type="full",
        status="completed",
    )
    db_session.add(d)
    await db_session.commit()

    s = Sample(
        id=uuid.uuid4(),
        diagnostic_id=d.id,
        sample_number="P-001",
        pollutant_type="pcb",
        concentration=100.0,
        unit="mg_per_kg",
        threshold_exceeded=True,
        risk_level="high",
    )
    db_session.add(s)
    await db_session.commit()

    result = await get_portfolio_compliance_gaps(db_session, org.id)
    assert result.total_buildings == 1
    assert result.buildings_with_gaps == 1
    assert result.total_gap_count >= 1
    assert result.estimated_total_cost_chf > 0
    assert len(result.most_common_gaps) >= 1
    assert len(result.furthest_from_compliance) >= 1


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_api_compliance_gaps(client, auth_headers, building_with_asbestos):
    resp = await client.get(
        f"/api/v1/buildings/{building_with_asbestos.id}/compliance-gaps",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_gaps"] >= 1
    assert len(data["gaps"]) >= 1


@pytest.mark.anyio
async def test_api_compliance_gaps_not_found(client, auth_headers):
    resp = await client.get(
        f"/api/v1/buildings/{uuid.uuid4()}/compliance-gaps",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_api_compliance_roadmap(client, auth_headers, building_with_asbestos):
    resp = await client.get(
        f"/api/v1/buildings/{building_with_asbestos.id}/compliance-roadmap",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["steps"]) >= 1


@pytest.mark.anyio
async def test_api_compliance_cost(client, auth_headers, building_with_asbestos):
    resp = await client.get(
        f"/api/v1/buildings/{building_with_asbestos.id}/compliance-cost",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"]["expected_chf"] > 0


@pytest.mark.anyio
async def test_api_org_compliance_gaps(client, auth_headers, org):
    resp = await client.get(
        f"/api/v1/organizations/{org.id}/compliance-gaps",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["organization_id"] == str(org.id)


@pytest.mark.anyio
async def test_api_unauthorized(client, building_with_asbestos):
    resp = await client.get(
        f"/api/v1/buildings/{building_with_asbestos.id}/compliance-gaps",
    )
    assert resp.status_code in (401, 403)
