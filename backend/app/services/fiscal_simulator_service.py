"""
SwissBuildingOS - Fiscal Simulator Service

Tax deduction estimation and subsidy eligibility for renovation works.
Covers cantonal tax deduction rules (VD/GE/BE/ZH/VS) and federal/cantonal
subsidy programs (Programme Batiments, cantonal energy programs).

Returns net cost, ROI, and detailed breakdown for renovation planning.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building

# ---------------------------------------------------------------------------
# Canton tax deduction rules
# ---------------------------------------------------------------------------

CANTON_TAX_DEDUCTIONS: dict[str, dict] = {
    "VD": {"renovation_deductible": True, "max_deduction_pct": 1.0, "energy_bonus": True},
    "GE": {"renovation_deductible": True, "max_deduction_pct": 1.0, "energy_bonus": True},
    "BE": {"renovation_deductible": True, "max_deduction_pct": 1.0, "energy_bonus": False},
    "ZH": {"renovation_deductible": True, "max_deduction_pct": 0.8, "energy_bonus": True},
    "VS": {"renovation_deductible": True, "max_deduction_pct": 1.0, "energy_bonus": False},
}

# Default marginal tax rate for deduction calculation (simplified)
DEFAULT_MARGINAL_TAX_RATE = 0.30

# Energy bonus: additional deduction percentage for energy-improving measures
ENERGY_BONUS_RATE = 0.10

# ---------------------------------------------------------------------------
# Subsidy programs
# ---------------------------------------------------------------------------

SUBSIDY_PROGRAMS: dict[str, dict] = {
    "programme_batiments": {
        "name": "Programme Batiments (federal)",
        "max_amount": 60000,
        "eligible": ["facade_insulation", "roof_insulation", "window_replacement", "heat_pump"],
        "cantons": None,  # All cantons
        "rate": 0.20,  # 20% of eligible costs
    },
    "programme_energie_vd": {
        "name": "Programme Energie VD",
        "max_amount": 40000,
        "eligible": ["heat_pump", "solar_panels"],
        "cantons": ["VD"],
        "rate": 0.25,
    },
    "programme_energie_ge": {
        "name": "Programme Energie GE",
        "max_amount": 35000,
        "eligible": ["heat_pump", "solar_panels"],
        "cantons": ["GE"],
        "rate": 0.25,
    },
}


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


def _compute_tax_deduction(
    renovation_cost: float,
    canton: str,
    measures: list[str],
) -> dict:
    """Compute the tax deduction amount based on cantonal rules."""
    rules = CANTON_TAX_DEDUCTIONS.get(canton)
    if rules is None or not rules["renovation_deductible"]:
        return {
            "deductible_amount": 0.0,
            "tax_saving": 0.0,
            "energy_bonus_applied": False,
            "canton": canton,
            "max_deduction_pct": 0.0,
        }

    deductible_pct = rules["max_deduction_pct"]
    deductible_amount = renovation_cost * deductible_pct

    # Energy bonus: additional rate for energy-improving measures
    energy_measures = {"facade_insulation", "roof_insulation", "window_replacement", "heat_pump", "solar_panels"}
    has_energy_measures = bool(set(measures) & energy_measures)
    energy_bonus_applied = rules["energy_bonus"] and has_energy_measures

    effective_tax_rate = DEFAULT_MARGINAL_TAX_RATE
    if energy_bonus_applied:
        effective_tax_rate += ENERGY_BONUS_RATE

    tax_saving = round(deductible_amount * effective_tax_rate, 2)

    return {
        "deductible_amount": round(deductible_amount, 2),
        "tax_saving": tax_saving,
        "energy_bonus_applied": energy_bonus_applied,
        "canton": canton,
        "max_deduction_pct": deductible_pct,
    }


def _compute_subsidies(
    renovation_cost: float,
    canton: str,
    measures: list[str],
) -> list[dict]:
    """Determine eligible subsidy programs and amounts."""
    subsidies = []
    for prog_id, prog in SUBSIDY_PROGRAMS.items():
        # Canton filter
        if prog["cantons"] is not None and canton not in prog["cantons"]:
            continue

        # Check measure overlap
        eligible_measures = [m for m in measures if m in prog["eligible"]]
        if not eligible_measures:
            continue

        # Calculate amount: rate * renovation_cost, capped at max_amount
        raw_amount = renovation_cost * prog["rate"]
        amount = min(raw_amount, float(prog["max_amount"]))

        subsidies.append(
            {
                "program_id": prog_id,
                "program_name": prog["name"],
                "amount": round(amount, 2),
                "max_amount": float(prog["max_amount"]),
                "eligible_measures": eligible_measures,
                "eligible": True,
            }
        )

    return subsidies


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def simulate_fiscal_impact(
    db: AsyncSession,
    building_id: UUID,
    renovation_cost: float,
    canton: str,
    measures: list[str],
) -> dict:
    """Simulate the full fiscal impact of a renovation.

    Return: {
        building_id, gross_cost, tax_deduction, subsidy_total, net_cost,
        energy_savings_annual, roi_years,
        breakdown: {deduction_detail, subsidies: [{program, amount, eligible}]},
        computed_at
    }
    """
    await _get_building(db, building_id)  # Validate building exists

    # Tax deduction
    deduction_detail = _compute_tax_deduction(renovation_cost, canton, measures)
    tax_deduction = deduction_detail["tax_saving"]

    # Subsidies
    subsidies = _compute_subsidies(renovation_cost, canton, measures)
    subsidy_total = sum(s["amount"] for s in subsidies)

    # Net cost
    net_cost = max(renovation_cost - tax_deduction - subsidy_total, 0.0)

    # Estimate energy savings (simplified: 15% of renovation cost as annual savings)
    # In real usage this would come from energy_trajectory_service
    energy_savings_annual = round(renovation_cost * 0.03, 2)  # ~3% of investment as annual energy savings

    # ROI: years to break even from energy savings
    roi_years = round(net_cost / energy_savings_annual, 1) if energy_savings_annual > 0 else 0.0

    return {
        "building_id": str(building_id),
        "gross_cost": round(renovation_cost, 2),
        "tax_deduction": round(tax_deduction, 2),
        "subsidy_total": round(subsidy_total, 2),
        "net_cost": round(net_cost, 2),
        "energy_savings_annual": energy_savings_annual,
        "roi_years": roi_years,
        "breakdown": {
            "deduction_detail": deduction_detail,
            "subsidies": subsidies,
        },
        "computed_at": datetime.now(UTC).isoformat(),
    }


async def check_subsidy_eligibility(
    db: AsyncSession,
    building_id: UUID,
    canton: str,
) -> list[dict]:
    """Return all eligible subsidy programs with max amounts for the building's canton.

    Checks all known programs against canton; returns both eligible and
    ineligible with reasons.
    """
    await _get_building(db, building_id)  # Validate building exists

    results = []

    for prog_id, prog in SUBSIDY_PROGRAMS.items():
        # Canton filter
        canton_eligible = prog["cantons"] is None or canton in prog["cantons"]

        if canton_eligible:
            results.append(
                {
                    "program_id": prog_id,
                    "program_name": prog["name"],
                    "max_amount": float(prog["max_amount"]),
                    "eligible": True,
                    "eligible_measures": prog["eligible"],
                    "reason": None,
                }
            )
        else:
            results.append(
                {
                    "program_id": prog_id,
                    "program_name": prog["name"],
                    "max_amount": float(prog["max_amount"]),
                    "eligible": False,
                    "eligible_measures": prog["eligible"],
                    "reason": f"Canton {canton} not covered by this program",
                }
            )

    return results
