"""Tests for contractor matching service and API endpoints."""

import uuid

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.organization import Organization
from app.models.sample import Sample
from app.services.contractor_matching_service import (
    estimate_contractor_needs,
    get_portfolio_contractor_demand,
    get_required_certifications,
    match_contractors,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def contractor_org(db_session):
    org = Organization(
        id=uuid.uuid4(),
        name="Sanacore AG",
        type="contractor",
        canton="VD",
        city="Lausanne",
        suva_recognized=True,
        fach_approved=True,
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def contractor_org_remote(db_session):
    org = Organization(
        id=uuid.uuid4(),
        name="RemoteBau GmbH",
        type="contractor",
        canton="ZH",
        city="Zurich",
        suva_recognized=False,
        fach_approved=False,
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def diagnostic_lab_org(db_session):
    org = Organization(
        id=uuid.uuid4(),
        name="DiagLab SA",
        type="diagnostic_lab",
        canton="VD",
        city="Lausanne",
        suva_recognized=True,
        fach_approved=True,
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def building_with_asbestos(db_session, admin_user):
    building = Building(
        id=uuid.uuid4(),
        address="Rue Amiante 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.flush()

    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="avant_travaux",
        status="completed",
    )
    db_session.add(diag)
    await db_session.flush()

    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S001",
        pollutant_type="asbestos",
        concentration=5.0,
        unit="percent_weight",
        threshold_exceeded=True,
        risk_level="high",
        cfst_work_category="major",
        material_category="flocage",
        material_state="degraded",
    )
    db_session.add(sample)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def building_multi_pollutant(db_session, admin_user):
    building = Building(
        id=uuid.uuid4(),
        address="Rue Multi 2",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1960,
        building_type="commercial",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.flush()

    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="full",
        status="completed",
    )
    db_session.add(diag)
    await db_session.flush()

    samples = [
        Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number="M001",
            pollutant_type="asbestos",
            concentration=3.0,
            unit="percent_weight",
            threshold_exceeded=True,
            risk_level="high",
            cfst_work_category="medium",
        ),
        Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number="M002",
            pollutant_type="pcb",
            concentration=120.0,
            unit="mg_per_kg",
            threshold_exceeded=True,
            risk_level="critical",
        ),
        Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number="M003",
            pollutant_type="lead",
            concentration=8000.0,
            unit="mg_per_kg",
            threshold_exceeded=True,
            risk_level="medium",
        ),
    ]
    for s in samples:
        db_session.add(s)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def building_no_pollutants(db_session, admin_user):
    building = Building(
        id=uuid.uuid4(),
        address="Rue Propre 3",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=2010,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def org_with_buildings(db_session, admin_user, building_with_asbestos):
    """An organization whose user created a building."""
    org = Organization(
        id=uuid.uuid4(),
        name="Regie Romande",
        type="property_management",
        canton="VD",
        city="Lausanne",
    )
    db_session.add(org)
    await db_session.flush()

    # Update admin_user to belong to this org
    admin_user.organization_id = org.id
    db_session.add(admin_user)
    await db_session.commit()
    await db_session.refresh(org)
    return org


# ---------------------------------------------------------------------------
# Service tests: match_contractors
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_match_contractors_ranks_by_score(
    db_session, building_with_asbestos, contractor_org, contractor_org_remote
):
    result = await match_contractors(db_session, building_with_asbestos.id)
    assert result["building_id"] == building_with_asbestos.id
    assert "asbestos" in result["pollutants_found"]
    assert len(result["contractors"]) == 2
    # Local SUVA contractor should rank higher
    assert result["contractors"][0]["organization_id"] == contractor_org.id
    assert result["contractors"][0]["total_score"] > result["contractors"][1]["total_score"]


@pytest.mark.asyncio
async def test_match_contractors_suva_bonus(db_session, building_with_asbestos, contractor_org):
    result = await match_contractors(db_session, building_with_asbestos.id)
    reasons = {r["factor"]: r for r in result["contractors"][0]["match_reasons"]}
    assert "suva_recognized" in reasons
    assert reasons["suva_recognized"]["score"] == 20.0


@pytest.mark.asyncio
async def test_match_contractors_empty_building(db_session, building_no_pollutants, contractor_org):
    result = await match_contractors(db_session, building_no_pollutants.id)
    assert result["pollutants_found"] == []
    # Contractor still listed but with lower score
    assert len(result["contractors"]) == 1


@pytest.mark.asyncio
async def test_match_contractors_nonexistent_building(db_session):
    fake_id = uuid.uuid4()
    result = await match_contractors(db_session, fake_id)
    assert result["contractors"] == []
    assert result["pollutants_found"] == []


@pytest.mark.asyncio
async def test_match_contractors_excludes_non_contractor_orgs(db_session, building_with_asbestos, diagnostic_lab_org):
    result = await match_contractors(db_session, building_with_asbestos.id)
    org_ids = [c["organization_id"] for c in result["contractors"]]
    assert diagnostic_lab_org.id not in org_ids


@pytest.mark.asyncio
async def test_match_contractors_location_proximity(
    db_session, building_with_asbestos, contractor_org, contractor_org_remote
):
    result = await match_contractors(db_session, building_with_asbestos.id)
    local = next(c for c in result["contractors"] if c["organization_id"] == contractor_org.id)
    remote = next(c for c in result["contractors"] if c["organization_id"] == contractor_org_remote.id)
    local_prox = next((r for r in local["match_reasons"] if r["factor"] == "location_proximity"), None)
    remote_prox = next((r for r in remote["match_reasons"] if r["factor"] == "location_proximity"), None)
    # Local (same canton) should have higher proximity score
    assert local_prox is not None
    assert local_prox["score"] > (remote_prox["score"] if remote_prox else 0)


# ---------------------------------------------------------------------------
# Service tests: get_required_certifications
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_required_certifications_asbestos(db_session, building_with_asbestos):
    result = await get_required_certifications(db_session, building_with_asbestos.id)
    assert result["building_id"] == building_with_asbestos.id
    assert result["cfst_work_category"] == "major"
    cert_names = [c["certification"] for c in result["suva_certifications"]]
    assert "SUVA_asbestos" in cert_names
    assert "CFST_6503" in cert_names


@pytest.mark.asyncio
async def test_required_certifications_multi_pollutant(db_session, building_multi_pollutant):
    result = await get_required_certifications(db_session, building_multi_pollutant.id)
    cert_names = [c["certification"] for c in result["suva_certifications"]]
    assert "SUVA_asbestos" in cert_names
    assert "SUVA_chemical_hazards" in cert_names
    assert "SUVA_lead" in cert_names


@pytest.mark.asyncio
async def test_required_certifications_empty(db_session, building_no_pollutants):
    result = await get_required_certifications(db_session, building_no_pollutants.id)
    assert result["suva_certifications"] == []
    assert result["cfst_work_category"] is None
    assert result["special_equipment"] == []


@pytest.mark.asyncio
async def test_required_certifications_equipment_major(db_session, building_with_asbestos):
    result = await get_required_certifications(db_session, building_with_asbestos.id)
    assert "full_containment_enclosure" in result["special_equipment"]
    assert "air_monitoring_equipment" in result["special_equipment"]


@pytest.mark.asyncio
async def test_required_certifications_notifications(db_session, building_with_asbestos):
    result = await get_required_certifications(db_session, building_with_asbestos.id)
    assert any("SUVA" in n for n in result["regulatory_notifications"])
    assert any("VD" in n for n in result["regulatory_notifications"])


@pytest.mark.asyncio
async def test_required_certifications_nonexistent(db_session):
    result = await get_required_certifications(db_session, uuid.uuid4())
    assert result["suva_certifications"] == []


# ---------------------------------------------------------------------------
# Service tests: estimate_contractor_needs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_contractor_needs_single_pollutant(db_session, building_with_asbestos):
    result = await estimate_contractor_needs(db_session, building_with_asbestos.id)
    assert result["building_id"] == building_with_asbestos.id
    assert len(result["pollutant_needs"]) == 1
    need = result["pollutant_needs"][0]
    assert need["pollutant"] == "asbestos"
    assert need["sample_count"] == 1
    assert need["max_risk_level"] == "high"
    assert need["specialists_needed"] >= 2
    assert result["total_specialists"] >= 2
    assert result["total_estimated_days"] > 0


@pytest.mark.asyncio
async def test_contractor_needs_multi_pollutant(db_session, building_multi_pollutant):
    result = await estimate_contractor_needs(db_session, building_multi_pollutant.id)
    assert len(result["pollutant_needs"]) == 3
    pollutants = [n["pollutant"] for n in result["pollutant_needs"]]
    assert "asbestos" in pollutants
    assert "pcb" in pollutants
    assert "lead" in pollutants
    # Asbestos + PCB => sequential (not parallel)
    assert result["parallel_possible"] is False
    assert result["safety_crew_required"] is True


@pytest.mark.asyncio
async def test_contractor_needs_empty(db_session, building_no_pollutants):
    result = await estimate_contractor_needs(db_session, building_no_pollutants.id)
    assert result["pollutant_needs"] == []
    assert result["total_specialists"] == 0
    assert result["total_estimated_days"] == 0.0
    assert result["work_sequence_recommendation"] == "No remediation needed"


@pytest.mark.asyncio
async def test_contractor_needs_nonexistent(db_session):
    result = await estimate_contractor_needs(db_session, uuid.uuid4())
    assert result["total_specialists"] == 0


@pytest.mark.asyncio
async def test_contractor_needs_safety_crew_critical(db_session, building_multi_pollutant):
    result = await estimate_contractor_needs(db_session, building_multi_pollutant.id)
    # PCB is critical -> safety crew required
    assert result["safety_crew_required"] is True
    pcb_need = next(n for n in result["pollutant_needs"] if n["pollutant"] == "pcb")
    assert pcb_need["requires_safety_crew"] is True


# ---------------------------------------------------------------------------
# Service tests: get_portfolio_contractor_demand
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_portfolio_demand(db_session, org_with_buildings):
    result = await get_portfolio_contractor_demand(db_session, org_with_buildings.id)
    assert result["organization_id"] == org_with_buildings.id
    assert result["total_buildings"] >= 1
    assert result["total_contractor_days"] > 0
    assert len(result["buildings"]) >= 1


@pytest.mark.asyncio
async def test_portfolio_demand_empty_org(db_session):
    org = Organization(
        id=uuid.uuid4(),
        name="Empty Org",
        type="property_management",
        canton="VD",
    )
    db_session.add(org)
    await db_session.commit()
    result = await get_portfolio_contractor_demand(db_session, org.id)
    assert result["total_buildings"] == 0
    assert result["total_contractor_days"] == 0.0
    assert result["buildings"] == []


@pytest.mark.asyncio
async def test_portfolio_demand_certification_distribution(db_session, org_with_buildings):
    result = await get_portfolio_contractor_demand(db_session, org_with_buildings.id)
    cert_names = [c["certification"] for c in result["certification_demand"]]
    # Building has asbestos, so SUVA_asbestos should be present
    assert "SUVA_asbestos" in cert_names


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_contractor_matching(client, auth_headers, sample_building):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/contractor-matching", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)


@pytest.mark.asyncio
async def test_api_required_certifications(client, auth_headers, sample_building):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/required-certifications", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)


@pytest.mark.asyncio
async def test_api_contractor_needs(client, auth_headers, sample_building):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/contractor-needs", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)


@pytest.mark.asyncio
async def test_api_contractor_demand(client, auth_headers, db_session, admin_user):
    org = Organization(
        id=uuid.uuid4(),
        name="TestOrg",
        type="property_management",
        canton="VD",
    )
    db_session.add(org)
    await db_session.commit()
    resp = await client.get(f"/api/v1/organizations/{org.id}/contractor-demand", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["organization_id"] == str(org.id)


@pytest.mark.asyncio
async def test_api_contractor_matching_unauthorized(client, sample_building):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/contractor-matching")
    assert resp.status_code in (401, 403)
