"""BatiConnect — Quote Comparison Intelligence service.

Analyzes submitted quotes for a request. NEVER ranks or recommends —
only surfaces factual differences.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.quote import Quote
from app.schemas.intelligence_stack import QuoteComparisonInsight, ScopeCoverageItem

logger = logging.getLogger(__name__)


async def get_comparison_insights(
    db: AsyncSession,
    request_id: uuid.UUID,
) -> QuoteComparisonInsight:
    """Analyze all submitted quotes for a request. No ranking, no recommendation."""
    result = await db.execute(
        select(Quote)
        .where(
            Quote.client_request_id == request_id,
            Quote.status.in_(["submitted", "awarded"]),
        )
        .options(selectinload(Quote.company_profile))
    )
    quotes = result.scalars().all()

    if not quotes:
        return QuoteComparisonInsight(
            request_id=request_id,
            scope_coverage_matrix=[],
            price_spread={"min": 0, "max": 0, "median": 0, "range_pct": 0},
            timeline_spread={"min_weeks": 0, "max_weeks": 0, "median_weeks": 0},
            common_exclusions=[],
            ambiguity_flags=[],
            quote_count=0,
        )

    # Collect scope items per quote
    all_scope_items: set[str] = set()
    quote_scopes: dict[str, set[str]] = {}
    quote_exclusions: dict[str, set[str]] = {}
    prices: list[float] = []
    timelines: list[int] = []
    ambiguity_flags: list[dict] = []

    for q in quotes:
        company_name = str(q.company_profile_id)[:8]
        if q.company_profile and hasattr(q.company_profile, "company_name"):
            company_name = q.company_profile.company_name or company_name

        includes = set(q.includes or [])
        excludes = set(q.excludes or [])
        all_scope_items.update(includes)
        quote_scopes[company_name] = includes
        quote_exclusions[company_name] = excludes

        if q.amount_chf is not None:
            prices.append(float(q.amount_chf))
        if q.timeline_weeks is not None:
            timelines.append(int(q.timeline_weeks))

    # Scope coverage matrix
    scope_matrix: list[ScopeCoverageItem] = []
    for item in sorted(all_scope_items):
        present_in = [name for name, scope in quote_scopes.items() if item in scope]
        missing_from = [name for name, scope in quote_scopes.items() if item not in scope]
        scope_matrix.append(ScopeCoverageItem(item=item, present_in=present_in, missing_from=missing_from))

    # Price spread
    if prices:
        sorted_prices = sorted(prices)
        median_price = sorted_prices[len(sorted_prices) // 2]
        price_min, price_max = sorted_prices[0], sorted_prices[-1]
        range_pct = ((price_max - price_min) / price_min * 100) if price_min > 0 else 0
        price_spread = {
            "min": price_min,
            "max": price_max,
            "median": median_price,
            "range_pct": round(range_pct, 1),
        }
    else:
        price_spread = {"min": 0, "max": 0, "median": 0, "range_pct": 0}

    # Timeline spread
    if timelines:
        sorted_tl = sorted(timelines)
        timeline_spread = {
            "min_weeks": sorted_tl[0],
            "max_weeks": sorted_tl[-1],
            "median_weeks": sorted_tl[len(sorted_tl) // 2],
        }
    else:
        timeline_spread = {"min_weeks": 0, "max_weeks": 0, "median_weeks": 0}

    # Common exclusions (in all quotes)
    all_exclusion_sets = list(quote_exclusions.values())
    if all_exclusion_sets:
        common = all_exclusion_sets[0]
        for s in all_exclusion_sets[1:]:
            common = common & s
        common_exclusions = sorted(common)
    else:
        common_exclusions = []

    return QuoteComparisonInsight(
        request_id=request_id,
        scope_coverage_matrix=scope_matrix,
        price_spread=price_spread,
        timeline_spread=timeline_spread,
        common_exclusions=common_exclusions,
        ambiguity_flags=ambiguity_flags,
        quote_count=len(quotes),
    )
