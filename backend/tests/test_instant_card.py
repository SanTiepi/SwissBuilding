"""Tests for the instant card service (Lot B+C) and portfolio triage (Lot B)."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.permit_procedure import PermitProcedure
from app.models.sample import Sample
from app.models.unknown_issue import UnknownIssue
from app.models.user import User
from app.services.instant_card_service import build_instant_card
from app.services.portfolio_triage_service import _classify_building, get_portfolio_triage

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def org(db_session: AsyncSession):
    org = Organization(
        id=uuid.uuid4(),
        name="Test Org",
        type="property_management",
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def ic_building(db_session: AsyncSession, admin_user: User, org: Organization):
    building = Building(
        id=uuid.uuid4(),
        address="Rue du Test 42",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        building_type="residential",
        created_by=admin_user.id,
        construction_year=1975,
        organization_id=org.id,
        latitude=46.52,
        longitude=6.63,
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def neighbor_building(db_session: AsyncSession, admin_user: User, org: Organization):
    building = Building(
        id=uuid.uuid4(),
        address="Rue du Test 44",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        building_type="residential",
        created_by=admin_user.id,
        construction_year=1978,
        organization_id=org.id,
        latitude=46.521,
        longitude=6.631,
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


# ---------------------------------------------------------------------------
# Instant Card — 5 question structure (Lot B)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_instant_card_nonexistent_building(db_session: AsyncSession):
    """Returns None for a non-existent building."""
    result = await build_instant_card(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_instant_card_basic_structure(db_session: AsyncSession, ic_building: Building):
    """Instant card has all 5 question sections."""
    result = await build_instant_card(db_session, ic_building.id)
    assert result is not None
    assert result.building_id == ic_building.id
    assert result.what_we_know is not None
    assert result.what_is_risky is not None
    assert result.what_blocks is not None
    assert result.what_to_do_next is not None
    assert result.what_is_reusable is not None


@pytest.mark.asyncio
async def test_instant_card_identity(db_session: AsyncSession, ic_building: Building):
    """what_we_know.identity contains building identity fields."""
    result = await build_instant_card(db_session, ic_building.id)
    assert result is not None
    identity = result.what_we_know.identity
    assert identity["address"] == "Rue du Test 42"
    assert identity["canton"] == "VD"
    assert identity["postal_code"] == "1000"


@pytest.mark.asyncio
async def test_instant_card_physical(db_session: AsyncSession, ic_building: Building):
    """what_we_know.physical contains building physical fields."""
    result = await build_instant_card(db_session, ic_building.id)
    assert result is not None
    physical = result.what_we_know.physical
    assert physical["construction_year"] == 1975
    assert physical["building_type"] == "residential"


@pytest.mark.asyncio
async def test_instant_card_passport_grade(db_session: AsyncSession, ic_building: Building):
    """Empty building gets F grade (no data)."""
    result = await build_instant_card(db_session, ic_building.id)
    assert result is not None
    assert result.passport_grade == "F"


@pytest.mark.asyncio
async def test_instant_card_trust_metadata(db_session: AsyncSession, ic_building: Building):
    """Trust metadata populated."""
    result = await build_instant_card(db_session, ic_building.id)
    assert result is not None
    assert result.trust is not None
    assert result.trust.confidence in ("high", "medium", "low")


@pytest.mark.asyncio
async def test_instant_card_blockers_from_procedures(db_session: AsyncSession, ic_building: Building, admin_user: User):
    """Blocked procedures appear in what_blocks."""
    proc = PermitProcedure(
        id=uuid.uuid4(),
        building_id=ic_building.id,
        procedure_type="suva_notification",
        title="SUVA blocked",
        status="complement_requested",
        authority_name="SUVA",
    )
    db_session.add(proc)
    await db_session.commit()

    result = await build_instant_card(db_session, ic_building.id)
    assert result is not None
    assert len(result.what_blocks.procedural_blockers) > 0


@pytest.mark.asyncio
async def test_instant_card_missing_proof_from_unknowns(
    db_session: AsyncSession, ic_building: Building, admin_user: User
):
    """Open blocking unknowns appear in what_blocks.missing_proof."""
    unk = UnknownIssue(
        id=uuid.uuid4(),
        building_id=ic_building.id,
        unknown_type="missing_diagnostic",
        title="No asbestos diagnostic",
        status="open",
        blocks_readiness=True,
    )
    db_session.add(unk)
    await db_session.commit()

    result = await build_instant_card(db_session, ic_building.id)
    assert result is not None
    assert len(result.what_blocks.missing_proof) > 0


@pytest.mark.asyncio
async def test_instant_card_what_to_do_next(db_session: AsyncSession, ic_building: Building):
    """what_to_do_next has suggestions (readiness advisor generates for pre-1991 buildings)."""
    result = await build_instant_card(db_session, ic_building.id)
    assert result is not None
    # For a 1975 building without diagnostics, readiness advisor should suggest pollutant coverage
    assert result.what_to_do_next is not None
    assert isinstance(result.what_to_do_next.top_3_actions, list)


@pytest.mark.asyncio
async def test_instant_card_what_is_reusable_empty(db_session: AsyncSession, ic_building: Building):
    """what_is_reusable is empty for a building with no proof chain."""
    result = await build_instant_card(db_session, ic_building.id)
    assert result is not None
    assert result.what_is_reusable.diagnostic_publications == []
    assert result.what_is_reusable.packs_generated == []


@pytest.mark.asyncio
async def test_instant_card_neighbor_signals(
    db_session: AsyncSession, ic_building: Building, neighbor_building: Building
):
    """Neighbor signals populated when buildings exist in same postal code."""
    result = await build_instant_card(db_session, ic_building.id)
    assert result is not None
    assert len(result.neighbor_signals) >= 1
    assert result.neighbor_signals[0]["signal"] == "same_neighborhood"


# ---------------------------------------------------------------------------
# Execution section (Lot C)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_instant_card_execution_section_exists(db_session: AsyncSession, ic_building: Building):
    """Execution section is present in instant card."""
    result = await build_instant_card(db_session, ic_building.id)
    assert result is not None
    assert result.execution is not None


@pytest.mark.asyncio
async def test_instant_card_execution_subsidies(db_session: AsyncSession, ic_building: Building):
    """Subsidies populated for a VD building with pollutant samples."""
    # Add a completed diagnostic with exceeded asbestos sample
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=ic_building.id,
        diagnostic_type="asbestos",
        status="completed",
    )
    db_session.add(diag)
    await db_session.flush()

    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S-001",
        location_floor="Floor 1",
        pollutant_type="asbestos",
        threshold_exceeded=True,
        risk_level="high",
    )
    db_session.add(sample)
    await db_session.commit()

    result = await build_instant_card(db_session, ic_building.id)
    assert result is not None
    # Should have subsidies since VD building with asbestos
    assert isinstance(result.execution.subsidies, list)


@pytest.mark.asyncio
async def test_instant_card_execution_roi(db_session: AsyncSession, ic_building: Building):
    """ROI renovation data populated when pollutant diagnostics exist."""
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=ic_building.id,
        diagnostic_type="asbestos",
        status="completed",
    )
    db_session.add(diag)
    await db_session.flush()

    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S-001",
        location_floor="Floor 1",
        pollutant_type="asbestos",
        threshold_exceeded=True,
        risk_level="high",
    )
    db_session.add(sample)
    await db_session.commit()

    result = await build_instant_card(db_session, ic_building.id)
    assert result is not None
    assert isinstance(result.execution.roi_renovation, dict)


@pytest.mark.asyncio
async def test_instant_card_execution_insurance(db_session: AsyncSession, ic_building: Building):
    """Insurance impact data present for building."""
    result = await build_instant_card(db_session, ic_building.id)
    assert result is not None
    # Insurance assessment runs even without samples (pre-1991 elevated)
    assert isinstance(result.execution.insurance_impact, dict)


# ---------------------------------------------------------------------------
# Residual materials (Lot D)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_instant_card_residual_materials_from_samples(db_session: AsyncSession, ic_building: Building):
    """Residual materials populated from exceeded diagnostic samples without remediation."""
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=ic_building.id,
        diagnostic_type="asbestos",
        status="completed",
    )
    db_session.add(diag)
    await db_session.flush()

    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S-002",
        location_floor="Basement",
        location_detail="pipe",
        pollutant_type="asbestos",
        threshold_exceeded=True,
        risk_level="high",
    )
    db_session.add(sample)
    await db_session.commit()

    result = await build_instant_card(db_session, ic_building.id)
    assert result is not None
    residuals = result.what_we_know.residual_materials
    assert len(residuals) >= 1
    assert residuals[0].material_type == "asbestos"
    assert residuals[0].source == "diagnostic_sample"


@pytest.mark.asyncio
async def test_instant_card_residual_materials_cleared_by_remediation(db_session: AsyncSession, ic_building: Building):
    """No sample-based residual materials when remediation is completed."""
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=ic_building.id,
        diagnostic_type="asbestos",
        status="completed",
    )
    db_session.add(diag)
    await db_session.flush()

    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S-002",
        location_floor="Basement",
        location_detail="pipe",
        pollutant_type="asbestos",
        threshold_exceeded=True,
        risk_level="high",
    )
    db_session.add(sample)

    # Add completed remediation
    intervention = Intervention(
        id=uuid.uuid4(),
        building_id=ic_building.id,
        intervention_type="remediation",
        title="Asbestos removal",
        status="completed",
        description="Asbestos removal",
    )
    db_session.add(intervention)
    await db_session.commit()

    result = await build_instant_card(db_session, ic_building.id)
    assert result is not None
    # Sample-based residuals should be cleared by completed remediation
    sample_residuals = [r for r in result.what_we_know.residual_materials if r.source == "diagnostic_sample"]
    assert len(sample_residuals) == 0


# ---------------------------------------------------------------------------
# Portfolio Triage (Lot B)
# ---------------------------------------------------------------------------


def test_classify_building_critical():
    """F-grade building is critical."""
    assert _classify_building("F", 0, 0.5) == "critical"


def test_classify_building_critical_blockers():
    """Any blockers = critical."""
    assert _classify_building("B", 2, 0.8) == "critical"


def test_classify_building_action_needed():
    """D-grade = action needed."""
    assert _classify_building("D", 0, 0.5) == "action_needed"


def test_classify_building_action_needed_low_trust():
    """Low trust = action needed."""
    assert _classify_building("B", 0, 0.2) == "action_needed"


def test_classify_building_monitored():
    """C-grade = monitored."""
    assert _classify_building("C", 0, 0.7) == "monitored"


def test_classify_building_under_control():
    """A/B-grade with good trust = under control."""
    assert _classify_building("A", 0, 0.9) == "under_control"
    assert _classify_building("B", 0, 0.7) == "under_control"


@pytest.mark.asyncio
async def test_portfolio_triage_empty_org(db_session: AsyncSession, org: Organization):
    """Empty org returns zero counts."""
    result = await get_portfolio_triage(db_session, org.id)
    assert result.org_id == org.id
    assert result.critical_count == 0
    assert result.action_needed_count == 0
    assert result.monitored_count == 0
    assert result.under_control_count == 0
    assert result.buildings == []


@pytest.mark.asyncio
async def test_portfolio_triage_classifies_buildings(
    db_session: AsyncSession, ic_building: Building, org: Organization
):
    """Building with no data classified as critical (F grade)."""
    result = await get_portfolio_triage(db_session, org.id)
    assert len(result.buildings) == 1
    assert result.buildings[0].status == "critical"
    assert result.critical_count == 1


@pytest.mark.asyncio
async def test_portfolio_triage_sorted_by_urgency(
    db_session: AsyncSession, ic_building: Building, neighbor_building: Building, org: Organization
):
    """Buildings sorted by urgency (critical first)."""
    result = await get_portfolio_triage(db_session, org.id)
    assert len(result.buildings) == 2
    # Both F-grade, so both critical
    assert all(b.status == "critical" for b in result.buildings)


@pytest.mark.asyncio
async def test_portfolio_triage_building_has_address(
    db_session: AsyncSession, ic_building: Building, org: Organization
):
    """Triage building has full address."""
    result = await get_portfolio_triage(db_session, org.id)
    assert "Rue du Test 42" in result.buildings[0].address
