"""Tests for regulatory filing service (SUVA, cantonal declarations, OLED waste manifests)."""

import uuid
from datetime import date

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.services.regulatory_filing_service import (
    generate_cantonal_declaration,
    generate_suva_notification,
    generate_waste_manifest,
    get_filing_status,
)


@pytest.fixture
async def building_vd(db_session, admin_user):
    building = Building(
        id=uuid.uuid4(),
        address="Rue de Bourg 12",
        postal_code="1003",
        city="Lausanne",
        canton="VD",
        construction_year=1960,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def building_ge(db_session, admin_user):
    building = Building(
        id=uuid.uuid4(),
        address="Rue du Mont-Blanc 5",
        postal_code="1201",
        city="Genève",
        canton="GE",
        construction_year=1955,
        building_type="commercial",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def diagnostic_with_asbestos(db_session, building_vd, admin_user):
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_vd.id,
        diagnostic_type="asbestos",
        status="completed",
        diagnostician_id=admin_user.id,
        laboratory="LabTest SA",
        laboratory_report_number="LT-2024-001",
        date_report=date(2024, 6, 15),
        suva_notification_required=True,
    )
    db_session.add(diag)
    await db_session.commit()
    await db_session.refresh(diag)

    samples = [
        Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number="S001",
            location_floor="2ème étage",
            location_room="Salon",
            location_detail="Faux-plafond",
            material_description="Plaques fibrociment",
            material_state="friable",
            pollutant_type="asbestos",
            concentration=2.5,
            unit="%",
            threshold_exceeded=True,
            risk_level="high",
            cfst_work_category="major",
            action_required="removal",
        ),
        Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number="S002",
            location_floor="Sous-sol",
            location_room="Local technique",
            location_detail="Calorifugeage",
            material_description="Isolation tuyaux",
            material_state="bon",
            pollutant_type="asbestos",
            concentration=5.0,
            unit="%",
            threshold_exceeded=True,
            risk_level="medium",
            cfst_work_category="medium",
            action_required="encapsulation",
        ),
    ]
    for s in samples:
        db_session.add(s)
    await db_session.commit()
    return diag, samples


@pytest.fixture
async def diagnostic_with_pcb(db_session, building_vd, admin_user):
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_vd.id,
        diagnostic_type="pcb",
        status="validated",
        diagnostician_id=admin_user.id,
        laboratory="EnviroLab",
        laboratory_report_number="EL-2024-042",
        date_report=date(2024, 7, 1),
    )
    db_session.add(diag)
    await db_session.commit()
    await db_session.refresh(diag)

    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="P001",
        location_floor="3ème étage",
        location_room="Cuisine",
        location_detail="Joint de fenêtre",
        pollutant_type="pcb",
        concentration=120.0,
        unit="mg/kg",
        threshold_exceeded=True,
        risk_level="high",
    )
    db_session.add(sample)
    await db_session.commit()
    return diag, [sample]


@pytest.fixture
async def diagnostic_with_lead(db_session, building_ge, admin_user):
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_ge.id,
        diagnostic_type="lead",
        status="completed",
        diagnostician_id=admin_user.id,
        laboratory="SwissAnalytics",
        laboratory_report_number="SA-2024-099",
        date_report=date(2024, 8, 10),
        canton_notification_date=date(2024, 8, 20),
    )
    db_session.add(diag)
    await db_session.commit()
    await db_session.refresh(diag)

    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="L001",
        location_floor="1er étage",
        location_room="Chambre",
        location_detail="Peinture murale",
        pollutant_type="lead",
        concentration=3000.0,
        unit="mg/kg",
        threshold_exceeded=False,
        risk_level="medium",
    )
    db_session.add(sample)
    await db_session.commit()
    return diag, [sample]


@pytest.fixture
async def planned_intervention(db_session, building_vd, admin_user):
    intervention = Intervention(
        id=uuid.uuid4(),
        building_id=building_vd.id,
        intervention_type="asbestos_removal",
        title="Désamiantage faux-plafonds",
        status="planned",
        date_start=date(2025, 3, 1),
        date_end=date(2025, 4, 15),
        contractor_name="SanAmiante SA",
        created_by=admin_user.id,
    )
    db_session.add(intervention)
    await db_session.commit()
    await db_session.refresh(intervention)
    return intervention


# ==================== SUVA NOTIFICATION TESTS ====================


@pytest.mark.asyncio
async def test_suva_notification_with_asbestos(db_session, building_vd, diagnostic_with_asbestos):
    result = await generate_suva_notification(db_session, building_vd.id)
    assert result.building_id == building_vd.id
    assert result.address == "Rue de Bourg 12"
    assert result.canton == "VD"
    assert result.suva_notification_required is True
    assert len(result.pollutant_locations) == 2
    assert result.max_work_category == "major"


@pytest.mark.asyncio
async def test_suva_notification_safety_measures(db_session, building_vd, diagnostic_with_asbestos):
    result = await generate_suva_notification(db_session, building_vd.id)
    assert len(result.safety_measures) > 0
    categories = {m.category for m in result.safety_measures}
    assert "confinement" in categories
    assert "protection_individuelle" in categories


@pytest.mark.asyncio
async def test_suva_notification_with_contractor(
    db_session, building_vd, diagnostic_with_asbestos, planned_intervention
):
    result = await generate_suva_notification(db_session, building_vd.id)
    assert result.contractor is not None
    assert result.contractor.contractor_name == "SanAmiante SA"
    assert result.contractor.intervention_type == "asbestos_removal"


@pytest.mark.asyncio
async def test_suva_notification_duration(db_session, building_vd, diagnostic_with_asbestos):
    result = await generate_suva_notification(db_session, building_vd.id)
    # major category → 30 days
    assert result.estimated_duration_days == 30


@pytest.mark.asyncio
async def test_suva_notification_no_asbestos(db_session, building_vd):
    result = await generate_suva_notification(db_session, building_vd.id)
    assert result.suva_notification_required is False
    assert len(result.pollutant_locations) == 0
    assert result.max_work_category is None


@pytest.mark.asyncio
async def test_suva_notification_diagnostic_references(db_session, building_vd, diagnostic_with_asbestos):
    result = await generate_suva_notification(db_session, building_vd.id)
    assert len(result.diagnostic_references) == 1
    assert "LT-2024-001" in result.diagnostic_references[0]


@pytest.mark.asyncio
async def test_suva_notification_building_not_found(db_session):
    with pytest.raises(ValueError, match="not found"):
        await generate_suva_notification(db_session, uuid.uuid4())


# ==================== CANTONAL DECLARATION TESTS ====================


@pytest.mark.asyncio
async def test_cantonal_declaration_vd(db_session, building_vd, diagnostic_with_asbestos):
    result = await generate_cantonal_declaration(db_session, building_vd.id)
    assert result.canton == "VD"
    assert result.format_variant == "VD"
    assert "entreprise_assainissement" in result.required_fields
    assert any("SEVEN" in c for c in result.compliance_commitments)


@pytest.mark.asyncio
async def test_cantonal_declaration_ge(db_session, building_ge, diagnostic_with_lead):
    result = await generate_cantonal_declaration(db_session, building_ge.id)
    assert result.canton == "GE"
    assert result.format_variant == "GE"
    assert "entreprise_certifiee_FACH" in result.required_fields
    assert any("STEB" in c for c in result.compliance_commitments)


@pytest.mark.asyncio
async def test_cantonal_declaration_override_canton(db_session, building_vd, diagnostic_with_asbestos):
    result = await generate_cantonal_declaration(db_session, building_vd.id, canton="GE")
    assert result.canton == "GE"
    assert result.format_variant == "GE"


@pytest.mark.asyncio
async def test_cantonal_declaration_standard_canton(db_session, building_vd, diagnostic_with_asbestos):
    result = await generate_cantonal_declaration(db_session, building_vd.id, canton="BE")
    assert result.canton == "BE"
    assert result.format_variant == "standard"


@pytest.mark.asyncio
async def test_cantonal_declaration_pollutant_summary(db_session, building_vd, diagnostic_with_asbestos):
    result = await generate_cantonal_declaration(db_session, building_vd.id)
    assert "asbestos" in result.pollutant_summary
    assert result.pollutant_summary["asbestos"] == 2


@pytest.mark.asyncio
async def test_cantonal_declaration_diagnostic_refs(db_session, building_vd, diagnostic_with_asbestos):
    result = await generate_cantonal_declaration(db_session, building_vd.id)
    assert len(result.diagnostic_references) == 1
    ref = result.diagnostic_references[0]
    assert ref.laboratory == "LabTest SA"
    assert ref.laboratory_report_number == "LT-2024-001"


@pytest.mark.asyncio
async def test_cantonal_declaration_building_not_found(db_session):
    with pytest.raises(ValueError, match="not found"):
        await generate_cantonal_declaration(db_session, uuid.uuid4())


# ==================== WASTE MANIFEST TESTS ====================


@pytest.mark.asyncio
async def test_waste_manifest_with_asbestos(db_session, building_vd, diagnostic_with_asbestos):
    result = await generate_waste_manifest(db_session, building_vd.id)
    assert result.building_id == building_vd.id
    assert result.tracking_number.startswith("WM-")
    categories = {e.waste_category for e in result.waste_entries}
    assert "special" in categories


@pytest.mark.asyncio
async def test_waste_manifest_with_pcb(db_session, building_vd, diagnostic_with_pcb):
    result = await generate_waste_manifest(db_session, building_vd.id)
    categories = {e.waste_category for e in result.waste_entries}
    assert "special" in categories  # PCB > 50 mg/kg → special


@pytest.mark.asyncio
async def test_waste_manifest_transport_chain(db_session, building_vd, diagnostic_with_asbestos):
    result = await generate_waste_manifest(db_session, building_vd.id)
    assert len(result.transport_chain) == 3
    # Special waste requires ADR
    step2_reqs = result.transport_chain[1].requirements
    assert any("ADR" in r for r in step2_reqs)


@pytest.mark.asyncio
async def test_waste_manifest_responsible_parties(
    db_session, building_vd, diagnostic_with_asbestos, planned_intervention
):
    result = await generate_waste_manifest(db_session, building_vd.id)
    roles = {p.role for p in result.responsible_parties}
    assert "maître_ouvrage" in roles
    assert "entreprise_assainissement" in roles


@pytest.mark.asyncio
async def test_waste_manifest_no_samples(db_session, building_vd):
    result = await generate_waste_manifest(db_session, building_vd.id)
    assert len(result.waste_entries) == 1
    assert result.waste_entries[0].waste_category == "type_b"


@pytest.mark.asyncio
async def test_waste_manifest_building_not_found(db_session):
    with pytest.raises(ValueError, match="not found"):
        await generate_waste_manifest(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_waste_manifest_regulatory_references(db_session, building_vd, diagnostic_with_asbestos):
    result = await generate_waste_manifest(db_session, building_vd.id)
    assert any("OLED" in r for r in result.regulatory_references)
    assert any("ORRChim" in r for r in result.regulatory_references)


# ==================== FILING STATUS TESTS ====================


@pytest.mark.asyncio
async def test_filing_status_all_required(db_session, building_vd, diagnostic_with_asbestos, diagnostic_with_pcb):
    result = await get_filing_status(db_session, building_vd.id)
    assert result.total_required == 3  # suva + cantonal + waste
    assert result.total_overdue >= 2  # suva and cantonal at minimum


@pytest.mark.asyncio
async def test_filing_status_suva_required(db_session, building_vd, diagnostic_with_asbestos):
    result = await get_filing_status(db_session, building_vd.id)
    suva = next(f for f in result.filings if f.filing_type == "suva_notification")
    assert suva.required is True
    assert suva.overdue is True
    assert "SUVA" in (suva.next_action or "")


@pytest.mark.asyncio
async def test_filing_status_no_pollutants(db_session, building_vd):
    result = await get_filing_status(db_session, building_vd.id)
    assert result.total_required == 0
    assert result.total_overdue == 0


@pytest.mark.asyncio
async def test_filing_status_cantonal_completed(db_session, building_ge, diagnostic_with_lead):
    result = await get_filing_status(db_session, building_ge.id)
    cantonal = next(f for f in result.filings if f.filing_type == "cantonal_declaration")
    assert cantonal.required is True
    assert cantonal.completed is True
    assert cantonal.overdue is False


@pytest.mark.asyncio
async def test_filing_status_building_not_found(db_session):
    with pytest.raises(ValueError, match="not found"):
        await get_filing_status(db_session, uuid.uuid4())


# ==================== API TESTS ====================


@pytest.mark.asyncio
async def test_api_suva_notification(client, auth_headers, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/regulatory-filings/suva",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert "suva_notification_required" in data


@pytest.mark.asyncio
async def test_api_cantonal_declaration(client, auth_headers, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/regulatory-filings/cantonal-declaration",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["canton"] == "VD"


@pytest.mark.asyncio
async def test_api_cantonal_declaration_with_canton_param(client, auth_headers, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/regulatory-filings/cantonal-declaration?canton=GE",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["canton"] == "GE"
    assert data["format_variant"] == "GE"


@pytest.mark.asyncio
async def test_api_waste_manifest(client, auth_headers, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/regulatory-filings/waste-manifest",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["tracking_number"].startswith("WM-")


@pytest.mark.asyncio
async def test_api_filing_status(client, auth_headers, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/regulatory-filings/status",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "filings" in data
    assert len(data["filings"]) == 3


@pytest.mark.asyncio
async def test_api_suva_404(client, auth_headers):
    resp = await client.get(
        f"/api/v1/buildings/{uuid.uuid4()}/regulatory-filings/suva",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_unauthenticated(client, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/regulatory-filings/suva",
    )
    assert resp.status_code in (401, 403)
