"""Tests for eco clause integration into contractor acknowledgment and transfer package."""

import uuid

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.schemas.contractor_acknowledgment import ContractorAcknowledgmentCreate
from app.services.contractor_acknowledgment_service import create_acknowledgment
from app.services.transfer_package_service import generate_transfer_package

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAFETY_REQS = [
    {"item": "Full-face respirator required", "category": "PPE"},
]


def _make_building(db_session, *, created_by):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Eco 5",
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
    """Create a diagnostic with threshold-exceeding samples for given pollutants."""
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
            risk_level="high",
        )
        db_session.add(sample)
    return diag


def _make_intervention(db_session, building_id):
    i = Intervention(
        id=uuid.uuid4(),
        building_id=building_id,
        intervention_type="asbestos_removal",
        title="Remove asbestos insulation",
        status="planned",
    )
    db_session.add(i)
    return i


# ---------------------------------------------------------------------------
# Contractor acknowledgment - eco clause enrichment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ack_includes_eco_clauses_when_pollutants_present(db_session, admin_user):
    """Eco clauses are injected into safety_requirements when building has pollutant samples."""
    building = _make_building(db_session, created_by=admin_user.id)
    _make_diagnostic_with_samples(db_session, building.id, admin_user.id, pollutants=["asbestos"])
    intervention = _make_intervention(db_session, building.id)
    await db_session.commit()

    data = ContractorAcknowledgmentCreate(
        intervention_id=intervention.id,
        contractor_user_id=admin_user.id,
        safety_requirements=_SAFETY_REQS,
    )
    ack = await create_acknowledgment(db_session, building.id, data, admin_user.id)
    await db_session.commit()

    # safety_requirements should be wrapped in a dict with eco_clauses
    assert isinstance(ack.safety_requirements, dict)
    assert "eco_clauses" in ack.safety_requirements
    eco = ack.safety_requirements["eco_clauses"]
    assert eco["total_clauses"] > 0
    assert "asbestos" in eco["detected_pollutants"]
    # Original items preserved
    assert "items" in ack.safety_requirements
    assert len(ack.safety_requirements["items"]) == len(_SAFETY_REQS)


@pytest.mark.asyncio
async def test_ack_no_eco_clauses_without_pollutants(db_session, admin_user):
    """No eco clauses when building has no threshold-exceeding samples."""
    building = _make_building(db_session, created_by=admin_user.id)
    intervention = _make_intervention(db_session, building.id)
    await db_session.commit()

    data = ContractorAcknowledgmentCreate(
        intervention_id=intervention.id,
        contractor_user_id=admin_user.id,
        safety_requirements=_SAFETY_REQS,
    )
    ack = await create_acknowledgment(db_session, building.id, data, admin_user.id)
    await db_session.commit()

    # safety_requirements should remain as original list (no eco clauses to add)
    assert isinstance(ack.safety_requirements, list)
    assert len(ack.safety_requirements) == len(_SAFETY_REQS)


@pytest.mark.asyncio
async def test_ack_eco_clauses_multiple_pollutants(db_session, admin_user):
    """Eco clauses cover multiple pollutant types."""
    building = _make_building(db_session, created_by=admin_user.id)
    _make_diagnostic_with_samples(db_session, building.id, admin_user.id, pollutants=["asbestos", "pcb", "lead"])
    intervention = _make_intervention(db_session, building.id)
    await db_session.commit()

    data = ContractorAcknowledgmentCreate(
        intervention_id=intervention.id,
        contractor_user_id=admin_user.id,
        safety_requirements=_SAFETY_REQS,
    )
    ack = await create_acknowledgment(db_session, building.id, data, admin_user.id)
    await db_session.commit()

    eco = ack.safety_requirements["eco_clauses"]
    detected = eco["detected_pollutants"]
    assert "asbestos" in detected
    assert "pcb" in detected
    assert "lead" in detected
    # Should have multiple sections (general + asbestos + pcb + lead + renovation)
    assert len(eco["sections"]) >= 4


@pytest.mark.asyncio
async def test_ack_eco_clauses_preserves_original_items(db_session, admin_user):
    """Original safety requirement items are preserved alongside eco clauses."""
    building = _make_building(db_session, created_by=admin_user.id)
    _make_diagnostic_with_samples(db_session, building.id, admin_user.id, pollutants=["asbestos"])
    intervention = _make_intervention(db_session, building.id)
    await db_session.commit()

    reqs = [
        {"item": "Helmet required", "category": "PPE"},
        {"item": "Gloves required", "category": "PPE"},
    ]
    data = ContractorAcknowledgmentCreate(
        intervention_id=intervention.id,
        contractor_user_id=admin_user.id,
        safety_requirements=reqs,
    )
    ack = await create_acknowledgment(db_session, building.id, data, admin_user.id)
    await db_session.commit()

    assert isinstance(ack.safety_requirements, dict)
    assert ack.safety_requirements["items"] == reqs
    assert "eco_clauses" in ack.safety_requirements
    # Eco clauses should have sections with clause details
    sections = ack.safety_requirements["eco_clauses"]["sections"]
    assert len(sections) > 0
    assert "clauses" in sections[0]


# ---------------------------------------------------------------------------
# Transfer package - eco clause section
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transfer_package_includes_eco_clauses(db_session, admin_user):
    """Transfer package includes eco_clauses section when pollutants are detected."""
    building = _make_building(db_session, created_by=admin_user.id)
    _make_diagnostic_with_samples(db_session, building.id, admin_user.id, pollutants=["asbestos", "pcb"])
    await db_session.commit()

    pkg = await generate_transfer_package(db_session, building.id, include_sections=["eco_clauses"])
    assert pkg is not None
    assert pkg.eco_clauses is not None
    assert pkg.eco_clauses["total_clauses"] > 0
    assert "asbestos" in pkg.eco_clauses["detected_pollutants"]
    assert "pcb" in pkg.eco_clauses["detected_pollutants"]
    assert pkg.eco_clauses["context"] == "renovation"


@pytest.mark.asyncio
async def test_transfer_package_no_eco_clauses_without_pollutants(db_session, admin_user):
    """Transfer package eco_clauses is None when no pollutants are detected."""
    building = _make_building(db_session, created_by=admin_user.id)
    await db_session.commit()

    pkg = await generate_transfer_package(db_session, building.id, include_sections=["eco_clauses"])
    assert pkg is not None
    assert pkg.eco_clauses is None


@pytest.mark.asyncio
async def test_transfer_package_eco_clauses_excluded_when_filtered(db_session, admin_user):
    """Eco clauses not included when not in include_sections."""
    building = _make_building(db_session, created_by=admin_user.id)
    _make_diagnostic_with_samples(db_session, building.id, admin_user.id, pollutants=["asbestos"])
    await db_session.commit()

    pkg = await generate_transfer_package(db_session, building.id, include_sections=["diagnostics"])
    assert pkg is not None
    assert pkg.eco_clauses is None


@pytest.mark.asyncio
async def test_transfer_package_full_includes_eco_clauses(db_session, admin_user):
    """Full transfer package (no section filter) includes eco_clauses when pollutants exist."""
    building = _make_building(db_session, created_by=admin_user.id)
    _make_diagnostic_with_samples(db_session, building.id, admin_user.id, pollutants=["asbestos"])
    await db_session.commit()

    pkg = await generate_transfer_package(db_session, building.id)
    assert pkg is not None
    assert pkg.eco_clauses is not None
    assert pkg.eco_clauses["total_clauses"] > 0
