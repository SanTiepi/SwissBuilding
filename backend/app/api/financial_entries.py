"""BatiConnect — FinancialEntry API routes (org-level listing for Finance workspace)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.building import Building
from app.models.financial_entry import FinancialEntry
from app.models.user import User
from app.schemas.financial_entry import FinancialEntryRead

router = APIRouter()


@router.get(
    "/financial-entries",
    response_model=list[FinancialEntryRead],
)
async def list_financial_entries(
    building_id: UUID | None = None,
    entry_type: str | None = None,
    category: str | None = None,
    fiscal_year: int | None = None,
    status: str | None = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List financial entries across buildings for the current user's organization."""
    # Sub-query: building IDs belonging to the user's org
    org_building_ids = select(Building.id).where(Building.organization_id == current_user.organization_id)

    stmt = select(FinancialEntry).where(FinancialEntry.building_id.in_(org_building_ids))

    if building_id:
        stmt = stmt.where(FinancialEntry.building_id == building_id)
    if entry_type:
        stmt = stmt.where(FinancialEntry.entry_type == entry_type)
    if category:
        stmt = stmt.where(FinancialEntry.category == category)
    if fiscal_year:
        stmt = stmt.where(FinancialEntry.fiscal_year == fiscal_year)
    if status:
        stmt = stmt.where(FinancialEntry.status == status)

    stmt = stmt.order_by(FinancialEntry.entry_date.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get(
    "/financial-entries/summary",
)
async def financial_summary(
    fiscal_year: int | None = None,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate summary of financial entries for the current user's organization."""
    org_building_ids = select(Building.id).where(Building.organization_id == current_user.organization_id)

    base = select(FinancialEntry).where(
        FinancialEntry.building_id.in_(org_building_ids),
        FinancialEntry.status != "cancelled",
    )
    if fiscal_year:
        base = base.where(FinancialEntry.fiscal_year == fiscal_year)

    # Total expenses
    expense_stmt = select(func.coalesce(func.sum(FinancialEntry.amount_chf), 0)).where(
        FinancialEntry.building_id.in_(org_building_ids),
        FinancialEntry.status != "cancelled",
        FinancialEntry.entry_type == "expense",
    )
    if fiscal_year:
        expense_stmt = expense_stmt.where(FinancialEntry.fiscal_year == fiscal_year)

    # Total income
    income_stmt = select(func.coalesce(func.sum(FinancialEntry.amount_chf), 0)).where(
        FinancialEntry.building_id.in_(org_building_ids),
        FinancialEntry.status != "cancelled",
        FinancialEntry.entry_type == "income",
    )
    if fiscal_year:
        income_stmt = income_stmt.where(FinancialEntry.fiscal_year == fiscal_year)

    # Count
    count_stmt = select(func.count(FinancialEntry.id)).where(
        FinancialEntry.building_id.in_(org_building_ids),
        FinancialEntry.status != "cancelled",
    )
    if fiscal_year:
        count_stmt = count_stmt.where(FinancialEntry.fiscal_year == fiscal_year)

    expenses = (await db.execute(expense_stmt)).scalar() or 0
    income = (await db.execute(income_stmt)).scalar() or 0
    count = (await db.execute(count_stmt)).scalar() or 0

    return {
        "total_expenses": float(expenses),
        "total_income": float(income),
        "net": float(income) - float(expenses),
        "entry_count": count,
        "fiscal_year": fiscal_year,
    }
