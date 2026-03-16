"""Tests for the post-works state service."""

from __future__ import annotations

import uuid

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.post_works_state import PostWorksState
from app.models.sample import Sample
from app.services.post_works_service import (
    compare_before_after,
    generate_post_works_states,
    get_post_works_summary,
    verify_post_works_state,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_building(db, admin_user):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=admin_user.id,
        owner_id=admin_user.id,
        status="active",
    )
    db.add(b)
    await db.flush()
    return b


async def _create_diagnostic(db, building_id, status="completed"):
    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type="avant_travaux",
        status=status,
    )
    db.add(d)
    await db.flush()
    return d


async def _create_sample(db, diagnostic_id, pollutant="asbestos", exceeded=True, location_room="Salle 1"):
    s = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic_id,
        sample_number=f"S-{uuid.uuid4().hex[:6]}",
        pollutant_type=pollutant,
        location_room=location_room,
        material_category="Flocage",
        threshold_exceeded=exceeded,
    )
    db.add(s)
    await db.flush()
    return s


async def _create_intervention(db, building_id, intervention_type="asbestos_removal", status="completed"):
    i = Intervention(
        id=uuid.uuid4(),
        building_id=building_id,
        intervention_type=intervention_type,
        title=f"Intervention {intervention_type}",
        status=status,
        created_by=None,
    )
    db.add(i)
    await db.flush()
    return i


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_post_works_from_removal(db_session, admin_user):
    building = await _create_building(db_session, admin_user)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id, pollutant="asbestos", location_room="Salle 1")
    await _create_sample(db_session, diag.id, pollutant="asbestos", location_room="Salle 2")
    intervention = await _create_intervention(db_session, building.id, intervention_type="asbestos_removal")

    states = await generate_post_works_states(db_session, building.id, intervention.id, recorded_by=admin_user.id)

    assert len(states) == 2
    for s in states:
        assert s.state_type == "removed"
        assert s.pollutant_type == "asbestos"
        assert s.verified is False
        assert s.recorded_by == admin_user.id


@pytest.mark.asyncio
async def test_generate_post_works_from_encapsulation(db_session, admin_user):
    building = await _create_building(db_session, admin_user)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id, pollutant="pcb")
    intervention = await _create_intervention(db_session, building.id, intervention_type="encapsulation")

    states = await generate_post_works_states(db_session, building.id, intervention.id)

    assert len(states) == 1
    assert states[0].state_type == "encapsulated"
    assert states[0].pollutant_type == "pcb"


@pytest.mark.asyncio
async def test_generate_post_works_from_generic(db_session, admin_user):
    building = await _create_building(db_session, admin_user)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id, pollutant="lead")
    intervention = await _create_intervention(db_session, building.id, intervention_type="inspection")

    states = await generate_post_works_states(db_session, building.id, intervention.id)

    assert len(states) == 1
    assert states[0].state_type == "recheck_needed"


@pytest.mark.asyncio
async def test_generate_post_works_not_completed(db_session, admin_user):
    building = await _create_building(db_session, admin_user)
    intervention = await _create_intervention(db_session, building.id, status="in_progress")

    with pytest.raises(ValueError, match="not completed"):
        await generate_post_works_states(db_session, building.id, intervention.id)


@pytest.mark.asyncio
async def test_generate_post_works_idempotent(db_session, admin_user):
    building = await _create_building(db_session, admin_user)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id, pollutant="asbestos")
    intervention = await _create_intervention(db_session, building.id)

    first = await generate_post_works_states(db_session, building.id, intervention.id)
    second = await generate_post_works_states(db_session, building.id, intervention.id)

    assert len(first) == 1
    assert len(second) == 0  # no duplicates


@pytest.mark.asyncio
async def test_compare_before_after(db_session, admin_user):
    building = await _create_building(db_session, admin_user)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id, pollutant="asbestos")
    await _create_sample(db_session, diag.id, pollutant="pcb")
    intervention = await _create_intervention(db_session, building.id)

    await generate_post_works_states(db_session, building.id, intervention.id)

    result = await compare_before_after(db_session, building.id, intervention_id=intervention.id)

    assert result["building_id"] == str(building.id)
    assert result["before"]["total_positive_samples"] == 2
    assert result["before"]["by_pollutant"]["asbestos"] == 1
    assert result["before"]["by_pollutant"]["pcb"] == 1
    assert result["after"]["removed"] == 2
    assert result["summary"]["remediation_rate"] == 1.0
    assert result["summary"]["residual_risk_count"] == 0


@pytest.mark.asyncio
async def test_compare_before_after_no_intervention(db_session, admin_user):
    building = await _create_building(db_session, admin_user)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id, pollutant="asbestos")

    result = await compare_before_after(db_session, building.id)

    assert result["before"]["total_positive_samples"] == 1
    assert result["after"]["removed"] == 0
    assert result["summary"]["remediation_rate"] == 0.0


@pytest.mark.asyncio
async def test_verify_post_works_state(db_session, admin_user):
    building = await _create_building(db_session, admin_user)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id, pollutant="asbestos")
    intervention = await _create_intervention(db_session, building.id)

    states = await generate_post_works_states(db_session, building.id, intervention.id)
    state = states[0]

    verified = await verify_post_works_state(db_session, state.id, verified_by=admin_user.id, notes="Confirmed on site")

    assert verified.verified is True
    assert verified.verified_by == admin_user.id
    assert verified.verified_at is not None
    assert verified.notes == "Confirmed on site"


@pytest.mark.asyncio
async def test_get_post_works_summary(db_session, admin_user):
    building = await _create_building(db_session, admin_user)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id, pollutant="asbestos")
    await _create_sample(db_session, diag.id, pollutant="pcb")

    intervention1 = await _create_intervention(db_session, building.id)
    intervention2 = await _create_intervention(db_session, building.id, intervention_type="encapsulation")

    await generate_post_works_states(db_session, building.id, intervention1.id)
    await generate_post_works_states(db_session, building.id, intervention2.id)

    summary = await get_post_works_summary(db_session, building.id)

    assert summary["building_id"] == str(building.id)
    assert summary["total_states"] == 4  # 2 samples x 2 interventions
    assert summary["verification_progress"]["verified"] == 0
    assert summary["verification_progress"]["rate"] == 0.0
    assert summary["interventions_covered"] == 2


@pytest.mark.asyncio
async def test_remediation_rate_calculation(db_session, admin_user):
    building = await _create_building(db_session, admin_user)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id, pollutant="asbestos")
    await _create_sample(db_session, diag.id, pollutant="pcb")
    await _create_sample(db_session, diag.id, pollutant="lead")

    # removal handles 2 of the 3 positive samples (asbestos + pcb + lead → all "removed")
    intervention = await _create_intervention(db_session, building.id)
    await generate_post_works_states(db_session, building.id, intervention.id)

    result = await compare_before_after(db_session, building.id, intervention_id=intervention.id)

    # 3 removed / 3 total = 1.0
    assert result["summary"]["remediation_rate"] == pytest.approx(1.0)

    # Now add a manual "remaining" state
    pws = PostWorksState(
        building_id=building.id,
        intervention_id=intervention.id,
        state_type="remaining",
        pollutant_type="hap",
        title="Remaining HAP",
    )
    db_session.add(pws)
    await db_session.flush()

    result2 = await compare_before_after(db_session, building.id, intervention_id=intervention.id)

    # remediation_rate = (removed=3) / total_positive_samples=3 = 1.0
    # residual_risk_count = remaining=1
    assert result2["summary"]["remediation_rate"] == pytest.approx(1.0)
    assert result2["summary"]["residual_risk_count"] == 1
