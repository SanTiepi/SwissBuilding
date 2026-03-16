"""Tests for the document template service."""

from __future__ import annotations

import uuid

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.services.document_template_service import (
    generate_template,
    get_available_templates,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def building_with_asbestos(db_session, admin_user):
    """Building with completed diagnostic, positive asbestos samples, and waste classification."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue Amiante 10",
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
        diagnostic_type="asbestos",
        diagnostic_context="AvT",
        status="completed",
        laboratory="LabTest SA",
        laboratory_report_number="LT-2025-001",
    )
    db_session.add(diag)
    await db_session.flush()

    sample1 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S-001",
        location_floor="1er etage",
        location_room="Salon",
        material_category="flocage",
        pollutant_type="asbestos",
        concentration=2.5,
        unit="percent_weight",
        threshold_exceeded=True,
        risk_level="high",
        cfst_work_category="major",
        waste_disposal_type="special",
    )
    sample2 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S-002",
        location_floor="2eme etage",
        location_room="Chambre",
        material_category="colle",
        pollutant_type="asbestos",
        concentration=0.1,
        unit="percent_weight",
        threshold_exceeded=False,
        risk_level="low",
    )
    db_session.add_all([sample1, sample2])
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def building_no_diagnostics(db_session, admin_user):
    """Building with no diagnostics at all."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue Vide 5",
        postal_code="1200",
        city="Geneve",
        canton="GE",
        construction_year=2010,
        building_type="commercial",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def building_with_intervention(db_session, admin_user):
    """Building with completed asbestos removal intervention."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue Intervention 3",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.flush()

    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="asbestos",
        status="completed",
    )
    db_session.add(diag)
    await db_session.flush()

    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S-010",
        pollutant_type="asbestos",
        concentration=3.0,
        unit="percent_weight",
        threshold_exceeded=True,
        risk_level="high",
        waste_disposal_type="special",
    )
    db_session.add(sample)

    intervention = Intervention(
        id=uuid.uuid4(),
        building_id=building.id,
        intervention_type="asbestos_removal",
        title="Desamiantage salon",
        status="completed",
        contractor_name="Sanacore AG",
    )
    db_session.add(intervention)
    await db_session.commit()
    await db_session.refresh(building)
    return building


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_templates_with_asbestos(db_session, building_with_asbestos):
    """Building with asbestos should have suva_notification available."""
    templates = await get_available_templates(db_session, building_with_asbestos.id)
    assert len(templates) == 7
    by_type = {t.template_type: t for t in templates}
    assert by_type["suva_notification"].is_available is True
    assert by_type["cantonal_notification"].is_available is True
    assert by_type["building_summary"].is_available is True
    assert by_type["diagnostic_summary"].is_available is True
    assert by_type["work_authorization_request"].is_available is True
    assert by_type["waste_elimination_plan"].is_available is True


@pytest.mark.asyncio
async def test_list_templates_no_diagnostics(db_session, building_no_diagnostics):
    """Building without diagnostics should only have building_summary available."""
    templates = await get_available_templates(db_session, building_no_diagnostics.id)
    available = [t for t in templates if t.is_available]
    assert len(available) == 1
    assert available[0].template_type == "building_summary"


@pytest.mark.asyncio
async def test_generate_building_summary(db_session, building_with_asbestos):
    """Building summary should have identity and owner sections populated."""
    result = await generate_template(db_session, building_with_asbestos.id, "building_summary")
    assert result.template_type == "building_summary"
    assert len(result.sections) == 2
    section_names = [s.name for s in result.sections]
    assert "identity" in section_names
    assert "owner" in section_names

    identity = next(s for s in result.sections if s.name == "identity")
    addr_field = next(f for f in identity.fields if f.label == "Adresse")
    assert addr_field.value == "Rue Amiante 10"
    assert addr_field.editable is False


@pytest.mark.asyncio
async def test_generate_suva_notification(db_session, building_with_asbestos):
    """SUVA notification should have correct pre-filled fields."""
    result = await generate_template(db_session, building_with_asbestos.id, "suva_notification")
    assert result.template_type == "suva_notification"
    section_names = [s.name for s in result.sections]
    assert "building" in section_names
    assert "findings" in section_names
    assert "work_category" in section_names
    assert "responsible" in section_names

    # Findings should only include positive asbestos samples
    findings = next(s for s in result.sections if s.name == "findings")
    assert len(findings.fields) == 1  # Only S-001 is positive
    assert "S-001" in findings.fields[0].label


@pytest.mark.asyncio
async def test_generate_diagnostic_summary(db_session, building_with_asbestos):
    """Diagnostic summary should list findings."""
    result = await generate_template(db_session, building_with_asbestos.id, "diagnostic_summary")
    assert result.template_type == "diagnostic_summary"
    section_names = [s.name for s in result.sections]
    assert "diagnostics" in section_names
    assert "samples" in section_names

    samples_section = next(s for s in result.sections if s.name == "samples")
    assert len(samples_section.fields) > 0


@pytest.mark.asyncio
async def test_template_not_available_raises_400(db_session, building_no_diagnostics):
    """Requesting an unavailable template should raise ValueError."""
    with pytest.raises(ValueError, match="not available"):
        await generate_template(db_session, building_no_diagnostics.id, "suva_notification")


@pytest.mark.asyncio
async def test_building_not_found_raises_404(db_session):
    """Requesting a template for nonexistent building should raise ValueError."""
    fake_id = uuid.uuid4()
    with pytest.raises(ValueError, match="not found"):
        await generate_template(db_session, fake_id, "building_summary")


@pytest.mark.asyncio
async def test_editable_fields_marked_correctly(db_session, building_with_asbestos):
    """Fields that need human review should be marked editable=True."""
    result = await generate_template(db_session, building_with_asbestos.id, "suva_notification")
    responsible = next(s for s in result.sections if s.name == "responsible")
    # All responsible fields should be editable (user must fill them)
    for field in responsible.fields:
        assert field.editable is True


@pytest.mark.asyncio
async def test_warnings_generated_for_missing_data(db_session, building_with_asbestos):
    """Warnings should be generated for data that couldn't be auto-filled."""
    result = await generate_template(db_session, building_with_asbestos.id, "suva_notification")
    assert len(result.warnings) > 0
    # Should warn about responsible person
    assert any("responsable" in w.lower() for w in result.warnings)


@pytest.mark.asyncio
async def test_waste_elimination_requires_classified_waste(db_session, building_no_diagnostics):
    """Waste elimination plan should not be available without classified waste."""
    templates = await get_available_templates(db_session, building_no_diagnostics.id)
    by_type = {t.template_type: t for t in templates}
    assert by_type["waste_elimination_plan"].is_available is False


@pytest.mark.asyncio
async def test_air_clearance_available_with_intervention(db_session, building_with_intervention):
    """Air clearance request should be available when asbestos intervention is completed."""
    templates = await get_available_templates(db_session, building_with_intervention.id)
    by_type = {t.template_type: t for t in templates}
    assert by_type["air_clearance_request"].is_available is True


@pytest.mark.asyncio
async def test_unknown_template_type_raises_error(db_session, building_with_asbestos):
    """Unknown template type should raise ValueError."""
    with pytest.raises(ValueError, match="Unknown template type"):
        await generate_template(db_session, building_with_asbestos.id, "nonexistent_template")


@pytest.mark.asyncio
async def test_building_not_found_returns_empty_list(db_session):
    """get_available_templates for nonexistent building returns empty list."""
    fake_id = uuid.uuid4()
    templates = await get_available_templates(db_session, fake_id)
    assert templates == []


@pytest.mark.asyncio
async def test_metadata_populated(db_session, building_with_asbestos):
    """Generated template metadata should contain building info."""
    result = await generate_template(db_session, building_with_asbestos.id, "building_summary")
    assert "building_id" in result.metadata
    assert "building_address" in result.metadata
    assert "Rue Amiante 10" in result.metadata["building_address"]
    assert result.generated_at is not None


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_list_templates(client, auth_headers, building_with_asbestos):
    """GET /buildings/{id}/templates should return 200."""
    resp = await client.get(
        f"/api/v1/buildings/{building_with_asbestos.id}/templates",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 7
    types = {t["template_type"] for t in data}
    assert "building_summary" in types
    assert "suva_notification" in types


@pytest.mark.asyncio
async def test_api_generate_template(client, auth_headers, building_with_asbestos):
    """POST /buildings/{id}/templates/generate should return 200."""
    resp = await client.post(
        f"/api/v1/buildings/{building_with_asbestos.id}/templates/generate",
        headers=auth_headers,
        json={"template_type": "building_summary"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["template_type"] == "building_summary"
    assert "sections" in data
    assert "warnings" in data


@pytest.mark.asyncio
async def test_api_generate_unavailable_template_returns_400(client, auth_headers, building_no_diagnostics):
    """Generating an unavailable template via API should return 400."""
    resp = await client.post(
        f"/api/v1/buildings/{building_no_diagnostics.id}/templates/generate",
        headers=auth_headers,
        json={"template_type": "suva_notification"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_api_generate_nonexistent_building_returns_404(client, auth_headers):
    """Generating a template for nonexistent building via API should return 404."""
    fake_id = uuid.uuid4()
    resp = await client.post(
        f"/api/v1/buildings/{fake_id}/templates/generate",
        headers=auth_headers,
        json={"template_type": "building_summary"},
    )
    assert resp.status_code == 404
