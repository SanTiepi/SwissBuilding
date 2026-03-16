"""Tests for the unknown_generator service."""

from __future__ import annotations

import uuid
from datetime import date

import pytest

from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.material import Material
from app.models.sample import Sample
from app.models.technical_plan import TechnicalPlan
from app.models.unknown_issue import UnknownIssue
from app.models.zone import Zone
from app.services.unknown_generator import generate_unknowns

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_building(db, admin_user, construction_year=1970):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=construction_year,
        building_type="residential",
        created_by=admin_user.id,
        owner_id=admin_user.id,
        status="active",
    )
    db.add(b)
    await db.flush()
    return b


async def _create_diagnostic(db, building, *, status="completed"):
    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="asbestos",
        status=status,
        date_inspection=date(2025, 1, 15),
    )
    db.add(d)
    await db.flush()
    return d


async def _create_sample(
    db,
    diagnostic,
    *,
    pollutant_type="asbestos",
    concentration=500.0,
    unit="mg/kg",
):
    s = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic.id,
        sample_number=f"S-{uuid.uuid4().hex[:6]}",
        pollutant_type=pollutant_type,
        concentration=concentration,
        unit=unit,
    )
    db.add(s)
    await db.flush()
    return s


async def _create_zone(db, building, admin_user, *, name="Rez-de-chaussée"):
    z = Zone(
        id=uuid.uuid4(),
        building_id=building.id,
        zone_type="floor",
        name=name,
        created_by=admin_user.id,
    )
    db.add(z)
    await db.flush()
    return z


async def _create_element(db, zone, admin_user, *, name="Mur salon"):
    e = BuildingElement(
        id=uuid.uuid4(),
        zone_id=zone.id,
        element_type="wall",
        name=name,
        created_by=admin_user.id,
    )
    db.add(e)
    await db.flush()
    return e


async def _create_material(db, element, admin_user, *, contains_pollutant=None):
    m = Material(
        id=uuid.uuid4(),
        element_id=element.id,
        material_type="coating",
        name="Enduit",
        contains_pollutant=contains_pollutant,
        created_by=admin_user.id,
    )
    db.add(m)
    await db.flush()
    return m


async def _create_plan(db, building, admin_user, *, plan_type="floor_plan"):
    p = TechnicalPlan(
        id=uuid.uuid4(),
        building_id=building.id,
        plan_type=plan_type,
        title="Plan RDC",
        file_path="/plans/rdc.pdf",
        file_name="rdc.pdf",
        uploaded_by=admin_user.id,
    )
    db.add(p)
    await db.flush()
    return p


async def _create_intervention(db, building, admin_user, *, status="completed"):
    i = Intervention(
        id=uuid.uuid4(),
        building_id=building.id,
        intervention_type="remediation",
        title="Désamiantage façade",
        status=status,
        created_by=admin_user.id,
    )
    db.add(i)
    await db.flush()
    return i


async def _create_document(db, building, admin_user):
    d = Document(
        id=uuid.uuid4(),
        building_id=building.id,
        file_path="/docs/report.pdf",
        file_name="report.pdf",
        document_type="report",
        uploaded_by=admin_user.id,
    )
    db.add(d)
    await db.flush()
    return d


def _types(issues: list[UnknownIssue]) -> list[str]:
    return sorted(i.unknown_type for i in issues)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_building_no_unknowns(db_session, admin_user):
    """Pre-1991 building with no data generates missing_diagnostic + pollutant unknowns."""
    building = await _create_building(db_session, admin_user, construction_year=1970)
    issues = await generate_unknowns(db_session, building.id)

    types = _types(issues)
    assert "missing_diagnostic" in types
    # 1970 → asbestos (pre-1990), pcb (1955-1975), lead (pre-2006), hap, radon
    pollutant_issues = [i for i in issues if i.unknown_type == "missing_pollutant_evaluation"]
    pollutant_titles = sorted(i.title for i in pollutant_issues)
    assert len(pollutant_issues) == 5
    assert "Missing asbestos evaluation" in pollutant_titles
    assert "Missing radon evaluation" in pollutant_titles


@pytest.mark.asyncio
async def test_modern_building_fewer_unknowns(db_session, admin_user):
    """Post-2006 building → no asbestos/pcb/lead unknowns, only hap+radon."""
    building = await _create_building(db_session, admin_user, construction_year=2010)
    issues = await generate_unknowns(db_session, building.id)

    types = _types(issues)
    # 2010 → no missing_diagnostic (post-1991), no asbestos/pcb/lead
    assert "missing_diagnostic" not in types
    pollutant_issues = [i for i in issues if i.unknown_type == "missing_pollutant_evaluation"]
    pollutant_names = {i.title for i in pollutant_issues}
    assert "Missing asbestos evaluation" not in pollutant_names
    assert "Missing pcb evaluation" not in pollutant_names
    assert "Missing lead evaluation" not in pollutant_names
    # hap and radon are always applicable
    assert "Missing hap evaluation" in pollutant_names
    assert "Missing radon evaluation" in pollutant_names


@pytest.mark.asyncio
async def test_missing_diagnostic_detected(db_session, admin_user):
    """Pre-1991 building without completed diagnostic → missing_diagnostic."""
    building = await _create_building(db_session, admin_user, construction_year=1985)
    issues = await generate_unknowns(db_session, building.id)

    diag_issues = [i for i in issues if i.unknown_type == "missing_diagnostic"]
    assert len(diag_issues) == 1
    assert diag_issues[0].severity == "high"
    assert diag_issues[0].blocks_readiness is True


@pytest.mark.asyncio
async def test_missing_diagnostic_resolved_when_diagnosed(db_session, admin_user):
    """Run generator, add diagnostic, run again → unknown auto-resolved."""
    building = await _create_building(db_session, admin_user, construction_year=1980)

    # First run: generates missing_diagnostic
    issues1 = await generate_unknowns(db_session, building.id)
    diag_issues = [i for i in issues1 if i.unknown_type == "missing_diagnostic"]
    assert len(diag_issues) == 1
    assert diag_issues[0].status == "open"

    # Add a completed diagnostic
    await _create_diagnostic(db_session, building, status="completed")

    # Second run: should auto-resolve
    await generate_unknowns(db_session, building.id)
    await db_session.refresh(diag_issues[0])
    assert diag_issues[0].status == "resolved"
    assert diag_issues[0].resolution_notes == "Auto-resolved: gap no longer detected"


@pytest.mark.asyncio
async def test_uninspected_zone(db_session, admin_user):
    """Building with zones but no elements → uninspected_zone."""
    building = await _create_building(db_session, admin_user, construction_year=2010)
    await _create_zone(db_session, building, admin_user, name="Sous-sol")

    issues = await generate_unknowns(db_session, building.id)
    zone_issues = [i for i in issues if i.unknown_type == "uninspected_zone"]
    assert len(zone_issues) == 1
    assert zone_issues[0].severity == "medium"
    assert "Sous-sol" in zone_issues[0].title


@pytest.mark.asyncio
async def test_missing_lab_results(db_session, admin_user):
    """Sample without concentration → missing_lab_results."""
    building = await _create_building(db_session, admin_user, construction_year=2010)
    diag = await _create_diagnostic(db_session, building)
    await _create_sample(db_session, diag, concentration=None, unit=None)

    issues = await generate_unknowns(db_session, building.id)
    lab_issues = [i for i in issues if i.unknown_type == "missing_lab_results"]
    assert len(lab_issues) == 1
    assert lab_issues[0].severity == "high"
    assert lab_issues[0].blocks_readiness is True


@pytest.mark.asyncio
async def test_idempotent_generation(db_session, admin_user):
    """Running generator twice produces no duplicates."""
    building = await _create_building(db_session, admin_user, construction_year=1970)

    issues1 = await generate_unknowns(db_session, building.id)
    count1 = len(issues1)
    assert count1 > 0

    issues2 = await generate_unknowns(db_session, building.id)
    assert len(issues2) == 0  # no new issues created


@pytest.mark.asyncio
async def test_missing_plan_detected(db_session, admin_user):
    """Building with zones but no floor_plan → missing_plan."""
    building = await _create_building(db_session, admin_user, construction_year=2010)
    await _create_zone(db_session, building, admin_user)

    issues = await generate_unknowns(db_session, building.id)
    plan_issues = [i for i in issues if i.unknown_type == "missing_plan"]
    assert len(plan_issues) == 1
    assert plan_issues[0].severity == "low"

    # Add a floor plan and re-run
    await _create_plan(db_session, building, admin_user, plan_type="floor_plan")
    await generate_unknowns(db_session, building.id)
    await db_session.refresh(plan_issues[0])
    assert plan_issues[0].status == "resolved"


@pytest.mark.asyncio
async def test_undocumented_intervention(db_session, admin_user):
    """Completed intervention with no documents → undocumented_intervention."""
    building = await _create_building(db_session, admin_user, construction_year=2010)
    await _create_intervention(db_session, building, admin_user, status="completed")

    issues = await generate_unknowns(db_session, building.id)
    interv_issues = [i for i in issues if i.unknown_type == "undocumented_intervention"]
    assert len(interv_issues) == 1
    assert interv_issues[0].severity == "medium"
    assert "Désamiantage" in interv_issues[0].title
