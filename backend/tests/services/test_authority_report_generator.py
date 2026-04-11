"""Tests for Programme M.1 — Authority Report Generator."""

import uuid
from datetime import UTC, date, timedelta

import pytest

from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.services.authority_report_generator import generate_authority_report
from app.services.report_templates import (
    render_action_plan_section,
    render_appendix_section,
    render_compliance_section,
    render_cover_page,
    render_diagnostics_section,
    render_evidence_section,
    render_executive_summary,
    render_recommendations_section,
    render_report_css,
    render_toc,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_building(db, admin_user, **overrides):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue du Test 42",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1965,
        "building_type": "residential",
        "surface_area_m2": 450.0,
        "floors_above": 4,
        "floors_below": 1,
        "created_by": admin_user.id,
        "owner_id": admin_user.id,
        "status": "active",
    }
    defaults.update(overrides)
    b = Building(**defaults)
    db.add(b)
    await db.flush()
    return b


async def _create_diagnostic(db, building_id, **overrides):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "diagnostic_type": "full_pollutant",
        "status": "completed",
        "date_inspection": date.today() - timedelta(days=30),
        "laboratory": "LabTest SA",
        "conclusion": "presence_confirmed",
        "methodology": "microscopy",
    }
    defaults.update(overrides)
    d = Diagnostic(**defaults)
    db.add(d)
    await db.flush()
    return d


async def _create_sample(db, diagnostic_id, **overrides):
    defaults = {
        "id": uuid.uuid4(),
        "diagnostic_id": diagnostic_id,
        "sample_number": f"S-{uuid.uuid4().hex[:6]}",
        "pollutant_type": "asbestos",
        "location_floor": "1er etage",
        "location_room": "Bureau 101",
        "material_description": "Faux-plafond",
        "concentration": 5.0,
        "unit": "%",
        "threshold_exceeded": True,
        "risk_level": "high",
        "cfst_work_category": "major",
    }
    defaults.update(overrides)
    s = Sample(**defaults)
    db.add(s)
    await db.flush()
    return s


async def _create_risk_score(db, building_id, **overrides):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "asbestos_probability": 0.85,
        "pcb_probability": 0.45,
        "lead_probability": 0.3,
        "hap_probability": 0.1,
        "radon_probability": 0.6,
        "overall_risk_level": "high",
    }
    defaults.update(overrides)
    r = BuildingRiskScore(**defaults)
    db.add(r)
    await db.flush()
    return r


async def _create_document(db, building_id, **overrides):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "file_name": "Rapport diagnostic amiante.pdf",
        "document_type": "diagnostic_report",
        "file_path": "/docs/test.pdf",
    }
    defaults.update(overrides)
    d = Document(**defaults)
    db.add(d)
    await db.flush()
    return d


async def _create_intervention(db, building_id, **overrides):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "title": "Desamiantage bureau 101",
        "intervention_type": "remediation",
        "status": "completed",
        "date_start": date.today() - timedelta(days=60),
        "date_end": date.today() - timedelta(days=30),
        "cost_chf": 15000.0,
        "contractor_name": "SanaCorp SA",
    }
    defaults.update(overrides)
    i = Intervention(**defaults)
    db.add(i)
    await db.flush()
    return i


# ---------------------------------------------------------------------------
# Tests — generate_authority_report
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_report_basic(db, admin_user):
    """Report generation with a building that has full data."""
    building = await _create_building(db, admin_user)
    diag = await _create_diagnostic(db, building.id)
    await _create_sample(db, diag.id)
    await _create_sample(db, diag.id, pollutant_type="pcb", concentration=80, threshold_exceeded=True)
    await _create_risk_score(db, building.id)
    await _create_document(db, building.id)
    await _create_intervention(db, building.id)
    await db.commit()

    result = await generate_authority_report(db, building.id)

    assert result is not None
    assert result["status"] == "generated"
    assert result["report_type"] == "authority"
    assert len(result["html_payload"]) > 5000
    assert result["sha256"]
    assert result["sections_count"] >= 7
    assert result["metadata"]["diagnostics_count"] == 1
    assert result["metadata"]["samples_count"] == 2
    assert result["metadata"]["documents_count"] == 1
    assert "BatiConnect" in result["html_payload"]
    assert "Rue du Test 42" in result["html_payload"]


@pytest.mark.asyncio
async def test_generate_report_not_found(db, admin_user):
    """Returns None for non-existent building."""
    result = await generate_authority_report(db, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_generate_report_no_diagnostics(db, admin_user):
    """Report works with a building that has no diagnostics."""
    building = await _create_building(db, admin_user)
    await db.commit()

    result = await generate_authority_report(db, building.id)

    assert result is not None
    assert result["status"] == "generated"
    assert result["metadata"]["diagnostics_count"] == 0
    assert result["metadata"]["samples_count"] == 0
    assert "Aucun diagnostic" in result["html_payload"]


@pytest.mark.asyncio
async def test_generate_report_no_photos(db, admin_user):
    """Report respects include_photos=False."""
    building = await _create_building(db, admin_user)
    await db.commit()

    result = await generate_authority_report(db, building.id, include_photos=False)

    assert result is not None
    assert result["include_photos"] is False


@pytest.mark.asyncio
async def test_generate_report_multiple_diagnostics(db, admin_user):
    """Report handles multiple diagnostics with different types."""
    building = await _create_building(db, admin_user)
    diag1 = await _create_diagnostic(db, building.id, diagnostic_type="asbestos")
    diag2 = await _create_diagnostic(db, building.id, diagnostic_type="pcb")
    await _create_sample(db, diag1.id, pollutant_type="asbestos")
    await _create_sample(db, diag2.id, pollutant_type="pcb")
    await db.commit()

    result = await generate_authority_report(db, building.id)

    assert result is not None
    assert result["metadata"]["diagnostics_count"] == 2
    assert result["metadata"]["samples_count"] == 2


@pytest.mark.asyncio
async def test_generate_report_contains_all_sections(db, admin_user):
    """HTML payload contains all major section headings."""
    building = await _create_building(db, admin_user)
    await _create_risk_score(db, building.id)
    await db.commit()

    result = await generate_authority_report(db, building.id)
    html = result["html_payload"]

    assert "Resume executif" in html
    assert "Diagnostics polluants" in html
    assert "conformite" in html.lower()
    assert "Recommandations" in html
    assert "interventions" in html.lower()
    assert "Preuves" in html
    assert "Annexes" in html


@pytest.mark.asyncio
async def test_generate_report_sha256_changes(db, admin_user):
    """Different data produces different SHA-256 hashes."""
    building = await _create_building(db, admin_user)
    await db.commit()

    result1 = await generate_authority_report(db, building.id)

    # Add data
    await _create_risk_score(db, building.id)
    await db.commit()

    result2 = await generate_authority_report(db, building.id)

    assert result1["sha256"] != result2["sha256"]


@pytest.mark.asyncio
async def test_generate_report_legal_metadata(db, admin_user):
    """Report contains legal metadata and disclaimer."""
    building = await _create_building(db, admin_user)
    await db.commit()

    result = await generate_authority_report(db, building.id)
    html = result["html_payload"]

    assert "BatiConnect" in html
    assert "Batiscan Sarl" in html
    assert "verification professionnelle" in html.lower()
    assert result["metadata"]["disclaimer"]
    assert result["metadata"]["emitter"] == "BatiConnect — Batiscan Sarl"


# ---------------------------------------------------------------------------
# Tests — Template rendering
# ---------------------------------------------------------------------------


def test_render_css():
    """CSS is non-empty and contains key styles."""
    css = render_report_css()
    assert len(css) > 500
    assert "@page" in css
    assert "A4" in css


def test_render_cover_page():
    from datetime import datetime

    identity = {
        "address": "Rue Test 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "egid": "12345",
        "egrid": "CH-VD-12345",
        "construction_year": 1970,
        "building_type": "residential",
        "surface_area_m2": 300,
    }
    html = render_cover_page(identity, datetime(2026, 4, 1, tzinfo=UTC))
    assert "Rue Test 1" in html
    assert "12345" in html
    assert "BatiConnect" in html
    assert "cover" in html


def test_render_toc():
    html = render_toc()
    assert "Table des matieres" in html
    assert "Resume executif" in html
    assert "Annexes" in html


def test_render_executive_summary_no_data():
    html = render_executive_summary(
        identity={"address": "Test", "postal_code": "", "city": "", "egid": "", "egrid": "", "construction_year": None},
        pollutant_risks=[],
        risk_obj=None,
        trust_score=0,
        completeness_pct=0,
        diagnostics=[],
        actions=[],
    )
    assert "Resume executif" in html
    assert "Aucune donnee" in html


def test_render_diagnostics_section_empty():
    html = render_diagnostics_section(diagnostics=[], samples=[], pollutant_risks=[])
    assert "Diagnostics polluants" in html
    assert "Aucun diagnostic" in html


def test_render_compliance_section_empty():
    html = render_compliance_section(compliance_artefacts=[], zones=[])
    assert "conformite" in html.lower()
    assert "Conforme" in html


def test_render_recommendations_section_empty():
    html = render_recommendations_section(actions=[], pollutant_risks=[])
    assert "Recommandations" in html


def test_render_action_plan_section_empty():
    html = render_action_plan_section(interventions=[])
    assert "interventions" in html.lower()
    assert "Aucune intervention" in html


def test_render_evidence_section_empty():
    html = render_evidence_section(documents=[])
    assert "Preuves" in html
    assert "Aucun document" in html


def test_render_appendix_section():
    from datetime import datetime

    identity = {"egid": "12345", "canton": "VD"}
    html = render_appendix_section(identity=identity, now=datetime(2026, 4, 1, tzinfo=UTC), version="1.0.0")
    assert "Annexes" in html
    assert "Amiante" in html
    assert "OTConst" in html
    assert "EGID" in html
    assert "Glossaire" in html
    assert "1.0.0" in html
