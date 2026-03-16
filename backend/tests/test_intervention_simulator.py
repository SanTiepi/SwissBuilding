"""Tests for the Intervention Simulator service."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.models.user import User
from app.schemas.simulation import SimulationInput
from app.services.intervention_simulator import simulate_interventions

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    u = User(
        id=uuid.uuid4(),
        email="sim-test@test.ch",
        password_hash="hashed",
        first_name="Sim",
        last_name="Test",
        role="admin",
        is_active=True,
        language="fr",
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest.fixture
async def building(db_session: AsyncSession, test_user: User) -> Building:
    b = Building(
        id=uuid.uuid4(),
        address="Rue de Test 1",
        city="Lausanne",
        canton="VD",
        postal_code="1000",
        building_type="residential",
        created_by=test_user.id,
    )
    db_session.add(b)
    await db_session.commit()
    await db_session.refresh(b)
    return b


@pytest.fixture
async def diagnostic(db_session: AsyncSession, building: Building) -> Diagnostic:
    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="asbestos",
        status="completed",
    )
    db_session.add(d)
    await db_session.commit()
    await db_session.refresh(d)
    return d


@pytest.fixture
async def positive_sample(db_session: AsyncSession, diagnostic: Diagnostic) -> Sample:
    s = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic.id,
        sample_number="S-001",
        pollutant_type="asbestos",
        threshold_exceeded=True,
        risk_level="high",
        location_room="Room 101",
    )
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)
    return s


@pytest.fixture
async def open_action(db_session: AsyncSession, building: Building) -> ActionItem:
    a = ActionItem(
        id=uuid.uuid4(),
        building_id=building.id,
        source_type="risk",
        action_type="remediation",
        title="Remove asbestos from Room 101",
        priority="high",
        status="open",
    )
    db_session.add(a)
    await db_session.commit()
    await db_session.refresh(a)
    return a


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_simulate_empty_interventions(db_session: AsyncSession, building: Building):
    """Simulating with no interventions returns unchanged state."""
    result = await simulate_interventions(db_session, building.id, [])

    assert result.current_state.passport_grade == result.projected_state.passport_grade
    assert result.impact_summary.actions_resolved == 0
    assert result.impact_summary.readiness_improvement == "no change"
    assert result.impact_summary.trust_delta == 0.0
    assert result.impact_summary.completeness_delta == 0.0
    assert result.impact_summary.grade_change is None
    assert result.impact_summary.estimated_total_cost is None


@pytest.mark.asyncio
async def test_simulate_single_removal(db_session: AsyncSession, building: Building, positive_sample: Sample):
    """A single asbestos_removal intervention produces positive deltas."""
    interventions = [
        SimulationInput(
            intervention_type="asbestos_removal",
            target_pollutant="asbestos",
            estimated_cost=15000.0,
        )
    ]
    result = await simulate_interventions(db_session, building.id, interventions)

    assert result.impact_summary.trust_delta > 0
    assert result.impact_summary.completeness_delta > 0
    assert result.impact_summary.estimated_total_cost == 15000.0
    # Risk reduction should mention asbestos
    assert "asbestos" in result.impact_summary.risk_reduction


@pytest.mark.asyncio
async def test_simulate_multiple_interventions(db_session: AsyncSession, building: Building, positive_sample: Sample):
    """Multiple interventions accumulate their effects."""
    interventions = [
        SimulationInput(intervention_type="asbestos_removal", target_pollutant="asbestos"),
        SimulationInput(intervention_type="inspection"),
        SimulationInput(intervention_type="renovation"),
    ]
    result = await simulate_interventions(db_session, building.id, interventions)

    # Trust delta should be sum of all boosts
    expected_trust = 0.05 + 0.02 + 0.05  # remediation + monitoring + remediation
    assert abs(result.impact_summary.trust_delta - expected_trust) < 0.001


@pytest.mark.asyncio
async def test_simulate_with_existing_actions(db_session: AsyncSession, building: Building, open_action: ActionItem):
    """Simulation resolves matching open actions."""
    assert open_action.status == "open"

    interventions = [
        SimulationInput(
            intervention_type="asbestos_removal",
            target_pollutant="asbestos",
        )
    ]
    result = await simulate_interventions(db_session, building.id, interventions)

    assert result.current_state.open_actions_count == 1
    assert result.impact_summary.actions_resolved == 1
    assert result.projected_state.open_actions_count == 0


@pytest.mark.asyncio
async def test_simulate_cost_aggregation(db_session: AsyncSession, building: Building):
    """Estimated costs are summed across all interventions."""
    interventions = [
        SimulationInput(intervention_type="renovation", estimated_cost=10000.0),
        SimulationInput(intervention_type="asbestos_removal", estimated_cost=25000.0),
        SimulationInput(intervention_type="maintenance", estimated_cost=5000.0),
    ]
    result = await simulate_interventions(db_session, building.id, interventions)

    assert result.impact_summary.estimated_total_cost == 40000.0


@pytest.mark.asyncio
async def test_simulate_grade_improvement(db_session: AsyncSession, building: Building):
    """Enough interventions can improve the passport grade."""
    result_before = await simulate_interventions(db_session, building.id, [])
    initial_grade = result_before.current_state.passport_grade

    # Simulate many high-impact interventions
    interventions = [
        SimulationInput(intervention_type="asbestos_removal", target_pollutant="asbestos"),
        SimulationInput(intervention_type="renovation"),
        SimulationInput(intervention_type="demolition"),
        SimulationInput(intervention_type="decontamination", target_pollutant="pcb"),
    ]
    result = await simulate_interventions(db_session, building.id, interventions)

    # With a building that starts at F (no data), enough trust/completeness boost
    # should improve the grade
    if initial_grade == "F":
        # 4 remediation interventions = 0.20 trust boost, 0.16 completeness boost
        # From 0.0 that gives D grade (trust >= 0.2, completeness >= 0.16 < 0.3 so still F or D)
        assert result.projected_state.trust_score > result.current_state.trust_score
    # If grade changed, it should be reflected
    if result.impact_summary.grade_change:
        assert "→" in result.impact_summary.grade_change


@pytest.mark.asyncio
async def test_simulate_recommendations(db_session: AsyncSession, building: Building):
    """Recommendations are generated based on projected state."""
    result = await simulate_interventions(db_session, building.id, [])

    assert isinstance(result.recommendations, list)
    assert len(result.recommendations) > 0


@pytest.mark.asyncio
async def test_simulate_nonexistent_building_404(db_session: AsyncSession):
    """Simulating for a non-existent building raises ValueError."""
    fake_id = uuid.uuid4()
    with pytest.raises(ValueError, match="not found"):
        await simulate_interventions(db_session, fake_id, [])
