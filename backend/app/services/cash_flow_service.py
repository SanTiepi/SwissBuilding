"""
SwissBuildingOS - Cash Flow Service

Aggregates FinancialEntry records into annual summaries and projects
multi-year cash flows based on historical data and planned interventions.

The FinancialEntry model has 21 categories (see financial_entry.py).
This service groups them into income vs. expense and provides by-category
breakdowns for any given fiscal year.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.financial_entry import FinancialEntry
from app.models.intervention import Intervention

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

INCOME_CATEGORIES = {
    "rent_income",
    "charges_income",
    "capital_gain",
    "other_income",
}

EXPENSE_CATEGORIES = {
    "maintenance",
    "repair",
    "renovation",
    "insurance_premium",
    "tax",
    "energy",
    "cleaning",
    "elevator",
    "management_fee",
    "concierge",
    "legal",
    "audit",
    "reserve_fund",
    "interest",
    "mortgage",
    "depreciation",
    "other_expense",
}

# Default annual growth rates for forecasting
INCOME_GROWTH_RATE = 0.015  # 1.5% per year (Swiss reference rate)
EXPENSE_GROWTH_RATE = 0.02  # 2% per year


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_building(db: AsyncSession, building_id: UUID) -> Building:
    stmt = select(Building).where(Building.id == building_id)
    result = await db.execute(stmt)
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")
    return building


async def _get_entries_for_year(
    db: AsyncSession,
    building_id: UUID,
    year: int,
) -> list[FinancialEntry]:
    """Fetch all financial entries for a building in a given fiscal year."""
    stmt = select(FinancialEntry).where(
        FinancialEntry.building_id == building_id,
        FinancialEntry.fiscal_year == year,
        FinancialEntry.status.in_(["recorded", "validated"]),
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _get_planned_interventions(
    db: AsyncSession,
    building_id: UUID,
) -> list[Intervention]:
    """Fetch planned interventions with cost estimates."""
    stmt = select(Intervention).where(
        Intervention.building_id == building_id,
        Intervention.status.in_(["planned", "approved"]),
        Intervention.cost_chf.isnot(None),
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def compute_annual_summary(
    db: AsyncSession,
    building_id: UUID,
    year: int,
) -> dict:
    """Aggregate FinancialEntry by category for a given fiscal year.

    Return: {
        building_id, year, total_income, total_expenses, net,
        by_category: {rent_income: X, charges_income: Y, ...},
        entry_count, computed_at
    }
    """
    await _get_building(db, building_id)
    entries = await _get_entries_for_year(db, building_id, year)

    by_category: dict[str, float] = {}
    total_income = 0.0
    total_expenses = 0.0

    for entry in entries:
        cat = entry.category
        amt = entry.amount_chf or 0.0
        by_category[cat] = by_category.get(cat, 0.0) + amt

        if cat in INCOME_CATEGORIES:
            total_income += amt
        else:
            total_expenses += amt

    net = total_income - total_expenses

    return {
        "building_id": str(building_id),
        "year": year,
        "total_income": round(total_income, 2),
        "total_expenses": round(total_expenses, 2),
        "net": round(net, 2),
        "by_category": {k: round(v, 2) for k, v in sorted(by_category.items())},
        "entry_count": len(entries),
        "computed_at": datetime.now(UTC).isoformat(),
    }


async def forecast_cash_flow(
    db: AsyncSession,
    building_id: UUID,
    years: int = 5,
) -> dict:
    """Project cash flows based on historical data and planned interventions.

    Uses the most recent fiscal year with data as the baseline.
    Applies growth rates and adds planned CAPEX from interventions.

    Return: {
        building_id, base_year, forecast_years,
        years: [{year, income, expenses, capex, net}],
        summary: {total_net, avg_annual_net},
        computed_at
    }
    """
    await _get_building(db, building_id)

    # Find the most recent year with financial data
    stmt = (
        select(FinancialEntry.fiscal_year)
        .where(
            FinancialEntry.building_id == building_id,
            FinancialEntry.status.in_(["recorded", "validated"]),
            FinancialEntry.fiscal_year.isnot(None),
        )
        .distinct()
        .order_by(FinancialEntry.fiscal_year.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    row = result.first()
    base_year = row[0] if row else datetime.now(UTC).year

    # Get base year data
    entries = await _get_entries_for_year(db, building_id, base_year)
    base_income = sum(e.amount_chf for e in entries if e.category in INCOME_CATEGORIES)
    base_expenses = sum(e.amount_chf for e in entries if e.category in EXPENSE_CATEGORIES)

    # If no data, use zeros
    if not entries:
        base_income = 0.0
        base_expenses = 0.0

    # Get planned interventions for CAPEX
    planned = await _get_planned_interventions(db, building_id)
    capex_by_year: dict[int, float] = {}
    for iv in planned:
        # Use date_start year if available, otherwise spread evenly
        iv_year = iv.date_start.year if iv.date_start else base_year + 1
        capex_by_year[iv_year] = capex_by_year.get(iv_year, 0.0) + (iv.cost_chf or 0.0)

    # Project forward
    year_projections = []
    total_net = 0.0

    for i in range(1, years + 1):
        proj_year = base_year + i
        income = round(base_income * ((1 + INCOME_GROWTH_RATE) ** i), 2)
        expenses = round(base_expenses * ((1 + EXPENSE_GROWTH_RATE) ** i), 2)
        capex = round(capex_by_year.get(proj_year, 0.0), 2)
        net = round(income - expenses - capex, 2)
        total_net += net

        year_projections.append(
            {
                "year": proj_year,
                "income": income,
                "expenses": expenses,
                "capex": capex,
                "net": net,
            }
        )

    avg_annual_net = round(total_net / years, 2) if years > 0 else 0.0

    return {
        "building_id": str(building_id),
        "base_year": base_year,
        "forecast_years": years,
        "years": year_projections,
        "summary": {
            "total_net": round(total_net, 2),
            "avg_annual_net": avg_annual_net,
        },
        "computed_at": datetime.now(UTC).isoformat(),
    }
