"""Tests for the eco clause template service."""

from __future__ import annotations

import uuid

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.services.eco_clause_template_service import (
    EcoClausePayload,
    generate_eco_clauses,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def building_all_pollutants(db_session, admin_user):
    """Building with threshold-exceeding samples for all 5 pollutants."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue Polluants 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1960,
        building_type="residential",
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

    pollutants = [
        ("asbestos", 2.5, "percent_weight"),
        ("pcb", 120.0, "mg_per_kg"),
        ("lead", 8000.0, "mg_per_kg"),
        ("hap", 500.0, "mg_per_kg"),
        ("radon", 450.0, "bq_per_m3"),
    ]
    for i, (ptype, conc, unit) in enumerate(pollutants, 1):
        sample = Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number=f"S-{i:03d}",
            pollutant_type=ptype,
            concentration=conc,
            unit=unit,
            threshold_exceeded=True,
            risk_level="high",
        )
        db_session.add(sample)

    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def building_asbestos_only(db_session, admin_user):
    """Building with only asbestos detected."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue Amiante 5",
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
        sample_number="S-001",
        pollutant_type="asbestos",
        concentration=3.0,
        unit="percent_weight",
        threshold_exceeded=True,
        risk_level="high",
    )
    db_session.add(sample)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def building_no_pollutants(db_session, admin_user):
    """Building with no diagnostics / no pollutants detected."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue Propre 10",
        postal_code="1200",
        city="Geneve",
        canton="GE",
        construction_year=2015,
        building_type="commercial",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def building_below_threshold(db_session, admin_user):
    """Building with samples that do NOT exceed thresholds."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue Seuil 2",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1985,
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
        sample_number="S-001",
        pollutant_type="asbestos",
        concentration=0.05,
        unit="percent_weight",
        threshold_exceeded=False,
        risk_level="low",
    )
    db_session.add(sample)
    await db_session.commit()
    await db_session.refresh(building)
    return building


# ---------------------------------------------------------------------------
# Context type tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_renovation_context_returns_payload(db_session, building_asbestos_only):
    """Renovation context should return a valid EcoClausePayload."""
    result = await generate_eco_clauses(building_asbestos_only.id, "renovation", db_session)
    assert isinstance(result, EcoClausePayload)
    assert result.context == "renovation"
    assert result.building_id == building_asbestos_only.id
    assert result.total_clauses > 0
    section_ids = [s.section_id for s in result.sections]
    assert "SEC-GEN" in section_ids
    assert "SEC-AMI" in section_ids
    assert "SEC-REN" in section_ids


@pytest.mark.asyncio
async def test_demolition_context_returns_payload(db_session, building_asbestos_only):
    """Demolition context should return a valid EcoClausePayload."""
    result = await generate_eco_clauses(building_asbestos_only.id, "demolition", db_session)
    assert isinstance(result, EcoClausePayload)
    assert result.context == "demolition"
    section_ids = [s.section_id for s in result.sections]
    assert "SEC-GEN" in section_ids
    assert "SEC-AMI" in section_ids
    assert "SEC-DEM" in section_ids
    # Renovation section should NOT be present
    assert "SEC-REN" not in section_ids


@pytest.mark.asyncio
async def test_invalid_context_raises(db_session, building_asbestos_only):
    """Invalid context should raise ValueError."""
    with pytest.raises(ValueError, match="Invalid context"):
        await generate_eco_clauses(building_asbestos_only.id, "inspection", db_session)


# ---------------------------------------------------------------------------
# Determinism tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deterministic_output(db_session, building_all_pollutants):
    """Same input should produce the same clause structure."""
    r1 = await generate_eco_clauses(building_all_pollutants.id, "renovation", db_session)
    r2 = await generate_eco_clauses(building_all_pollutants.id, "renovation", db_session)

    assert r1.total_clauses == r2.total_clauses
    assert r1.detected_pollutants == r2.detected_pollutants
    assert len(r1.sections) == len(r2.sections)
    for s1, s2 in zip(r1.sections, r2.sections, strict=True):
        assert s1.section_id == s2.section_id
        assert len(s1.clauses) == len(s2.clauses)
        for c1, c2 in zip(s1.clauses, s2.clauses, strict=True):
            assert c1.clause_id == c2.clause_id
            assert c1.body == c2.body
            assert c1.legal_references == c2.legal_references


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_pollutants_still_returns_general_clauses(db_session, building_no_pollutants):
    """Building with no pollutants should still get general obligation clauses."""
    result = await generate_eco_clauses(building_no_pollutants.id, "renovation", db_session)
    assert result.total_clauses > 0
    assert result.detected_pollutants == []
    section_ids = [s.section_id for s in result.sections]
    assert "SEC-GEN" in section_ids
    assert "SEC-REN" in section_ids
    # Pollutant-specific sections should be absent
    assert "SEC-AMI" not in section_ids
    assert "SEC-PCB" not in section_ids
    assert "SEC-PB" not in section_ids
    assert "SEC-HAP" not in section_ids
    assert "SEC-RN" not in section_ids


@pytest.mark.asyncio
async def test_all_pollutants_present(db_session, building_all_pollutants):
    """Building with all 5 pollutants should have all pollutant sections."""
    result = await generate_eco_clauses(building_all_pollutants.id, "renovation", db_session)
    assert len(result.detected_pollutants) == 5
    section_ids = [s.section_id for s in result.sections]
    assert "SEC-AMI" in section_ids
    assert "SEC-PCB" in section_ids
    assert "SEC-PB" in section_ids
    assert "SEC-HAP" in section_ids
    assert "SEC-RN" in section_ids


@pytest.mark.asyncio
async def test_below_threshold_not_detected(db_session, building_below_threshold):
    """Samples below threshold should not trigger pollutant clauses."""
    result = await generate_eco_clauses(building_below_threshold.id, "renovation", db_session)
    assert result.detected_pollutants == []
    section_ids = [s.section_id for s in result.sections]
    assert "SEC-AMI" not in section_ids


@pytest.mark.asyncio
async def test_building_not_found_raises(db_session):
    """Nonexistent building should raise ValueError."""
    fake_id = uuid.uuid4()
    with pytest.raises(ValueError, match="Building not found"):
        await generate_eco_clauses(fake_id, "renovation", db_session)


# ---------------------------------------------------------------------------
# Provenance tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_provenance_includes_building_and_context(db_session, building_asbestos_only):
    """Provenance should contain building_id and context."""
    result = await generate_eco_clauses(building_asbestos_only.id, "renovation", db_session)
    assert any(f"building_id={building_asbestos_only.id}" in p for p in result.provenance)
    assert any("context=renovation" in p for p in result.provenance)


@pytest.mark.asyncio
async def test_provenance_includes_legal_refs(db_session, building_asbestos_only):
    """Provenance should reference legal bases."""
    result = await generate_eco_clauses(building_asbestos_only.id, "renovation", db_session)
    ref_entries = [p for p in result.provenance if p.startswith("ref=")]
    assert len(ref_entries) > 0
    # Asbestos building should reference OTConst
    assert any("OTConst" in p for p in ref_entries)


# ---------------------------------------------------------------------------
# Legal reference integrity
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_clauses_have_legal_references(db_session, building_all_pollutants):
    """Every clause must have at least one legal reference."""
    result = await generate_eco_clauses(building_all_pollutants.id, "renovation", db_session)
    for section in result.sections:
        for clause in section.clauses:
            assert len(clause.legal_references) > 0, f"Clause {clause.clause_id} has no legal references"


@pytest.mark.asyncio
async def test_clauses_have_nonempty_body(db_session, building_all_pollutants):
    """Every clause body must be non-empty."""
    result = await generate_eco_clauses(building_all_pollutants.id, "demolition", db_session)
    for section in result.sections:
        for clause in section.clauses:
            assert clause.body.strip(), f"Clause {clause.clause_id} has empty body"


@pytest.mark.asyncio
async def test_clause_ids_unique(db_session, building_all_pollutants):
    """All clause IDs within a payload must be unique."""
    result = await generate_eco_clauses(building_all_pollutants.id, "renovation", db_session)
    all_ids = [c.clause_id for s in result.sections for c in s.clauses]
    assert len(all_ids) == len(set(all_ids))


# ---------------------------------------------------------------------------
# Demolition with all pollutants (cross-check)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_demolition_all_pollutants(db_session, building_all_pollutants):
    """Demolition with all pollutants should include DEM section and all pollutant sections."""
    result = await generate_eco_clauses(building_all_pollutants.id, "demolition", db_session)
    section_ids = [s.section_id for s in result.sections]
    assert "SEC-DEM" in section_ids
    assert "SEC-AMI" in section_ids
    assert "SEC-PCB" in section_ids
    # Renovation section should NOT be present
    assert "SEC-REN" not in section_ids
