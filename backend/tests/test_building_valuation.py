"""Tests for building valuation service — pollutant impact on Swiss building value."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.services.building_valuation_service import (
    calculate_renovation_roi,
    compare_market_position,
    estimate_pollutant_impact,
    get_portfolio_valuation_summary,
)

# Re-use conftest password hashes
from tests.conftest import _HASH_ADMIN

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_user(db: AsyncSession, org_id: uuid.UUID | None = None) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"val-{uuid.uuid4().hex[:8]}@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Val",
        last_name="Test",
        role="admin",
        is_active=True,
        language="fr",
        organization_id=org_id,
    )
    db.add(user)
    await db.flush()
    return user


async def _create_org(db: AsyncSession) -> Organization:
    org = Organization(
        id=uuid.uuid4(),
        name=f"TestOrg-{uuid.uuid4().hex[:6]}",
        type="property_management",
    )
    db.add(org)
    await db.flush()
    return org


async def _create_building(
    db: AsyncSession,
    user_id: uuid.UUID,
    canton: str = "VD",
    building_type: str = "residential",
    surface: float | None = None,
) -> Building:
    bldg = Building(
        id=uuid.uuid4(),
        address=f"Rue Test {uuid.uuid4().hex[:4]}",
        postal_code="1000",
        city="Lausanne",
        canton=canton,
        construction_year=1970,
        building_type=building_type,
        created_by=user_id,
        status="active",
    )
    if surface is not None:
        bldg.surface_area_m2 = surface
    db.add(bldg)
    await db.flush()
    return bldg


async def _create_diagnostic_with_samples(
    db: AsyncSession,
    building_id: uuid.UUID,
    pollutant_samples: list[dict],
    status: str = "completed",
) -> Diagnostic:
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type="pollutant",
        status=status,
    )
    db.add(diag)
    await db.flush()

    for i, sample_data in enumerate(pollutant_samples):
        sample = Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number=f"S-{i + 1}",
            pollutant_type=sample_data.get("pollutant_type", "asbestos"),
            risk_level=sample_data.get("risk_level", "high"),
            threshold_exceeded=sample_data.get("threshold_exceeded", True),
            location_floor=sample_data.get("location_floor"),
            location_room=sample_data.get("location_room"),
        )
        db.add(sample)

    await db.flush()
    return diag


# ===========================================================================
# FN1 — estimate_pollutant_impact
# ===========================================================================


@pytest.mark.asyncio
async def test_pollutant_impact_no_building(db_session):
    """Should raise ValueError for non-existent building."""
    with pytest.raises(ValueError, match="not found"):
        await estimate_pollutant_impact(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_pollutant_impact_clean_building(db_session):
    """Building with no diagnostics should return zero impact."""
    user = await _create_user(db_session)
    bldg = await _create_building(db_session, user.id)
    await db_session.commit()

    result = await estimate_pollutant_impact(db_session, bldg.id)
    assert result.building_id == bldg.id
    assert result.estimated_remediation_cost == 0.0
    assert result.value_reduction_percentage == 0.0
    assert result.market_impact_assessment == "minor"
    assert result.affected_areas == []


@pytest.mark.asyncio
async def test_pollutant_impact_single_pollutant(db_session):
    """Single asbestos finding should produce remediation cost and value reduction."""
    user = await _create_user(db_session)
    bldg = await _create_building(db_session, user.id, surface=200.0)
    await _create_diagnostic_with_samples(
        db_session,
        bldg.id,
        [{"pollutant_type": "asbestos", "risk_level": "high", "threshold_exceeded": True, "location_floor": "1er"}],
    )
    await db_session.commit()

    result = await estimate_pollutant_impact(db_session, bldg.id)
    assert result.estimated_remediation_cost == 120.0 * 200  # 24000
    assert result.value_reduction_percentage > 0
    assert result.market_impact_assessment in ("minor", "moderate", "significant", "severe")
    assert len(result.affected_areas) == 1
    assert result.affected_areas[0].zone == "1er"
    assert result.affected_areas[0].pollutant == "asbestos"


@pytest.mark.asyncio
async def test_pollutant_impact_multi_pollutant(db_session):
    """Multiple pollutants should accumulate costs and reduction."""
    user = await _create_user(db_session)
    bldg = await _create_building(db_session, user.id, surface=100.0)
    await _create_diagnostic_with_samples(
        db_session,
        bldg.id,
        [
            {"pollutant_type": "asbestos", "risk_level": "critical", "threshold_exceeded": True},
            {"pollutant_type": "pcb", "risk_level": "high", "threshold_exceeded": True},
            {"pollutant_type": "lead", "risk_level": "medium", "threshold_exceeded": True},
        ],
    )
    await db_session.commit()

    result = await estimate_pollutant_impact(db_session, bldg.id)
    expected_cost = 120.0 * 100 + 150.0 * 100 + 80.0 * 100  # 35000
    assert result.estimated_remediation_cost == expected_cost
    assert result.value_reduction_percentage > 0
    assert len(result.affected_areas) == 3


@pytest.mark.asyncio
async def test_pollutant_impact_below_threshold(db_session):
    """Samples below threshold should not affect valuation."""
    user = await _create_user(db_session)
    bldg = await _create_building(db_session, user.id)
    await _create_diagnostic_with_samples(
        db_session,
        bldg.id,
        [{"pollutant_type": "asbestos", "risk_level": "low", "threshold_exceeded": False}],
    )
    await db_session.commit()

    result = await estimate_pollutant_impact(db_session, bldg.id)
    assert result.estimated_remediation_cost == 0.0
    assert result.value_reduction_percentage == 0.0


@pytest.mark.asyncio
async def test_pollutant_impact_draft_diagnostic_ignored(db_session):
    """Draft diagnostics should not be included."""
    user = await _create_user(db_session)
    bldg = await _create_building(db_session, user.id)
    await _create_diagnostic_with_samples(
        db_session,
        bldg.id,
        [{"pollutant_type": "asbestos", "risk_level": "critical", "threshold_exceeded": True}],
        status="draft",
    )
    await db_session.commit()

    result = await estimate_pollutant_impact(db_session, bldg.id)
    assert result.estimated_remediation_cost == 0.0


@pytest.mark.asyncio
async def test_pollutant_impact_radon(db_session):
    """Radon should use fixed + per-m2 cost."""
    user = await _create_user(db_session)
    bldg = await _create_building(db_session, user.id, surface=100.0)
    await _create_diagnostic_with_samples(
        db_session,
        bldg.id,
        [{"pollutant_type": "radon", "risk_level": "high", "threshold_exceeded": True}],
    )
    await db_session.commit()

    result = await estimate_pollutant_impact(db_session, bldg.id)
    assert result.estimated_remediation_cost == 5000.0 + 15.0 * 100  # 6500


@pytest.mark.asyncio
async def test_pollutant_impact_value_reduction_capped(db_session):
    """Value reduction should be capped at 50%."""
    user = await _create_user(db_session)
    bldg = await _create_building(db_session, user.id, surface=200.0)
    # All 5 pollutants at critical = each pollutant's reduction * 2.0 multiplier
    await _create_diagnostic_with_samples(
        db_session,
        bldg.id,
        [
            {"pollutant_type": "asbestos", "risk_level": "critical", "threshold_exceeded": True},
            {"pollutant_type": "pcb", "risk_level": "critical", "threshold_exceeded": True},
            {"pollutant_type": "lead", "risk_level": "critical", "threshold_exceeded": True},
            {"pollutant_type": "hap", "risk_level": "critical", "threshold_exceeded": True},
            {"pollutant_type": "radon", "risk_level": "critical", "threshold_exceeded": True},
        ],
    )
    await db_session.commit()

    result = await estimate_pollutant_impact(db_session, bldg.id)
    assert result.value_reduction_percentage <= 50.0


# ===========================================================================
# FN2 — calculate_renovation_roi
# ===========================================================================


@pytest.mark.asyncio
async def test_renovation_roi_no_building(db_session):
    """Should raise ValueError for non-existent building."""
    with pytest.raises(ValueError, match="not found"):
        await calculate_renovation_roi(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_renovation_roi_clean_building(db_session):
    """Clean building should have zero cost and zero ROI."""
    user = await _create_user(db_session)
    bldg = await _create_building(db_session, user.id)
    await db_session.commit()

    result = await calculate_renovation_roi(db_session, bldg.id)
    assert result.total_remediation_cost == 0.0
    assert result.estimated_value_increase == 0.0
    assert result.roi_percentage == 0.0
    assert result.certification_eligibility_gained == []


@pytest.mark.asyncio
async def test_renovation_roi_with_pollutants(db_session):
    """Building with exceeded thresholds should show positive ROI."""
    user = await _create_user(db_session)
    bldg = await _create_building(db_session, user.id, surface=200.0)
    await _create_diagnostic_with_samples(
        db_session,
        bldg.id,
        [{"pollutant_type": "asbestos", "risk_level": "high", "threshold_exceeded": True}],
    )
    await db_session.commit()

    result = await calculate_renovation_roi(db_session, bldg.id)
    assert result.total_remediation_cost > 0
    assert result.estimated_value_increase > 0
    assert result.roi_percentage > 0
    assert result.payback_period_years > 0
    assert result.risk_reduction.before == "high"
    assert result.risk_reduction.after == "low"
    assert len(result.certification_eligibility_gained) > 0


@pytest.mark.asyncio
async def test_renovation_roi_risk_reduction_levels(db_session):
    """Before risk should reflect worst pollutant, after should be low."""
    user = await _create_user(db_session)
    bldg = await _create_building(db_session, user.id, surface=100.0)
    await _create_diagnostic_with_samples(
        db_session,
        bldg.id,
        [
            {"pollutant_type": "asbestos", "risk_level": "critical", "threshold_exceeded": True},
            {"pollutant_type": "lead", "risk_level": "medium", "threshold_exceeded": True},
        ],
    )
    await db_session.commit()

    result = await calculate_renovation_roi(db_session, bldg.id)
    assert result.risk_reduction.before == "critical"
    assert result.risk_reduction.after == "low"


# ===========================================================================
# FN3 — compare_market_position
# ===========================================================================


@pytest.mark.asyncio
async def test_market_position_no_building(db_session):
    """Should raise ValueError for non-existent building."""
    with pytest.raises(ValueError, match="not found"):
        await compare_market_position(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_market_position_no_comparables(db_session):
    """Building with no comparables should default to 50th percentile."""
    user = await _create_user(db_session)
    bldg = await _create_building(db_session, user.id)
    await db_session.commit()

    result = await compare_market_position(db_session, bldg.id)
    assert result.building_id == bldg.id
    assert result.percentile_rank == 50.0
    assert result.comparable_buildings_count == 0


@pytest.mark.asyncio
async def test_market_position_clean_has_advantages(db_session):
    """Clean building should list advantages."""
    user = await _create_user(db_session)
    bldg = await _create_building(db_session, user.id)
    await db_session.commit()

    result = await compare_market_position(db_session, bldg.id)
    assert any("No pollutant" in a for a in result.advantages)


@pytest.mark.asyncio
async def test_market_position_with_comparables(db_session):
    """Building should be ranked against comparable buildings in same canton/type."""
    user = await _create_user(db_session)
    # Target building: clean
    target = await _create_building(db_session, user.id, canton="VD", building_type="residential")
    # Comparable: polluted
    comp1 = await _create_building(db_session, user.id, canton="VD", building_type="residential")
    await _create_diagnostic_with_samples(
        db_session,
        comp1.id,
        [{"pollutant_type": "asbestos", "risk_level": "critical", "threshold_exceeded": True}],
    )
    # Comparable: also polluted
    comp2 = await _create_building(db_session, user.id, canton="VD", building_type="residential")
    await _create_diagnostic_with_samples(
        db_session,
        comp2.id,
        [{"pollutant_type": "pcb", "risk_level": "high", "threshold_exceeded": True}],
    )
    await db_session.commit()

    result = await compare_market_position(db_session, target.id)
    assert result.comparable_buildings_count == 2
    # Clean building should rank better (higher percentile = better)
    assert result.percentile_rank == 100.0


@pytest.mark.asyncio
async def test_market_position_different_canton_not_comparable(db_session):
    """Buildings in different cantons should not be comparables."""
    user = await _create_user(db_session)
    target = await _create_building(db_session, user.id, canton="VD")
    await _create_building(db_session, user.id, canton="GE")
    await db_session.commit()

    result = await compare_market_position(db_session, target.id)
    assert result.comparable_buildings_count == 0


@pytest.mark.asyncio
async def test_market_position_disadvantages(db_session):
    """Polluted building should list disadvantages."""
    user = await _create_user(db_session)
    bldg = await _create_building(db_session, user.id)
    await _create_diagnostic_with_samples(
        db_session,
        bldg.id,
        [{"pollutant_type": "asbestos", "risk_level": "high", "threshold_exceeded": True}],
    )
    await db_session.commit()

    result = await compare_market_position(db_session, bldg.id)
    assert any("ASBESTOS" in d for d in result.disadvantages)


# ===========================================================================
# FN4 — get_portfolio_valuation_summary
# ===========================================================================


@pytest.mark.asyncio
async def test_portfolio_summary_no_org(db_session):
    """Should raise ValueError for non-existent organization."""
    with pytest.raises(ValueError, match="not found"):
        await get_portfolio_valuation_summary(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_portfolio_summary_empty_org(db_session):
    """Org with no members should return empty summary."""
    org = await _create_org(db_session)
    await db_session.commit()

    result = await get_portfolio_valuation_summary(db_session, org.id)
    assert result.organization_id == org.id
    assert result.total_remediation_liability == 0.0
    assert result.top_priority_buildings == []


@pytest.mark.asyncio
async def test_portfolio_summary_no_buildings(db_session):
    """Org with members but no buildings should return empty summary."""
    org = await _create_org(db_session)
    await _create_user(db_session, org_id=org.id)
    await db_session.commit()

    result = await get_portfolio_valuation_summary(db_session, org.id)
    assert result.total_remediation_liability == 0.0


@pytest.mark.asyncio
async def test_portfolio_summary_with_buildings(db_session):
    """Portfolio with polluted buildings should aggregate correctly."""
    org = await _create_org(db_session)
    user = await _create_user(db_session, org_id=org.id)
    bldg1 = await _create_building(db_session, user.id, surface=200.0)
    bldg2 = await _create_building(db_session, user.id, surface=100.0)
    await _create_diagnostic_with_samples(
        db_session,
        bldg1.id,
        [{"pollutant_type": "asbestos", "risk_level": "critical", "threshold_exceeded": True}],
    )
    await _create_diagnostic_with_samples(
        db_session,
        bldg2.id,
        [{"pollutant_type": "lead", "risk_level": "medium", "threshold_exceeded": True}],
    )
    await db_session.commit()

    result = await get_portfolio_valuation_summary(db_session, org.id)
    expected_liability = 120.0 * 200 + 80.0 * 100  # 32000
    assert result.total_remediation_liability == expected_liability
    assert result.average_value_impact_pct > 0
    assert len(result.top_priority_buildings) == 2


@pytest.mark.asyncio
async def test_portfolio_summary_impact_classification(db_session):
    """Buildings should be classified by impact level."""
    org = await _create_org(db_session)
    user = await _create_user(db_session, org_id=org.id)
    # Clean building = minor
    await _create_building(db_session, user.id, surface=100.0)
    # Polluted building = moderate+
    bldg2 = await _create_building(db_session, user.id, surface=100.0)
    await _create_diagnostic_with_samples(
        db_session,
        bldg2.id,
        [
            {"pollutant_type": "asbestos", "risk_level": "high", "threshold_exceeded": True},
            {"pollutant_type": "pcb", "risk_level": "high", "threshold_exceeded": True},
        ],
    )
    await db_session.commit()

    result = await get_portfolio_valuation_summary(db_session, org.id)
    total = (
        result.buildings_by_impact.minor
        + result.buildings_by_impact.moderate
        + result.buildings_by_impact.significant
        + result.buildings_by_impact.severe
    )
    assert total == 2


@pytest.mark.asyncio
async def test_portfolio_summary_top_priority_sorted_by_cost(db_session):
    """Top priority buildings should be sorted by remediation cost descending."""
    org = await _create_org(db_session)
    user = await _create_user(db_session, org_id=org.id)

    # Small cost building
    bldg_small = await _create_building(db_session, user.id, surface=50.0)
    await _create_diagnostic_with_samples(
        db_session,
        bldg_small.id,
        [{"pollutant_type": "lead", "risk_level": "medium", "threshold_exceeded": True}],
    )
    # Large cost building
    bldg_large = await _create_building(db_session, user.id, surface=500.0)
    await _create_diagnostic_with_samples(
        db_session,
        bldg_large.id,
        [{"pollutant_type": "asbestos", "risk_level": "critical", "threshold_exceeded": True}],
    )
    await db_session.commit()

    result = await get_portfolio_valuation_summary(db_session, org.id)
    assert len(result.top_priority_buildings) == 2
    assert result.top_priority_buildings[0].remediation_cost > result.top_priority_buildings[1].remediation_cost


@pytest.mark.asyncio
async def test_pollutant_impact_default_surface(db_session):
    """Building without surface_area_m2 should default to 200m2."""
    user = await _create_user(db_session)
    bldg = await _create_building(db_session, user.id)
    await _create_diagnostic_with_samples(
        db_session,
        bldg.id,
        [{"pollutant_type": "pcb", "risk_level": "high", "threshold_exceeded": True}],
    )
    await db_session.commit()

    result = await estimate_pollutant_impact(db_session, bldg.id)
    # Default 200m² * 150 CHF/m² = 30000
    assert result.estimated_remediation_cost == 150.0 * 200


@pytest.mark.asyncio
async def test_renovation_roi_no_threshold_exceeded(db_session):
    """Building with samples but none exceeded should have zero cost."""
    user = await _create_user(db_session)
    bldg = await _create_building(db_session, user.id)
    await _create_diagnostic_with_samples(
        db_session,
        bldg.id,
        [
            {"pollutant_type": "asbestos", "risk_level": "low", "threshold_exceeded": False},
            {"pollutant_type": "pcb", "risk_level": "low", "threshold_exceeded": False},
        ],
    )
    await db_session.commit()

    result = await calculate_renovation_roi(db_session, bldg.id)
    assert result.total_remediation_cost == 0.0
    assert result.roi_percentage == 0.0
    assert result.certification_eligibility_gained == []
