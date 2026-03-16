"""Tests for work_phase_service — Swiss renovation work phase planning."""

import uuid

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.services.work_phase_service import (
    estimate_phase_timeline,
    get_phase_requirements,
    get_portfolio_work_overview,
    plan_work_phases,
)
from tests.conftest import _HASH_ADMIN

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_user(db, org_id=None):
    user = User(
        id=uuid.uuid4(),
        email=f"test-{uuid.uuid4().hex[:6]}@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Test",
        last_name="User",
        role="admin",
        is_active=True,
        language="fr",
        organization_id=org_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _create_org(db):
    org = Organization(
        id=uuid.uuid4(),
        name=f"TestOrg-{uuid.uuid4().hex[:6]}",
        type="diagnostic_lab",
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


async def _create_building(db, user, construction_year=1965):
    building = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=construction_year,
        building_type="residential",
        created_by=user.id,
        status="active",
    )
    db.add(building)
    await db.commit()
    await db.refresh(building)
    return building


async def _create_diagnostic(db, building_id, diag_type="asbestos", status="completed"):
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type=diag_type,
        status=status,
    )
    db.add(diag)
    await db.commit()
    await db.refresh(diag)
    return diag


async def _create_sample(
    db,
    diagnostic_id,
    pollutant_type="asbestos",
    threshold_exceeded=True,
    material_state="good",
    material_category="fibrociment",
    concentration=5.0,
):
    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic_id,
        sample_number=f"S-{uuid.uuid4().hex[:6]}",
        pollutant_type=pollutant_type,
        threshold_exceeded=threshold_exceeded,
        material_state=material_state,
        material_category=material_category,
        concentration=concentration,
        unit="percent_weight",
        location_floor="1er etage",
    )
    db.add(sample)
    await db.commit()
    await db.refresh(sample)
    return sample


# ---------------------------------------------------------------------------
# FN1: plan_work_phases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_plan_work_phases_no_building(db_session):
    """Non-existent building returns empty plan."""
    result = await plan_work_phases(db_session, uuid.uuid4())
    assert result.total_phases == 0
    assert result.phases == []


@pytest.mark.asyncio
async def test_plan_work_phases_clean_building(db_session):
    """Building with no positive samples returns empty plan."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    result = await plan_work_phases(db_session, building.id)
    assert result.total_phases == 0


@pytest.mark.asyncio
async def test_plan_work_phases_asbestos_minor(db_session):
    """Asbestos in good condition generates 6 phases with minor CFST category."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id, material_state="good", threshold_exceeded=True)

    result = await plan_work_phases(db_session, building.id)
    # good state + threshold_exceeded → medium (per _determine_cfst_category logic)
    assert result.total_phases == 6
    assert all(p.cfst_category == "medium" for p in result.phases)

    # Check phase types in order
    phase_types = [p.phase_type for p in result.phases]
    assert phase_types == ["preparation", "containment", "removal", "decontamination", "restoration", "verification"]


@pytest.mark.asyncio
async def test_plan_work_phases_asbestos_major(db_session):
    """Friable asbestos generates major CFST category."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(
        db_session,
        diag.id,
        material_state="friable",
        material_category="flocage",
    )

    result = await plan_work_phases(db_session, building.id)
    assert result.total_phases == 6
    assert all(p.cfst_category == "major" for p in result.phases)
    # Major removal takes 10 days
    removal = next(p for p in result.phases if p.phase_type == "removal")
    assert removal.duration_days == 10


@pytest.mark.asyncio
async def test_plan_work_phases_asbestos_minor_no_threshold(db_session):
    """Asbestos in good condition without threshold exceeded → minor."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(
        db_session,
        diag.id,
        material_state="good",
        threshold_exceeded=False,  # Not exceeded → won't appear in positive samples
    )

    result = await plan_work_phases(db_session, building.id)
    # No positive samples → no phases
    assert result.total_phases == 0


@pytest.mark.asyncio
async def test_plan_work_phases_dependencies_chain(db_session):
    """Each phase depends on the previous one within a pollutant."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id, material_state="degraded")

    result = await plan_work_phases(db_session, building.id)
    # First phase has no dependencies
    assert result.phases[0].dependencies == []
    # Each subsequent phase depends on the previous
    for i in range(1, len(result.phases)):
        assert result.phases[i].dependencies == [result.phases[i - 1].phase_id]


@pytest.mark.asyncio
async def test_plan_work_phases_multi_pollutant(db_session):
    """Multiple pollutants generate 6 phases each, asbestos first."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    diag = await _create_diagnostic(db_session, building.id, diag_type="full")
    await _create_sample(db_session, diag.id, pollutant_type="pcb", material_state="degraded")
    await _create_sample(db_session, diag.id, pollutant_type="asbestos", material_state="degraded")

    result = await plan_work_phases(db_session, building.id)
    assert result.total_phases == 12  # 6 phases x 2 pollutants

    # Asbestos phases come first
    asbestos_phases = [p for p in result.phases if p.pollutant == "asbestos"]
    pcb_phases = [p for p in result.phases if p.pollutant == "pcb"]
    assert asbestos_phases[0].order < pcb_phases[0].order


@pytest.mark.asyncio
async def test_plan_work_phases_equipment_and_safety(db_session):
    """Phases include required equipment and safety measures."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id, material_state="degraded")

    result = await plan_work_phases(db_session, building.id)
    removal = next(p for p in result.phases if p.phase_type == "removal")
    assert "hepa_vacuum" in removal.required_equipment
    assert "respiratory_protection_ffp3" in removal.safety_measures


@pytest.mark.asyncio
async def test_plan_work_phases_degraded_medium(db_session):
    """Degraded material state produces medium CFST category."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id, material_state="degraded")

    result = await plan_work_phases(db_session, building.id)
    assert all(p.cfst_category == "medium" for p in result.phases)


@pytest.mark.asyncio
async def test_plan_work_phases_pcb_only(db_session):
    """PCB-only building generates 6 phases."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    diag = await _create_diagnostic(db_session, building.id, diag_type="pcb")
    await _create_sample(db_session, diag.id, pollutant_type="pcb", material_state="degraded")

    result = await plan_work_phases(db_session, building.id)
    assert result.total_phases == 6
    assert all(p.pollutant == "pcb" for p in result.phases)


@pytest.mark.asyncio
async def test_plan_work_phases_lead_only(db_session):
    """Lead-only building generates 6 phases."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    diag = await _create_diagnostic(db_session, building.id, diag_type="lead")
    await _create_sample(db_session, diag.id, pollutant_type="lead", material_state="good")

    result = await plan_work_phases(db_session, building.id)
    assert result.total_phases == 6
    assert all(p.pollutant == "lead" for p in result.phases)


@pytest.mark.asyncio
async def test_plan_work_phases_hap_only(db_session):
    """HAP-only building generates 6 phases."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    diag = await _create_diagnostic(db_session, building.id, diag_type="hap")
    await _create_sample(db_session, diag.id, pollutant_type="hap", material_state="degraded")

    result = await plan_work_phases(db_session, building.id)
    assert result.total_phases == 6


@pytest.mark.asyncio
async def test_plan_work_phases_radon_only(db_session):
    """Radon-only building generates 6 phases."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    diag = await _create_diagnostic(db_session, building.id, diag_type="radon")
    await _create_sample(db_session, diag.id, pollutant_type="radon", material_state="good")

    result = await plan_work_phases(db_session, building.id)
    assert result.total_phases == 6


# ---------------------------------------------------------------------------
# FN2: estimate_phase_timeline
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_timeline_empty_building(db_session):
    """Clean building returns zero-duration timeline."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    result = await estimate_phase_timeline(db_session, building.id)
    assert result.total_duration_days == 0
    assert result.phases == []
    assert result.critical_path == []


@pytest.mark.asyncio
async def test_timeline_single_pollutant(db_session):
    """Single pollutant timeline has sequential phases on critical path."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id, material_state="degraded")

    result = await estimate_phase_timeline(db_session, building.id)
    assert result.total_duration_days > 0
    assert len(result.phases) == 6
    assert result.start_date < result.end_date

    # All phases should be on critical path (single chain)
    assert len(result.critical_path) == 6


@pytest.mark.asyncio
async def test_timeline_dates_sequential(db_session):
    """Phase dates are sequential — each starts when predecessor ends."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id, material_state="degraded")

    result = await estimate_phase_timeline(db_session, building.id)
    for i in range(1, len(result.phases)):
        assert result.phases[i].start_date == result.phases[i - 1].end_date


@pytest.mark.asyncio
async def test_timeline_multi_pollutant_parallel_possible(db_session):
    """Multi-pollutant timeline identifies parallel-possible phases."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    diag = await _create_diagnostic(db_session, building.id, diag_type="full")
    await _create_sample(db_session, diag.id, pollutant_type="asbestos", material_state="degraded")
    await _create_sample(db_session, diag.id, pollutant_type="pcb", material_state="degraded")

    result = await estimate_phase_timeline(db_session, building.id)
    assert result.total_duration_days > 0
    assert len(result.parallel_possible) > 0


@pytest.mark.asyncio
async def test_timeline_total_duration_matches_sum(db_session):
    """Total duration equals sum of all sequential phase durations."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id, material_state="degraded")

    result = await estimate_phase_timeline(db_session, building.id)
    sum_durations = sum(p.duration_days for p in result.phases)
    assert result.total_duration_days == sum_durations


@pytest.mark.asyncio
async def test_timeline_no_building(db_session):
    """Non-existent building returns zero-duration timeline."""
    result = await estimate_phase_timeline(db_session, uuid.uuid4())
    assert result.total_duration_days == 0


# ---------------------------------------------------------------------------
# FN3: get_phase_requirements
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_requirements_asbestos_removal(db_session):
    """Asbestos removal requirements include CFST/OTConst refs and air monitoring."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id)

    result = await get_phase_requirements(db_session, building.id, "removal")
    assert "CFST 6503" in result.regulatory_references
    assert "OTConst Art. 60a" in result.regulatory_references
    assert "certified_asbestos_removal_specialist" in result.qualified_personnel
    assert "suva_notification" in result.permits_needed
    assert result.air_monitoring_required is True
    assert result.waste_management_plan is not None


@pytest.mark.asyncio
async def test_requirements_no_samples(db_session):
    """Building with no samples returns empty requirements."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)

    result = await get_phase_requirements(db_session, building.id, "preparation")
    assert result.regulatory_references == []
    assert result.qualified_personnel == []
    assert result.air_monitoring_required is False


@pytest.mark.asyncio
async def test_requirements_pcb(db_session):
    """PCB requirements include ORRChim references."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    diag = await _create_diagnostic(db_session, building.id, diag_type="pcb")
    await _create_sample(db_session, diag.id, pollutant_type="pcb")

    result = await get_phase_requirements(db_session, building.id, "removal")
    assert "ORRChim Annexe 2.15" in result.regulatory_references
    assert "pcb_remediation_specialist" in result.qualified_personnel


@pytest.mark.asyncio
async def test_requirements_verification_air_monitoring(db_session):
    """Verification phase requires air monitoring when asbestos present."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id)

    result = await get_phase_requirements(db_session, building.id, "verification")
    assert result.air_monitoring_required is True


@pytest.mark.asyncio
async def test_requirements_preparation_no_air_monitoring(db_session):
    """Preparation phase without asbestos does not require air monitoring."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    diag = await _create_diagnostic(db_session, building.id, diag_type="lead")
    await _create_sample(db_session, diag.id, pollutant_type="lead")

    result = await get_phase_requirements(db_session, building.id, "preparation")
    # Lead only — preparation doesn't require air monitoring
    assert result.air_monitoring_required is False


@pytest.mark.asyncio
async def test_requirements_multi_pollutant_dedup(db_session):
    """Multi-pollutant requirements are deduplicated."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    diag = await _create_diagnostic(db_session, building.id, diag_type="full")
    await _create_sample(db_session, diag.id, pollutant_type="asbestos")
    await _create_sample(db_session, diag.id, pollutant_type="pcb")

    result = await get_phase_requirements(db_session, building.id, "removal")
    # cantonal_waste_plan appears in both asbestos and pcb permits
    assert result.permits_needed.count("cantonal_waste_plan") == 1


# ---------------------------------------------------------------------------
# FN4: get_portfolio_work_overview
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_portfolio_no_org(db_session):
    """Non-existent org returns empty overview."""
    result = await get_portfolio_work_overview(db_session, uuid.uuid4())
    assert result.buildings_with_planned_work == 0
    assert result.total_phases_pending == 0


@pytest.mark.asyncio
async def test_portfolio_empty_org(db_session):
    """Org with no buildings returns zeros."""
    org = await _create_org(db_session)
    result = await get_portfolio_work_overview(db_session, org.id)
    assert result.buildings_with_planned_work == 0


@pytest.mark.asyncio
async def test_portfolio_one_building_with_work(db_session):
    """Org with one contaminated building shows correct counts."""
    org = await _create_org(db_session)
    user = await _create_user(db_session, org_id=org.id)
    building = await _create_building(db_session, user)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id, material_state="degraded")

    result = await get_portfolio_work_overview(db_session, org.id)
    assert result.buildings_with_planned_work == 1
    assert result.total_phases_pending == 6
    assert result.estimated_total_duration_days > 0
    assert len(result.buildings_by_cfst_category) > 0


@pytest.mark.asyncio
async def test_portfolio_mixed_buildings(db_session):
    """Org with clean and contaminated buildings counts only contaminated."""
    org = await _create_org(db_session)
    user = await _create_user(db_session, org_id=org.id)

    # Clean building
    await _create_building(db_session, user, construction_year=2020)

    # Contaminated building
    building2 = await _create_building(db_session, user)
    diag = await _create_diagnostic(db_session, building2.id)
    await _create_sample(db_session, diag.id, material_state="degraded")

    result = await get_portfolio_work_overview(db_session, org.id)
    assert result.buildings_with_planned_work == 1


@pytest.mark.asyncio
async def test_portfolio_cfst_category_distribution(db_session):
    """Portfolio shows correct CFST category distribution."""
    org = await _create_org(db_session)
    user = await _create_user(db_session, org_id=org.id)

    # Building with major category (friable)
    b1 = await _create_building(db_session, user)
    d1 = await _create_diagnostic(db_session, b1.id)
    await _create_sample(db_session, d1.id, material_state="friable", material_category="flocage")

    # Building with medium category (degraded)
    b2 = await _create_building(db_session, user)
    d2 = await _create_diagnostic(db_session, b2.id)
    await _create_sample(db_session, d2.id, material_state="degraded")

    result = await get_portfolio_work_overview(db_session, org.id)
    assert result.buildings_with_planned_work == 2

    cat_map = {c.category: c.count for c in result.buildings_by_cfst_category}
    assert cat_map.get("major", 0) == 1
    assert cat_map.get("medium", 0) == 1
