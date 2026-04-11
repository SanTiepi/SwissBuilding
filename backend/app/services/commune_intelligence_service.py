"""
BatiConnect - Commune Intelligence Service

Provides commune-level demographic and fiscal intelligence for buildings.
Uses CommuneProfile reference data matched via BFS number (municipality_ofs).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.commune_profile import CommuneProfile

# Swiss national median income (2023 OFS estimate)
_NATIONAL_MEDIAN_INCOME = 56000  # CHF/year


async def get_commune_profile(db: AsyncSession, commune_number: int) -> CommuneProfile | None:
    """Lookup commune by BFS number."""
    result = await db.execute(
        select(CommuneProfile).where(
            CommuneProfile.commune_number == commune_number,
            CommuneProfile.active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def get_commune_for_building(db: AsyncSession, building_id: UUID) -> CommuneProfile | None:
    """Resolve commune from building's municipality_ofs field."""
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None or building.municipality_ofs is None:
        return None
    return await get_commune_profile(db, building.municipality_ofs)


async def compute_fiscal_attractiveness(db: AsyncSession, commune_number: int) -> dict | None:
    """Compare commune's tax situation vs canton peers.

    Returns:
        {
            commune: str,
            canton: str,
            tax_multiplier: float,
            canton_average: float,
            comparison: "below_average" | "at_average" | "above_average",
            yearly_tax_estimate_for_income: {50000: X, 80000: Y, 100000: Z},
            ranking_in_canton: "N of M",
            nearby_cheaper: [{commune, multiplier, savings_estimate}],
        }
    """
    profile = await get_commune_profile(db, commune_number)
    if profile is None:
        return None

    # Fetch all active communes in the same canton
    result = await db.execute(
        select(CommuneProfile).where(
            CommuneProfile.canton == profile.canton,
            CommuneProfile.active.is_(True),
            CommuneProfile.tax_multiplier.isnot(None),
        )
    )
    canton_peers = result.scalars().all()

    if not canton_peers:
        return None

    multipliers = [c.tax_multiplier for c in canton_peers]
    canton_avg = round(sum(multipliers) / len(multipliers), 4)

    # Determine comparison label
    tolerance = 0.02
    if profile.tax_multiplier < canton_avg - tolerance:
        comparison = "below_average"
    elif profile.tax_multiplier > canton_avg + tolerance:
        comparison = "above_average"
    else:
        comparison = "at_average"

    # Rank within canton (1 = lowest multiplier = most attractive)
    sorted_peers = sorted(canton_peers, key=lambda c: c.tax_multiplier)
    rank = next((i + 1 for i, c in enumerate(sorted_peers) if c.commune_number == commune_number), len(sorted_peers))

    # Simple tax estimate: income * multiplier * base_rate (simplified)
    # Swiss communal tax ≈ canton_base_rate * multiplier * income
    # We use a simplified 10% cantonal base rate for illustration
    base_rate = 0.10
    tax_estimates = {}
    for income in [50000, 80000, 100000]:
        tax_estimates[income] = round(income * base_rate * profile.tax_multiplier, 2)

    # Find cheaper communes in same canton
    nearby_cheaper = []
    for peer in sorted_peers:
        if peer.commune_number == commune_number:
            break
        savings_100k = round(
            100000 * base_rate * (profile.tax_multiplier - peer.tax_multiplier),
            2,
        )
        nearby_cheaper.append(
            {
                "commune": peer.name,
                "multiplier": peer.tax_multiplier,
                "savings_estimate": savings_100k,
            }
        )

    return {
        "commune": profile.name,
        "canton": profile.canton,
        "tax_multiplier": profile.tax_multiplier,
        "canton_average": canton_avg,
        "comparison": comparison,
        "yearly_tax_estimate_for_income": tax_estimates,
        "ranking_in_canton": f"{rank} of {len(canton_peers)}",
        "nearby_cheaper": nearby_cheaper[:5],  # Top 5 cheaper options
    }


def _classify_income(median_income: int | None) -> str:
    """Classify income vs national median."""
    if median_income is None:
        return "unknown"
    if median_income >= _NATIONAL_MEDIAN_INCOME * 1.15:
        return "high"
    if median_income <= _NATIONAL_MEDIAN_INCOME * 0.85:
        return "low"
    return "medium"


def _classify_market_tension(vacancy_rate: float | None) -> str:
    """Classify market tension from vacancy rate."""
    if vacancy_rate is None:
        return "unknown"
    if vacancy_rate < 0.5:
        return "high"
    if vacancy_rate < 1.0:
        return "moderate"
    return "low"


def _classify_demographic_trend(growth_pct: float | None) -> str:
    """Classify demographic trend from 5-year population growth."""
    if growth_pct is None:
        return "unknown"
    if growth_pct > 0.5:
        return "growing"
    if growth_pct < -0.2:
        return "declining"
    return "stable"


def _classify_fiscal_pressure(tax_multiplier: float | None, canton: str | None) -> str:
    """Classify fiscal pressure. Accounts for GE cantonal structure (lower multipliers)."""
    if tax_multiplier is None:
        return "unknown"
    # Geneva has a different tax system with lower multipliers
    if canton == "GE":
        if tax_multiplier > 0.45:
            return "high"
        if tax_multiplier < 0.43:
            return "low"
        return "moderate"
    # Standard cantons
    if tax_multiplier > 1.55:
        return "high"
    if tax_multiplier < 1.35:
        return "low"
    return "moderate"


def _compute_attractiveness_scores(profile: CommuneProfile) -> dict:
    """Compute 0-10 attractiveness scores for different buyer personas."""
    scores = {"family_attractiveness": 5.0, "retiree_attractiveness": 5.0, "investor_attractiveness": 5.0}

    # Family: lower tax + higher income + low vacancy (stable area)
    if profile.tax_multiplier is not None:
        # Lower tax = better for families (normalize around 1.4 midpoint for non-GE)
        if profile.canton == "GE":
            tax_score = max(0, min(10, (0.50 - profile.tax_multiplier) * 50 + 5))
        else:
            tax_score = max(0, min(10, (1.60 - profile.tax_multiplier) * 10 + 5))
        scores["family_attractiveness"] = round(tax_score, 1)

    if profile.homeowner_rate_pct is not None:
        scores["family_attractiveness"] = round(
            (scores["family_attractiveness"] + min(10, profile.homeowner_rate_pct / 3)) / 2, 1
        )

    # Retiree: moderate tax + aging/mixed demographic + good financial health
    retiree_base = 5.0
    if profile.dominant_age_group == "aging":
        retiree_base += 1.5
    elif profile.dominant_age_group == "mixed":
        retiree_base += 0.5
    if profile.financial_health in ("excellent", "good"):
        retiree_base += 1.0
    if profile.vacancy_rate_pct is not None and profile.vacancy_rate_pct > 0.5:
        retiree_base += 0.5  # More availability
    scores["retiree_attractiveness"] = round(min(10, retiree_base), 1)

    # Investor: low vacancy (rental demand) + population growth + lower homeowner rate
    investor_base = 5.0
    if profile.vacancy_rate_pct is not None:
        investor_base += max(0, (1.0 - profile.vacancy_rate_pct) * 3)
    if profile.population_growth_pct is not None and profile.population_growth_pct > 0.5:
        investor_base += 1.5
    if profile.homeowner_rate_pct is not None and profile.homeowner_rate_pct < 20:
        investor_base += 1.0  # More renters = more rental demand
    scores["investor_attractiveness"] = round(min(10, investor_base), 1)

    return scores


async def compute_socioeconomic_profile(db: AsyncSession, building_id: UUID) -> dict | None:
    """Build socioeconomic context from commune data for a building.

    Returns:
        {
            commune: {name, canton, population},
            income_level: "high" | "medium" | "low",
            market_tension: "high" | "moderate" | "low",
            demographic_trend: "growing" | "stable" | "declining",
            fiscal_pressure: "high" | "moderate" | "low",
            scores: {
                family_attractiveness: 0-10,
                retiree_attractiveness: 0-10,
                investor_attractiveness: 0-10,
            },
        }
    """
    profile = await get_commune_for_building(db, building_id)
    if profile is None:
        return None

    return {
        "commune": {
            "name": profile.name,
            "canton": profile.canton,
            "population": profile.population,
        },
        "income_level": _classify_income(profile.median_income),
        "market_tension": _classify_market_tension(profile.vacancy_rate_pct),
        "demographic_trend": _classify_demographic_trend(profile.population_growth_pct),
        "fiscal_pressure": _classify_fiscal_pressure(profile.tax_multiplier, profile.canton),
        "scores": _compute_attractiveness_scores(profile),
    }
