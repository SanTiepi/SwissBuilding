"""Tests for the Material Recommendation Service."""

from __future__ import annotations

import uuid

import pytest

from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.material import Material
from app.models.sample import Sample
from app.models.user import User
from app.models.zone import Zone
from app.schemas.material_recommendation import (
    EvidenceRequirement,
    MaterialRecommendation,
    MaterialRecommendationReport,
)
from app.services.material_recommendation_service import (
    _assess_risk_level,
    _build_reason,
    _build_summary,
    _get_evidence_requirements,
    _get_risk_flags,
    _get_safe_alternative,
    generate_recommendations,
)

# ── Helpers ────────────────────────────────────────────────────────


async def _seed_user(db):
    user = User(
        id=uuid.uuid4(),
        email=f"test-{uuid.uuid4().hex[:8]}@test.ch",
        password_hash="$2b$12$LJ3m4ys3Lk0YnPsOK1/KpOJPsFKN1UWmhzK2jqYGnH0BDL0GALXC",
        first_name="Test",
        last_name="User",
        role="admin",
    )
    db.add(user)
    await db.flush()
    return user


async def _seed_building(db, user):
    building = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=user.id,
        owner_id=user.id,
        status="active",
    )
    db.add(building)
    await db.flush()
    return building


async def _seed_zone(db, building):
    zone = Zone(
        id=uuid.uuid4(),
        building_id=building.id,
        zone_type="floor",
        name="Ground floor",
    )
    db.add(zone)
    await db.flush()
    return zone


async def _seed_element(db, zone):
    element = BuildingElement(
        id=uuid.uuid4(),
        zone_id=zone.id,
        element_type="wall",
        name="Main wall",
    )
    db.add(element)
    await db.flush()
    return element


async def _seed_pollutant_material(db, element, pollutant="asbestos", mat_type="insulation", **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "element_id": element.id,
        "material_type": mat_type,
        "name": f"Test {mat_type}",
        "contains_pollutant": True,
        "pollutant_type": pollutant,
        "pollutant_confirmed": False,
    }
    defaults.update(kwargs)
    material = Material(**defaults)
    db.add(material)
    await db.flush()
    return material


async def _seed_intervention(db, building, intervention_type="renovation", status="planned"):
    intervention = Intervention(
        id=uuid.uuid4(),
        building_id=building.id,
        intervention_type=intervention_type,
        title=f"Test {intervention_type}",
        status=status,
    )
    db.add(intervention)
    await db.flush()
    return intervention


async def _seed_diagnostic_with_sample(db, building, user, pollutant="asbestos", risk="high"):
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="avant_travaux",
        status="completed",
        diagnostician_id=user.id,
    )
    db.add(diag)
    await db.flush()

    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number=f"S-{uuid.uuid4().hex[:6]}",
        pollutant_type=pollutant,
        threshold_exceeded=True,
        risk_level=risk,
        location_detail="Wall sample",
    )
    db.add(sample)
    await db.flush()
    return diag, sample


# ── Unit tests (pure functions) ───────────────────────────────────


class TestGetSafeAlternative:
    def test_known_combo(self):
        alt_type, alt_desc = _get_safe_alternative("asbestos", "insulation")
        assert alt_type == "mineral_wool_new_gen"
        assert "asbestos-free" in alt_desc

    def test_unknown_material_type_falls_back(self):
        alt_type, _alt_desc = _get_safe_alternative("asbestos", "exotic_material")
        assert alt_type == "generic_safe_replacement"

    def test_unknown_pollutant_falls_back(self):
        alt_type, _ = _get_safe_alternative("unknown_pollutant", "wall")
        assert alt_type == "generic_safe_replacement"

    def test_pcb_coating(self):
        _alt_type, alt_desc = _get_safe_alternative("pcb", "coating")
        assert "PCB-free" in alt_desc

    def test_lead_pipe(self):
        alt_type, _alt_desc = _get_safe_alternative("lead", "pipe")
        assert alt_type == "pe_hd_pipe"


class TestGetEvidenceRequirements:
    def test_asbestos_has_four_docs(self):
        evidence = _get_evidence_requirements("asbestos")
        assert len(evidence) == 4
        assert all(isinstance(e, EvidenceRequirement) for e in evidence)
        types = {e.document_type for e in evidence}
        assert "lab_analysis_certificate" in types
        assert "waste_elimination_plan" in types

    def test_pcb_evidence(self):
        evidence = _get_evidence_requirements("pcb")
        assert len(evidence) == 3

    def test_unknown_pollutant_gets_default(self):
        evidence = _get_evidence_requirements("exotic")
        assert len(evidence) == 1
        assert evidence[0].document_type == "supplier_declaration"

    def test_all_mandatory_flags(self):
        evidence = _get_evidence_requirements("asbestos")
        mandatory = [e for e in evidence if e.mandatory]
        assert len(mandatory) == 4


class TestAssessRiskLevel:
    def test_linked_sample_uses_sample_risk(self):
        sample_id = uuid.uuid4()
        mat = Material(
            id=uuid.uuid4(),
            element_id=uuid.uuid4(),
            material_type="insulation",
            name="Test",
            contains_pollutant=True,
            pollutant_type="asbestos",
            sample_id=sample_id,
        )
        sample = Sample(
            id=sample_id,
            diagnostic_id=uuid.uuid4(),
            sample_number="S-TEST",
            pollutant_type="asbestos",
            risk_level="critical",
            threshold_exceeded=True,
        )
        assert _assess_risk_level(mat, [sample]) == "critical"

    def test_confirmed_pollutant_returns_high(self):
        mat = Material(
            id=uuid.uuid4(),
            element_id=uuid.uuid4(),
            material_type="coating",
            name="Test",
            contains_pollutant=True,
            pollutant_type="lead",
            pollutant_confirmed=True,
        )
        assert _assess_risk_level(mat, []) == "high"

    def test_unconfirmed_returns_medium(self):
        mat = Material(
            id=uuid.uuid4(),
            element_id=uuid.uuid4(),
            material_type="coating",
            name="Test",
            contains_pollutant=True,
            pollutant_type="lead",
            pollutant_confirmed=False,
        )
        assert _assess_risk_level(mat, []) == "medium"


class TestGetRiskFlags:
    def test_asbestos_flags(self):
        mat = Material(
            id=uuid.uuid4(),
            element_id=uuid.uuid4(),
            material_type="insulation",
            name="Test",
            contains_pollutant=True,
            pollutant_type="asbestos",
            pollutant_confirmed=False,
        )
        flags = _get_risk_flags("asbestos", mat, "medium")
        assert len(flags) >= 2
        assert any("SUVA" in f for f in flags)

    def test_critical_risk_adds_flag(self):
        mat = Material(
            id=uuid.uuid4(),
            element_id=uuid.uuid4(),
            material_type="coating",
            name="Test",
            contains_pollutant=True,
            pollutant_type="pcb",
            pollutant_confirmed=True,
        )
        flags = _get_risk_flags("pcb", mat, "critical")
        assert any("CRITICAL" in f for f in flags)
        assert any("confirmed" in f.lower() for f in flags)


class TestBuildReason:
    def test_includes_pollutant_and_risk(self):
        reason = _build_reason("asbestos", "insulation", "high")
        assert "asbestos" in reason
        assert "high" in reason
        assert "insulation" in reason

    def test_includes_legal_ref(self):
        reason = _build_reason("asbestos", "insulation", "high")
        assert "OTConst" in reason or "FACH" in reason


class TestBuildSummary:
    def test_no_materials(self):
        summary = _build_summary(0, 0, 0)
        assert "No pollutant-containing materials" in summary

    def test_materials_but_no_recommendations(self):
        summary = _build_summary(0, 3, 0)
        assert "3 pollutant-containing" in summary

    def test_with_recommendations(self):
        summary = _build_summary(2, 5, 4)
        assert "4 material replacement" in summary
        assert "5 pollutant-containing" in summary
        assert "2 active intervention" in summary


# ── Integration tests (async, uses DB) ────────────────────────────


@pytest.mark.asyncio
async def test_generate_recommendations_building_not_found(db_session):
    with pytest.raises(ValueError, match="not found"):
        await generate_recommendations(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_generate_recommendations_no_pollutant_materials(db_session):
    user = await _seed_user(db_session)
    building = await _seed_building(db_session, user)

    report = await generate_recommendations(db_session, building.id)
    assert isinstance(report, MaterialRecommendationReport)
    assert report.pollutant_material_count == 0
    assert report.recommendations == []
    assert "No pollutant-containing materials" in report.summary


@pytest.mark.asyncio
async def test_generate_recommendations_with_pollutant_material(db_session):
    user = await _seed_user(db_session)
    building = await _seed_building(db_session, user)
    zone = await _seed_zone(db_session, building)
    element = await _seed_element(db_session, zone)
    await _seed_pollutant_material(db_session, element, pollutant="asbestos", mat_type="insulation")
    await _seed_intervention(db_session, building, intervention_type="renovation", status="planned")

    report = await generate_recommendations(db_session, building.id)
    assert report.pollutant_material_count == 1
    assert len(report.recommendations) == 1

    rec = report.recommendations[0]
    assert rec.original_pollutant == "asbestos"
    assert rec.original_material_type == "insulation"
    assert rec.recommended_material_type == "mineral_wool_new_gen"
    assert len(rec.evidence_requirements) == 4
    assert rec.risk_level == "medium"  # unconfirmed


@pytest.mark.asyncio
async def test_generate_recommendations_multiple_pollutants(db_session):
    user = await _seed_user(db_session)
    building = await _seed_building(db_session, user)
    zone = await _seed_zone(db_session, building)
    element = await _seed_element(db_session, zone)
    await _seed_pollutant_material(db_session, element, pollutant="asbestos", mat_type="insulation")
    await _seed_pollutant_material(db_session, element, pollutant="pcb", mat_type="coating")
    await _seed_pollutant_material(db_session, element, pollutant="lead", mat_type="pipe")
    await _seed_intervention(db_session, building, intervention_type="renovation", status="planned")

    report = await generate_recommendations(db_session, building.id)
    assert report.pollutant_material_count == 3
    assert len(report.recommendations) == 3
    pollutants = {r.original_pollutant for r in report.recommendations}
    assert pollutants == {"asbestos", "pcb", "lead"}


@pytest.mark.asyncio
async def test_generate_recommendations_confirmed_pollutant_higher_risk(db_session):
    user = await _seed_user(db_session)
    building = await _seed_building(db_session, user)
    zone = await _seed_zone(db_session, building)
    element = await _seed_element(db_session, zone)
    await _seed_pollutant_material(
        db_session, element, pollutant="asbestos", mat_type="insulation", pollutant_confirmed=True
    )
    await _seed_intervention(db_session, building, intervention_type="asbestos_removal", status="planned")

    report = await generate_recommendations(db_session, building.id)
    assert len(report.recommendations) == 1
    assert report.recommendations[0].risk_level == "high"


@pytest.mark.asyncio
async def test_generate_recommendations_with_linked_sample(db_session):
    user = await _seed_user(db_session)
    building = await _seed_building(db_session, user)
    zone = await _seed_zone(db_session, building)
    element = await _seed_element(db_session, zone)
    _, sample = await _seed_diagnostic_with_sample(db_session, building, user, pollutant="asbestos", risk="critical")
    await _seed_pollutant_material(
        db_session, element, pollutant="asbestos", mat_type="insulation", sample_id=sample.id
    )
    await _seed_intervention(db_session, building, intervention_type="renovation", status="planned")

    report = await generate_recommendations(db_session, building.id)
    assert len(report.recommendations) == 1
    assert report.recommendations[0].risk_level == "critical"
    assert any("CRITICAL" in f for f in report.recommendations[0].risk_flags)


@pytest.mark.asyncio
async def test_generate_recommendations_no_active_interventions(db_session):
    user = await _seed_user(db_session)
    building = await _seed_building(db_session, user)
    zone = await _seed_zone(db_session, building)
    element = await _seed_element(db_session, zone)
    await _seed_pollutant_material(db_session, element, pollutant="asbestos", mat_type="insulation")
    # Only completed intervention — not active
    await _seed_intervention(db_session, building, intervention_type="renovation", status="completed")

    report = await generate_recommendations(db_session, building.id)
    # Materials still found, recommendations still generated (materials drive recommendations)
    assert report.pollutant_material_count == 1
    assert report.intervention_count == 0


# ── Schema tests ──────────────────────────────────────────────────


class TestSchemaValidation:
    def test_evidence_requirement_minimal(self):
        er = EvidenceRequirement(document_type="cert", description="A cert")
        assert er.mandatory is True
        assert er.legal_ref is None

    def test_material_recommendation_schema(self):
        rec = MaterialRecommendation(
            original_material_type="insulation",
            original_pollutant="asbestos",
            recommended_material="Mineral wool",
            recommended_material_type="mineral_wool_new_gen",
            reason="Contains asbestos",
            risk_level="high",
            evidence_requirements=[],
            risk_flags=["Flag 1"],
        )
        assert rec.risk_level == "high"

    def test_report_schema(self):
        report = MaterialRecommendationReport(
            building_id=str(uuid.uuid4()),
            intervention_count=2,
            pollutant_material_count=3,
            recommendations=[],
            summary="Test summary",
        )
        assert report.intervention_count == 2
