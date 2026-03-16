"""Tests for handoff pack generation service and API endpoints."""

import uuid
from datetime import date

import pytest
from httpx import AsyncClient

from app.models.action_item import ActionItem
from app.models.assignment import Assignment
from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.building_risk_score import BuildingRiskScore
from app.models.compliance_artefact import ComplianceArtefact
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.material import Material
from app.models.sample import Sample
from app.models.zone import Zone

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def building_with_data(db_session, admin_user):
    """Create a building with full diagnostic data for handoff testing."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue du Handoff 10",
        postal_code="1003",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        floors_above=4,
        floors_below=1,
        surface_area_m2=800.0,
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(building)

    # Diagnostic with samples
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="asbestos",
        status="completed",
        date_inspection=date(2025, 6, 15),
        date_report=date(2025, 6, 20),
        laboratory="LabTest SA",
        laboratory_report_number="LT-2025-001",
        conclusion="presence",
        summary="Amiante detecte dans les joints de facade.",
        suva_notification_required=True,
        suva_notification_date=date(2025, 7, 1),
    )
    db_session.add(diag)

    s1 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="E-001",
        location_floor="2",
        location_room="Cuisine",
        material_category="joint",
        material_description="Joint de facade",
        material_state="bon",
        pollutant_type="asbestos",
        concentration=5.2,
        unit="%",
        threshold_exceeded=True,
        risk_level="high",
        cfst_work_category="major",
        waste_disposal_type="type_e",
    )
    s2 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="E-002",
        location_floor="1",
        location_room="Salon",
        material_category="coating",
        pollutant_type="asbestos",
        concentration=0.1,
        unit="%",
        threshold_exceeded=False,
        risk_level="low",
    )
    db_session.add_all([s1, s2])

    # Risk score
    risk = BuildingRiskScore(
        id=uuid.uuid4(),
        building_id=building.id,
        overall_risk_level="high",
        confidence=0.85,
        asbestos_probability=0.9,
        pcb_probability=0.1,
        lead_probability=0.2,
        hap_probability=0.05,
        radon_probability=0.15,
        data_source="diagnostic",
    )
    db_session.add(risk)

    # Actions
    a1 = ActionItem(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_id=diag.id,
        source_type="diagnostic",
        action_type="removal",
        title="Retrait des joints amiances",
        priority="high",
        status="open",
        due_date=date(2025, 12, 31),
        created_by=admin_user.id,
        metadata_json={"estimated_cost_chf": 15000},
    )
    db_session.add(a1)

    # Intervention
    intv = Intervention(
        id=uuid.uuid4(),
        building_id=building.id,
        intervention_type="removal",
        title="Desamiantage facade",
        status="planned",
        date_start=date(2026, 1, 15),
        date_end=date(2026, 3, 15),
        contractor_name="SanAmiante SA",
        cost_chf=25000.0,
        created_by=admin_user.id,
    )
    db_session.add(intv)

    # Zone and element with material
    zone = Zone(
        id=uuid.uuid4(),
        building_id=building.id,
        zone_type="floor",
        name="2eme etage",
        floor_number=2,
        created_by=admin_user.id,
    )
    db_session.add(zone)

    element = BuildingElement(
        id=uuid.uuid4(),
        zone_id=zone.id,
        element_type="wall",
        name="Mur facade sud",
        created_by=admin_user.id,
    )
    db_session.add(element)

    material = Material(
        id=uuid.uuid4(),
        element_id=element.id,
        material_type="joint",
        name="Joint mastic facade",
        contains_pollutant=True,
        pollutant_type="asbestos",
        pollutant_confirmed=True,
        installation_year=1972,
        created_by=admin_user.id,
    )
    db_session.add(material)

    # Document
    doc = Document(
        id=uuid.uuid4(),
        building_id=building.id,
        file_path="/docs/rapport.pdf",
        file_name="rapport-amiante-2025.pdf",
        document_type="diagnostic_report",
        description="Rapport de diagnostic amiante",
        uploaded_by=admin_user.id,
    )
    db_session.add(doc)

    # Compliance artefact
    artefact = ComplianceArtefact(
        id=uuid.uuid4(),
        building_id=building.id,
        artefact_type="notification",
        title="Notification SUVA",
        status="submitted",
        authority_name="SUVA",
        legal_basis="OTConst Art. 60a",
        created_by=admin_user.id,
    )
    db_session.add(artefact)

    # Assignment
    assignment = Assignment(
        id=uuid.uuid4(),
        target_type="building",
        target_id=building.id,
        user_id=admin_user.id,
        role="responsible",
        created_by=admin_user.id,
    )
    db_session.add(assignment)

    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def empty_building(db_session, admin_user):
    """Building with no diagnostic data — for testing empty/low-completeness scenarios."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue Vide 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1985,
        building_type="commercial",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_diagnostic_handoff_full_data(db_session, building_with_data):
    from app.services.handoff_pack_service import generate_diagnostic_handoff

    result = await generate_diagnostic_handoff(db_session, building_with_data.id)
    assert result.building_id == building_with_data.id
    assert len(result.findings_summary.items) >= 1
    assert result.findings_summary.items[0]["diagnostic_type"] == "asbestos"
    assert result.risk_levels.completeness == 1.0
    assert result.overall_completeness > 0.5


@pytest.mark.anyio
async def test_diagnostic_handoff_empty(db_session, empty_building):
    from app.services.handoff_pack_service import generate_diagnostic_handoff

    result = await generate_diagnostic_handoff(db_session, empty_building.id)
    assert result.building_id == empty_building.id
    assert len(result.findings_summary.items) == 0
    assert "Aucun diagnostic enregistre" in result.warnings


@pytest.mark.anyio
async def test_diagnostic_handoff_not_found(db_session):
    from app.services.handoff_pack_service import generate_diagnostic_handoff

    with pytest.raises(ValueError, match="Building not found"):
        await generate_diagnostic_handoff(db_session, uuid.uuid4())


@pytest.mark.anyio
async def test_contractor_handoff_full_data(db_session, building_with_data):
    from app.services.handoff_pack_service import generate_contractor_handoff

    result = await generate_contractor_handoff(db_session, building_with_data.id)
    assert result.building_id == building_with_data.id
    assert len(result.pollutant_map.items) >= 1
    assert result.pollutant_map.items[0]["pollutant_type"] == "asbestos"
    assert len(result.safety_requirements.items) >= 1
    assert len(result.access_constraints.items) >= 1
    assert len(result.reference_documents.items) >= 1
    assert result.overall_completeness > 0.5


@pytest.mark.anyio
async def test_contractor_handoff_empty(db_session, empty_building):
    from app.services.handoff_pack_service import generate_contractor_handoff

    result = await generate_contractor_handoff(db_session, empty_building.id)
    assert result.building_id == empty_building.id
    assert len(result.pollutant_map.items) == 0
    assert "Aucun travail planifie" in result.warnings


@pytest.mark.anyio
async def test_authority_handoff_full_data(db_session, building_with_data):
    from app.services.handoff_pack_service import generate_authority_handoff

    result = await generate_authority_handoff(db_session, building_with_data.id)
    assert result.building_id == building_with_data.id
    assert len(result.compliance_status.items) >= 1
    assert len(result.diagnostic_reports.items) >= 1
    assert len(result.responsible_parties.items) >= 1
    assert result.overall_completeness > 0.5


@pytest.mark.anyio
async def test_authority_handoff_empty(db_session, empty_building):
    from app.services.handoff_pack_service import generate_authority_handoff

    result = await generate_authority_handoff(db_session, empty_building.id)
    assert result.building_id == empty_building.id
    assert "Aucun rapport de diagnostic" in result.warnings
    assert "Aucune partie responsable identifiee" in result.warnings


@pytest.mark.anyio
async def test_validate_diagnostic_full(db_session, building_with_data):
    from app.services.handoff_pack_service import validate_handoff_completeness

    result = await validate_handoff_completeness(db_session, building_with_data.id, "diagnostic")
    assert result.handoff_type == "diagnostic"
    assert result.readiness_score >= 80
    assert result.is_ready is True
    assert len(result.missing_fields) == 0


@pytest.mark.anyio
async def test_validate_diagnostic_empty(db_session, empty_building):
    from app.services.handoff_pack_service import validate_handoff_completeness

    result = await validate_handoff_completeness(db_session, empty_building.id, "diagnostic")
    assert result.readiness_score < 80
    assert result.is_ready is False
    assert "diagnostics" in result.missing_fields


@pytest.mark.anyio
async def test_validate_contractor_full(db_session, building_with_data):
    from app.services.handoff_pack_service import validate_handoff_completeness

    result = await validate_handoff_completeness(db_session, building_with_data.id, "contractor")
    assert result.handoff_type == "contractor"
    assert result.readiness_score > 0


@pytest.mark.anyio
async def test_validate_authority_full(db_session, building_with_data):
    from app.services.handoff_pack_service import validate_handoff_completeness

    result = await validate_handoff_completeness(db_session, building_with_data.id, "authority")
    assert result.handoff_type == "authority"
    assert result.readiness_score > 0


@pytest.mark.anyio
async def test_validate_invalid_type(db_session, empty_building):
    from app.services.handoff_pack_service import validate_handoff_completeness

    with pytest.raises(ValueError, match="Invalid handoff_type"):
        await validate_handoff_completeness(db_session, empty_building.id, "invalid")


@pytest.mark.anyio
async def test_validate_building_not_found(db_session):
    from app.services.handoff_pack_service import validate_handoff_completeness

    with pytest.raises(ValueError, match="Building not found"):
        await validate_handoff_completeness(db_session, uuid.uuid4(), "diagnostic")


@pytest.mark.anyio
async def test_diagnostic_handoff_regulatory_items(db_session, building_with_data):
    """Verify regulatory obligations section includes SUVA and pollutant refs."""
    from app.services.handoff_pack_service import generate_diagnostic_handoff

    result = await generate_diagnostic_handoff(db_session, building_with_data.id)
    reg_items = result.regulatory_obligations.items
    pollutant_regs = [i for i in reg_items if i.get("pollutant_type") == "asbestos"]
    assert len(pollutant_regs) >= 1
    assert "OTConst" in pollutant_regs[0]["regulation"]
    suva_items = [i for i in reg_items if i.get("type") == "suva_notification"]
    assert len(suva_items) >= 1


@pytest.mark.anyio
async def test_contractor_handoff_disposal_requirements(db_session, building_with_data):
    """Verify disposal section maps pollutants to waste categories."""
    from app.services.handoff_pack_service import generate_contractor_handoff

    result = await generate_contractor_handoff(db_session, building_with_data.id)
    disposal = result.disposal_requirements.items
    assert len(disposal) >= 1
    assert disposal[0]["pollutant_type"] == "asbestos"
    assert "type_e" in str(disposal[0]["waste_category"])


@pytest.mark.anyio
async def test_authority_handoff_timeline_commitments(db_session, building_with_data):
    """Verify timeline commitments include SUVA notification dates."""
    from app.services.handoff_pack_service import generate_authority_handoff

    result = await generate_authority_handoff(db_session, building_with_data.id)
    timeline = result.timeline_commitments.items
    suva_items = [i for i in timeline if i.get("type") == "suva_notification"]
    assert len(suva_items) >= 1


# ---------------------------------------------------------------------------
# API-level tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_api_diagnostic_handoff(client: AsyncClient, auth_headers, building_with_data):
    resp = await client.get(
        f"/api/v1/buildings/{building_with_data.id}/handoff/diagnostic",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(building_with_data.id)
    assert "findings_summary" in data
    assert "risk_levels" in data


@pytest.mark.anyio
async def test_api_contractor_handoff(client: AsyncClient, auth_headers, building_with_data):
    resp = await client.get(
        f"/api/v1/buildings/{building_with_data.id}/handoff/contractor",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(building_with_data.id)
    assert "work_scope" in data
    assert "pollutant_map" in data


@pytest.mark.anyio
async def test_api_authority_handoff(client: AsyncClient, auth_headers, building_with_data):
    resp = await client.get(
        f"/api/v1/buildings/{building_with_data.id}/handoff/authority",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(building_with_data.id)
    assert "compliance_status" in data


@pytest.mark.anyio
async def test_api_validate_handoff(client: AsyncClient, auth_headers, building_with_data):
    resp = await client.get(
        f"/api/v1/buildings/{building_with_data.id}/handoff/validate?type=diagnostic",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["handoff_type"] == "diagnostic"
    assert "readiness_score" in data
    assert "is_ready" in data


@pytest.mark.anyio
async def test_api_validate_invalid_type(client: AsyncClient, auth_headers, building_with_data):
    resp = await client.get(
        f"/api/v1/buildings/{building_with_data.id}/handoff/validate?type=invalid",
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_api_handoff_not_found(client: AsyncClient, auth_headers):
    fake_id = uuid.uuid4()
    resp = await client.get(
        f"/api/v1/buildings/{fake_id}/handoff/diagnostic",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_api_handoff_unauthorized(client: AsyncClient, building_with_data):
    resp = await client.get(
        f"/api/v1/buildings/{building_with_data.id}/handoff/diagnostic",
    )
    assert resp.status_code == 403
