"""Market valuation service — Programme R.

Property market intelligence with Swiss reference data.
Estimates building market value, rental yield, and renovation value impact
using canton-level price/m2 benchmarks and multi-factor adjustments.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample

# ---------------------------------------------------------------------------
# Swiss average prices per m2 by canton and building type (2024-2025, CHF)
# ---------------------------------------------------------------------------

PRICE_PER_M2_REFERENCE: dict[str, dict[str, int]] = {
    "VD": {"apartment": 8500, "house": 7200, "commercial": 5500},
    "GE": {"apartment": 12500, "house": 10000, "commercial": 8000},
    "ZH": {"apartment": 11000, "house": 9500, "commercial": 7500},
    "BE": {"apartment": 6500, "house": 5800, "commercial": 4500},
    "VS": {"apartment": 5500, "house": 4800, "commercial": 3500},
    "FR": {"apartment": 6000, "house": 5200, "commercial": 4000},
    "BS": {"apartment": 8000, "house": 7000, "commercial": 6000},
}

_DEFAULT_PRICES: dict[str, int] = {"apartment": 7000, "house": 6000, "commercial": 5000}

# ---------------------------------------------------------------------------
# Adjustment factor tables
# ---------------------------------------------------------------------------

ADJUSTMENT_FACTORS: dict[str, Any] = {
    "age": {
        (0, 10): 1.0,
        (10, 30): 0.95,
        (30, 50): 0.85,
        (50, 80): 0.75,
        (80, 999): 0.65,
    },
    "energy_class": {
        "A": 1.08,
        "B": 1.04,
        "C": 1.0,
        "D": 0.96,
        "E": 0.92,
        "F": 0.85,
        "G": 0.78,
    },
    "pollutant": {
        "clean": 1.0,
        "minor": 0.95,
        "major": 0.85,
        "critical": 0.70,
    },
}

# Rental yield canton averages (gross %)
_CANTON_AVG_YIELD: dict[str, float] = {
    "VD": 3.2,
    "GE": 2.8,
    "ZH": 2.9,
    "BE": 3.8,
    "VS": 4.0,
    "FR": 3.5,
    "BS": 3.1,
}
_DEFAULT_AVG_YIELD = 3.5

# Average rent per m2/month by canton (CHF) for yield estimation
_RENT_PER_M2_MONTH: dict[str, float] = {
    "VD": 20.0,
    "GE": 26.0,
    "ZH": 24.0,
    "BE": 17.0,
    "VS": 15.0,
    "FR": 16.0,
    "BS": 19.0,
}
_DEFAULT_RENT_M2 = 18.0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _fetch_building(db: AsyncSession, building_id: UUID) -> Building:
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")
    return building


def _surface(building: Building) -> float:
    return building.surface_area_m2 or 200.0


def _building_age(building: Building) -> int:
    year = building.construction_year
    if not year:
        return 40  # conservative default
    return max(0, datetime.now(UTC).year - year)


def _map_building_type(raw: str) -> str:
    """Map building_type from the model to price reference category."""
    raw_lower = (raw or "").lower()
    if "commercial" in raw_lower or "office" in raw_lower or "industrial" in raw_lower:
        return "commercial"
    if "house" in raw_lower or "villa" in raw_lower or "maison" in raw_lower:
        return "house"
    return "apartment"  # default for residential, mixed, etc.


def _get_price_per_m2(canton: str, building_type: str) -> int:
    """Look up price/m2 for canton + type, with fallback."""
    canton_data = PRICE_PER_M2_REFERENCE.get(canton.upper(), _DEFAULT_PRICES)
    if isinstance(canton_data, dict):
        return canton_data.get(building_type, canton_data.get("apartment", 7000))
    return 7000


def _age_factor(age: int) -> float:
    for (lo, hi), factor in ADJUSTMENT_FACTORS["age"].items():
        if lo <= age < hi:
            return factor
    return 0.65


def _energy_factor(energy_class: str | None) -> float:
    if not energy_class:
        return 1.0
    return ADJUSTMENT_FACTORS["energy_class"].get(energy_class.upper(), 1.0)


async def _pollutant_severity(db: AsyncSession, building_id: UUID) -> str:
    """Determine pollutant severity: clean / minor / major / critical."""
    stmt = (
        select(Sample)
        .join(Diagnostic, Diagnostic.id == Sample.diagnostic_id)
        .where(
            Diagnostic.building_id == building_id,
            Diagnostic.status.in_(["completed", "validated"]),
        )
    )
    result = await db.execute(stmt)
    samples = list(result.scalars().all())

    exceeded = [s for s in samples if s.threshold_exceeded]
    if not exceeded:
        return "clean"

    risk_levels = {s.risk_level for s in exceeded if s.risk_level}
    if "critical" in risk_levels:
        return "critical"
    if len(exceeded) >= 3 or "high" in risk_levels:
        return "major"
    return "minor"


def _pollutant_factor(severity: str) -> float:
    return ADJUSTMENT_FACTORS["pollutant"].get(severity, 1.0)


def _location_factor(canton: str) -> float:
    """Premium cantons get a small location bonus."""
    premium = {"GE": 1.05, "ZH": 1.04, "BS": 1.02, "VD": 1.01}
    return premium.get(canton.upper(), 1.0)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def estimate_market_value(db: AsyncSession, building_id: UUID) -> dict[str, Any]:
    """Estimate building market value with multi-factor adjustments.

    Returns: {estimated_value_min, estimated_value_median, estimated_value_max,
              adjustments: [{factor, impact_pct, reason}],
              price_per_m2, canton_average, comparison}
    """
    building = await _fetch_building(db, building_id)
    surface = _surface(building)
    canton = (building.canton or "").upper()
    btype = _map_building_type(building.building_type or "")
    price_m2 = _get_price_per_m2(canton, btype)

    base_value = surface * price_m2

    # Compute adjustments
    age = _building_age(building)
    af = _age_factor(age)

    # Energy class from source_metadata_json if available
    meta = building.source_metadata_json or {}
    e_class = meta.get("energy_class") or meta.get("cecb_class")
    ef = _energy_factor(e_class)

    severity = await _pollutant_severity(db, building_id)
    pf = _pollutant_factor(severity)

    lf = _location_factor(canton)

    # Condition factor from renovation year
    if building.renovation_year and (datetime.now(UTC).year - building.renovation_year) < 10:
        cf = 1.05
    else:
        cf = 1.0

    combined = af * ef * pf * lf * cf
    median_value = base_value * combined

    adjustments = []
    if af != 1.0:
        adjustments.append(
            {
                "factor": "age",
                "impact_pct": round((af - 1.0) * 100, 1),
                "reason": f"Bâtiment de {age} ans",
            }
        )
    if ef != 1.0:
        adjustments.append(
            {
                "factor": "energy",
                "impact_pct": round((ef - 1.0) * 100, 1),
                "reason": f"Classe énergétique {e_class}",
            }
        )
    if pf != 1.0:
        adjustments.append(
            {
                "factor": "pollutant",
                "impact_pct": round((pf - 1.0) * 100, 1),
                "reason": f"Pollution: {severity}",
            }
        )
    if lf != 1.0:
        adjustments.append(
            {
                "factor": "location",
                "impact_pct": round((lf - 1.0) * 100, 1),
                "reason": f"Canton {canton} premium",
            }
        )
    if cf != 1.0:
        adjustments.append(
            {
                "factor": "condition",
                "impact_pct": round((cf - 1.0) * 100, 1),
                "reason": "Rénové récemment",
            }
        )

    # Canton average for comparison
    canton_avg_m2 = _get_price_per_m2(canton, "apartment")
    canton_avg_value = surface * canton_avg_m2

    if canton_avg_value > 0:
        comparison = (
            "above" if median_value > canton_avg_value else "below" if median_value < canton_avg_value else "at"
        )
    else:
        comparison = "unknown"

    return {
        "building_id": str(building_id),
        "estimated_value_min": round(median_value * 0.85),
        "estimated_value_median": round(median_value),
        "estimated_value_max": round(median_value * 1.15),
        "adjustments": adjustments,
        "price_per_m2": price_m2,
        "canton_average": canton_avg_m2,
        "comparison": comparison,
        "surface_m2": surface,
        "canton": canton,
        "building_type": btype,
        "generated_at": datetime.now(UTC).isoformat(),
    }


async def estimate_rental_yield(db: AsyncSession, building_id: UUID) -> dict[str, Any]:
    """Gross rental yield estimate.

    annual_rent_estimate = surface * avg_rent_per_m2_month * 12
    yield = annual_rent / market_value
    """
    building = await _fetch_building(db, building_id)
    surface = _surface(building)
    canton = (building.canton or "").upper()

    rent_m2 = _RENT_PER_M2_MONTH.get(canton, _DEFAULT_RENT_M2)
    annual_rent = surface * rent_m2 * 12

    # Get market value for yield calc
    valuation = await estimate_market_value(db, building_id)
    market_value = valuation["estimated_value_median"]

    gross_yield = (annual_rent / market_value * 100) if market_value > 0 else 0.0
    canton_avg_yield = _CANTON_AVG_YIELD.get(canton, _DEFAULT_AVG_YIELD)

    if gross_yield > canton_avg_yield + 0.5:
        recommendation = "Rendement supérieur à la moyenne cantonale — bon potentiel locatif"
    elif gross_yield < canton_avg_yield - 0.5:
        recommendation = "Rendement inférieur à la moyenne cantonale — envisager optimisation"
    else:
        recommendation = "Rendement dans la moyenne cantonale"

    comparison = "above" if gross_yield > canton_avg_yield else "below" if gross_yield < canton_avg_yield else "at"

    return {
        "building_id": str(building_id),
        "annual_rent_estimate": round(annual_rent),
        "market_value": market_value,
        "gross_yield_pct": round(gross_yield, 2),
        "canton_avg_yield": canton_avg_yield,
        "comparison": comparison,
        "recommendation": recommendation,
        "rent_per_m2_month": rent_m2,
        "surface_m2": surface,
        "generated_at": datetime.now(UTC).isoformat(),
    }


async def estimate_renovation_value_impact(
    db: AsyncSession,
    building_id: UUID,
    renovation_cost: float,
) -> dict[str, Any]:
    """How much does renovation increase value.

    Renovation improves condition factor and may clear pollutant penalty.
    """
    building = await _fetch_building(db, building_id)

    # Current value
    current = await estimate_market_value(db, building_id)
    current_value = current["estimated_value_median"]

    # Post-renovation: assume condition improved + pollutant cleaned
    surface = _surface(building)
    canton = (building.canton or "").upper()
    btype = _map_building_type(building.building_type or "")
    price_m2 = _get_price_per_m2(canton, btype)
    base_value = surface * price_m2

    age = _building_age(building)
    # After renovation, age penalty reduced by ~50%
    af = 1.0 - (1.0 - _age_factor(age)) * 0.5

    meta = building.source_metadata_json or {}
    e_class = meta.get("energy_class") or meta.get("cecb_class")
    # Renovation typically improves energy 1-2 classes
    ef = min(_energy_factor(e_class) + 0.04, 1.08)

    lf = _location_factor(canton)
    cf = 1.05  # recently renovated

    # Assume pollutants remediated
    pf = 1.0

    post_value = round(base_value * af * ef * pf * lf * cf)
    value_increase = max(0, post_value - current_value)
    net_gain = value_increase - renovation_cost
    roi_pct = (net_gain / renovation_cost * 100) if renovation_cost > 0 else 0.0

    return {
        "building_id": str(building_id),
        "current_value": current_value,
        "post_renovation_value": post_value,
        "value_increase": value_increase,
        "renovation_cost": round(renovation_cost),
        "net_gain": round(net_gain),
        "roi_pct": round(roi_pct, 1),
        "generated_at": datetime.now(UTC).isoformat(),
    }
