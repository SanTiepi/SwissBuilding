"""Tests for eco clause API module and service integration.

Note: The eco_clauses router is not yet wired into router.py (supervisor merge).
These tests validate the service function directly.
"""

import uuid

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.services.eco_clause_template_service import generate_eco_clauses

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_building(db_session, *, created_by):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Eco API 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        created_by=created_by,
        status="active",
    )
    db_session.add(b)
    return b


def _make_diagnostic_with_samples(db_session, building_id, diagnostician_id, *, pollutants=None):
    pollutants = pollutants or ["asbestos"]
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type="asbestos",
        diagnostic_context="AvT",
        status="completed",
        diagnostician_id=diagnostician_id,
    )
    db_session.add(diag)
    for p in pollutants:
        sample = Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number=f"S-{p[:3].upper()}-01",
            pollutant_type=p,
            concentration=50.0,
            unit="mg_per_kg",
            threshold_exceeded=True,
            location_detail=f"Test {p}",
        )
        db_session.add(sample)
    return diag


# ---------------------------------------------------------------------------
# Tests — service-level (router wiring is supervisor-only)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_eco_clauses_renovation_with_pollutants(db_session, admin_user):
    building = _make_building(db_session, created_by=admin_user.id)
    _make_diagnostic_with_samples(db_session, building.id, admin_user.id, pollutants=["asbestos", "pcb"])
    await db_session.commit()

    payload = await generate_eco_clauses(building.id, "renovation", db_session)
    assert payload.building_id == building.id
    assert payload.context == "renovation"
    assert payload.total_clauses > 0
    assert "asbestos" in payload.detected_pollutants
    assert "pcb" in payload.detected_pollutants

    section_ids = [s.section_id for s in payload.sections]
    assert "SEC-GEN" in section_ids
    assert "SEC-AMI" in section_ids
    assert "SEC-PCB" in section_ids
    assert "SEC-REN" in section_ids


@pytest.mark.asyncio
async def test_eco_clauses_demolition_context(db_session, admin_user):
    building = _make_building(db_session, created_by=admin_user.id)
    _make_diagnostic_with_samples(db_session, building.id, admin_user.id, pollutants=["asbestos"])
    await db_session.commit()

    payload = await generate_eco_clauses(building.id, "demolition", db_session)
    assert payload.context == "demolition"
    section_ids = [s.section_id for s in payload.sections]
    assert "SEC-DEM" in section_ids
    assert "SEC-REN" not in section_ids


@pytest.mark.asyncio
async def test_eco_clauses_no_pollutants(db_session, admin_user):
    building = _make_building(db_session, created_by=admin_user.id)
    await db_session.commit()

    payload = await generate_eco_clauses(building.id, "renovation", db_session)
    assert payload.detected_pollutants == []
    assert payload.total_clauses >= 2  # GEN-01 + GEN-02 at minimum


@pytest.mark.asyncio
async def test_eco_clauses_invalid_context(db_session, admin_user):
    building = _make_building(db_session, created_by=admin_user.id)
    await db_session.commit()

    with pytest.raises(ValueError, match="Invalid context"):
        await generate_eco_clauses(building.id, "invalid", db_session)


@pytest.mark.asyncio
async def test_eco_clauses_building_not_found(db_session):
    fake_id = uuid.uuid4()
    with pytest.raises(ValueError, match="Building not found"):
        await generate_eco_clauses(fake_id, "renovation", db_session)


@pytest.mark.asyncio
async def test_eco_clauses_clause_structure(db_session, admin_user):
    building = _make_building(db_session, created_by=admin_user.id)
    _make_diagnostic_with_samples(db_session, building.id, admin_user.id, pollutants=["lead"])
    await db_session.commit()

    payload = await generate_eco_clauses(building.id, "renovation", db_session)
    for section in payload.sections:
        assert section.section_id
        assert section.title
        for clause in section.clauses:
            assert clause.clause_id
            assert clause.title
            assert clause.body
            assert isinstance(clause.legal_references, list)
            assert isinstance(clause.pollutants, list)
            assert clause.applicability


@pytest.mark.asyncio
async def test_eco_clauses_all_five_pollutants(db_session, admin_user):
    building = _make_building(db_session, created_by=admin_user.id)
    _make_diagnostic_with_samples(
        db_session,
        building.id,
        admin_user.id,
        pollutants=["asbestos", "pcb", "lead", "hap", "radon"],
    )
    await db_session.commit()

    payload = await generate_eco_clauses(building.id, "renovation", db_session)
    assert len(payload.detected_pollutants) == 5
    section_ids = [s.section_id for s in payload.sections]
    assert "SEC-AMI" in section_ids
    assert "SEC-PCB" in section_ids
    assert "SEC-PB" in section_ids
    assert "SEC-HAP" in section_ids
    assert "SEC-RN" in section_ids


@pytest.mark.asyncio
async def test_eco_clauses_deterministic(db_session, admin_user):
    """Same input produces identical sections (minus generated_at)."""
    building = _make_building(db_session, created_by=admin_user.id)
    _make_diagnostic_with_samples(db_session, building.id, admin_user.id, pollutants=["asbestos"])
    await db_session.commit()

    p1 = await generate_eco_clauses(building.id, "renovation", db_session)
    p2 = await generate_eco_clauses(building.id, "renovation", db_session)
    assert p1.total_clauses == p2.total_clauses
    assert p1.detected_pollutants == p2.detected_pollutants
    assert len(p1.sections) == len(p2.sections)
    for s1, s2 in zip(p1.sections, p2.sections, strict=True):
        assert s1.section_id == s2.section_id


@pytest.mark.asyncio
async def test_eco_clause_api_module_imports():
    """Verify the API module imports and has a router."""
    from app.api.eco_clauses import router

    assert router is not None
    routes = [r.path for r in router.routes]
    assert "/buildings/{building_id}/eco-clauses" in routes
