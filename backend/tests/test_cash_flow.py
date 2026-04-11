"""Tests for cash flow service."""

import uuid
from datetime import date

import pytest

from app.models.building import Building
from app.models.financial_entry import FinancialEntry
from app.models.intervention import Intervention
from app.services.cash_flow_service import (
    INCOME_GROWTH_RATE,
    compute_annual_summary,
    forecast_cash_flow,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def building_with_finances(db_session, admin_user):
    """Building with financial entries for 2025."""
    bldg = Building(
        id=uuid.uuid4(),
        address="Rue Finance 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1990,
        building_type="residential",
        surface_area_m2=400.0,
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(bldg)
    await db_session.flush()

    # Income entries
    entries = [
        FinancialEntry(
            id=uuid.uuid4(),
            building_id=bldg.id,
            entry_type="income",
            category="rent_income",
            amount_chf=120000.0,
            entry_date=date(2025, 6, 1),
            fiscal_year=2025,
            status="recorded",
            created_by=admin_user.id,
        ),
        FinancialEntry(
            id=uuid.uuid4(),
            building_id=bldg.id,
            entry_type="income",
            category="charges_income",
            amount_chf=24000.0,
            entry_date=date(2025, 6, 1),
            fiscal_year=2025,
            status="recorded",
            created_by=admin_user.id,
        ),
        # Expense entries
        FinancialEntry(
            id=uuid.uuid4(),
            building_id=bldg.id,
            entry_type="expense",
            category="maintenance",
            amount_chf=15000.0,
            entry_date=date(2025, 3, 15),
            fiscal_year=2025,
            status="recorded",
            created_by=admin_user.id,
        ),
        FinancialEntry(
            id=uuid.uuid4(),
            building_id=bldg.id,
            entry_type="expense",
            category="insurance_premium",
            amount_chf=8000.0,
            entry_date=date(2025, 1, 1),
            fiscal_year=2025,
            status="recorded",
            created_by=admin_user.id,
        ),
        FinancialEntry(
            id=uuid.uuid4(),
            building_id=bldg.id,
            entry_type="expense",
            category="energy",
            amount_chf=12000.0,
            entry_date=date(2025, 12, 1),
            fiscal_year=2025,
            status="validated",
            created_by=admin_user.id,
        ),
    ]
    db_session.add_all(entries)
    await db_session.commit()
    await db_session.refresh(bldg)
    return bldg


@pytest.fixture
async def empty_building(db_session, admin_user):
    bldg = Building(
        id=uuid.uuid4(),
        address="Rue Vide 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=2010,
        building_type="commercial",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(bldg)
    await db_session.commit()
    await db_session.refresh(bldg)
    return bldg


@pytest.fixture
async def building_with_planned_capex(db_session, admin_user):
    """Building with financial history + planned interventions."""
    bldg = Building(
        id=uuid.uuid4(),
        address="Rue Capex 5",
        postal_code="1200",
        city="Geneve",
        canton="GE",
        construction_year=1985,
        building_type="residential",
        surface_area_m2=350.0,
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(bldg)
    await db_session.flush()

    # Financial entries for 2025
    fe = FinancialEntry(
        id=uuid.uuid4(),
        building_id=bldg.id,
        entry_type="income",
        category="rent_income",
        amount_chf=80000.0,
        entry_date=date(2025, 6, 1),
        fiscal_year=2025,
        status="recorded",
        created_by=admin_user.id,
    )
    db_session.add(fe)

    fe2 = FinancialEntry(
        id=uuid.uuid4(),
        building_id=bldg.id,
        entry_type="expense",
        category="maintenance",
        amount_chf=10000.0,
        entry_date=date(2025, 6, 1),
        fiscal_year=2025,
        status="recorded",
        created_by=admin_user.id,
    )
    db_session.add(fe2)

    # Planned intervention in 2027
    iv = Intervention(
        id=uuid.uuid4(),
        building_id=bldg.id,
        intervention_type="insulation_upgrade",
        title="Full facade renovation",
        status="planned",
        cost_chf=150000.0,
        date_start=date(2027, 4, 1),
        created_by=admin_user.id,
    )
    db_session.add(iv)
    await db_session.commit()
    await db_session.refresh(bldg)
    return bldg


# ---------------------------------------------------------------------------
# Tests: compute_annual_summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_annual_summary_with_entries(db_session, building_with_finances):
    result = await compute_annual_summary(db_session, building_with_finances.id, 2025)

    assert result["year"] == 2025
    assert result["total_income"] == 144000.0  # 120000 + 24000
    assert result["total_expenses"] == 35000.0  # 15000 + 8000 + 12000
    assert result["net"] == 109000.0
    assert result["entry_count"] == 5
    assert "rent_income" in result["by_category"]
    assert result["by_category"]["rent_income"] == 120000.0


@pytest.mark.asyncio
async def test_annual_summary_empty_year(db_session, building_with_finances):
    """Querying a year with no entries returns zeros."""
    result = await compute_annual_summary(db_session, building_with_finances.id, 2020)

    assert result["total_income"] == 0.0
    assert result["total_expenses"] == 0.0
    assert result["net"] == 0.0
    assert result["entry_count"] == 0


@pytest.mark.asyncio
async def test_annual_summary_building_not_found(db_session):
    with pytest.raises(ValueError, match="not found"):
        await compute_annual_summary(db_session, uuid.uuid4(), 2025)


# ---------------------------------------------------------------------------
# Tests: forecast_cash_flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_forecast_with_history(db_session, building_with_finances):
    """Forecast from building with 2025 data: 5 years projected."""
    result = await forecast_cash_flow(db_session, building_with_finances.id, years=5)

    assert result["base_year"] == 2025
    assert result["forecast_years"] == 5
    assert len(result["years"]) == 5

    # Year 1 (2026): income grows, expenses grow
    y1 = result["years"][0]
    assert y1["year"] == 2026
    assert y1["income"] > 0
    assert y1["expenses"] > 0
    assert y1["capex"] == 0.0  # No planned interventions

    # Income should grow at INCOME_GROWTH_RATE
    expected_income = round(144000.0 * (1 + INCOME_GROWTH_RATE), 2)
    assert y1["income"] == expected_income


@pytest.mark.asyncio
async def test_forecast_with_capex(db_session, building_with_planned_capex):
    """Planned intervention appears as CAPEX in the right year."""
    result = await forecast_cash_flow(db_session, building_with_planned_capex.id, years=5)

    # Find year 2027 (base=2025, so year index 1 = 2027)
    y2027 = next((y for y in result["years"] if y["year"] == 2027), None)
    assert y2027 is not None
    assert y2027["capex"] == 150000.0
    assert y2027["net"] < 0  # Should be negative due to large CAPEX


@pytest.mark.asyncio
async def test_forecast_empty_building(db_session, empty_building):
    """Building with no financial history returns projections of zeros."""
    result = await forecast_cash_flow(db_session, empty_building.id, years=3)

    assert len(result["years"]) == 3
    for y in result["years"]:
        assert y["income"] == 0.0
        assert y["expenses"] == 0.0


@pytest.mark.asyncio
async def test_forecast_summary(db_session, building_with_finances):
    result = await forecast_cash_flow(db_session, building_with_finances.id, years=3)

    assert "summary" in result
    assert "total_net" in result["summary"]
    assert "avg_annual_net" in result["summary"]
    # With positive net income, total should be positive
    assert result["summary"]["total_net"] > 0


@pytest.mark.asyncio
async def test_forecast_building_not_found(db_session):
    with pytest.raises(ValueError, match="not found"):
        await forecast_cash_flow(db_session, uuid.uuid4())
