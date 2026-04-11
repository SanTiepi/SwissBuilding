"""
RénoPredict — Remediation cost prediction service.

Computes fourchette estimates (min/median/max) for pollutant remediation
based on Swiss market averages, canton coefficients, and accessibility factors.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.remediation_cost_reference import RemediationCostReference
from app.schemas.cost_prediction import (
    CostBreakdownItem,
    CostPredictionRequest,
    CostPredictionResponse,
)

# ---------------------------------------------------------------------------
# Coefficients
# ---------------------------------------------------------------------------

CANTON_COEFFICIENTS: dict[str, float] = {
    "VD": 1.0,
    "GE": 1.15,
    "ZH": 1.10,
    "BE": 1.0,
    "VS": 0.95,
    "FR": 1.0,
}

ACCESSIBILITY_COEFFICIENTS: dict[str, float] = {
    "facile": 0.9,
    "normal": 1.0,
    "difficile": 1.3,
    "tres_difficile": 1.6,
}

# Condition multiplier — friable materials cost more to remove safely
CONDITION_COEFFICIENTS: dict[str, float] = {
    "bon": 0.85,
    "degrade": 1.0,
    "friable": 1.25,
}

BREAKDOWN_TEMPLATE: list[tuple[str, float]] = [
    ("Dépose / Intervention", 0.45),
    ("Traitement déchets", 0.20),
    ("Analyses contrôle", 0.08),
    ("Remise en état", 0.22),
    ("Frais généraux", 0.05),
]

# Valid enum values
VALID_POLLUTANTS = {"asbestos", "pcb", "lead", "hap", "radon", "pfas"}
VALID_CONDITIONS = {"bon", "degrade", "friable"}
VALID_ACCESSIBILITY = {"facile", "normal", "difficile", "tres_difficile"}


class CostPredictionError(Exception):
    """Raised when cost prediction cannot be computed."""

    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def _build_breakdown(
    cost_min: float,
    cost_median: float,
    cost_max: float,
) -> list[CostBreakdownItem]:
    """Split total cost into breakdown items."""
    return [
        CostBreakdownItem(
            label=label,
            percentage=round(pct * 100, 1),
            amount_min=round(cost_min * pct, 2),
            amount_median=round(cost_median * pct, 2),
            amount_max=round(cost_max * pct, 2),
        )
        for label, pct in BREAKDOWN_TEMPLATE
    ]


async def predict_cost(
    db: AsyncSession,
    request: CostPredictionRequest,
) -> CostPredictionResponse:
    """
    Compute a remediation cost fourchette.

    Steps:
    1. Validate inputs
    2. Lookup reference by pollutant + material (+ optional condition match)
    3. Apply condition coefficient
    4. Apply canton coefficient
    5. Apply accessibility coefficient
    6. Compute fourchette (min/median/max x surface x coefficients)
    7. Special case: radon = forfait (not per m2)
    8. Build breakdown
    9. Return response with disclaimer
    """
    # ── 1. Validate inputs ───────────────────────────────────────────
    pollutant = request.pollutant_type.lower().strip()
    if pollutant not in VALID_POLLUTANTS:
        raise CostPredictionError(
            f"Unknown pollutant_type: {request.pollutant_type}. Valid: {', '.join(sorted(VALID_POLLUTANTS))}",
        )

    condition = request.condition.lower().strip()
    if condition not in VALID_CONDITIONS:
        raise CostPredictionError(
            f"Unknown condition: {request.condition}. Valid: {', '.join(sorted(VALID_CONDITIONS))}",
        )

    accessibility = request.accessibility.lower().strip()
    if accessibility not in VALID_ACCESSIBILITY:
        raise CostPredictionError(
            f"Unknown accessibility: {request.accessibility}. Valid: {', '.join(sorted(VALID_ACCESSIBILITY))}",
        )

    material = request.material_type.lower().strip()
    canton = request.canton.upper().strip()

    # ── 2. Lookup reference ──────────────────────────────────────────
    # Try exact match first (pollutant + material + condition)
    result = await db.execute(
        select(RemediationCostReference).where(
            RemediationCostReference.pollutant_type == pollutant,
            RemediationCostReference.material_type == material,
            RemediationCostReference.active.is_(True),
        )
    )
    ref = result.scalar_one_or_none()

    # Fallback: try generic "other" material for this pollutant
    if ref is None:
        result = await db.execute(
            select(RemediationCostReference).where(
                RemediationCostReference.pollutant_type == pollutant,
                RemediationCostReference.material_type == "other",
                RemediationCostReference.active.is_(True),
            )
        )
        ref = result.scalar_one_or_none()

    if ref is None:
        raise CostPredictionError(
            f"No cost reference found for pollutant={pollutant}, material={material}. "
            "Contact support to add this reference.",
            status_code=404,
        )

    # ── 3. Coefficients ──────────────────────────────────────────────
    canton_coeff = CANTON_COEFFICIENTS.get(canton, 1.0)
    access_coeff = ACCESSIBILITY_COEFFICIENTS.get(accessibility, 1.0)
    condition_coeff = CONDITION_COEFFICIENTS.get(condition, 1.0)

    combined_coeff = canton_coeff * access_coeff * condition_coeff

    # ── 4. Compute fourchette ────────────────────────────────────────
    if ref.is_forfait:
        # Forfait: fixed price, not per m²
        base_min = float(ref.forfait_min or 0)
        base_median = float(ref.forfait_median or 0)
        base_max = float(ref.forfait_max or 0)
        cost_min = round(base_min * combined_coeff, 2)
        cost_median = round(base_median * combined_coeff, 2)
        cost_max = round(base_max * combined_coeff, 2)
        surface_used = 0.0
    else:
        # Per m² calculation
        surface = request.surface_m2
        if surface <= 0:
            raise CostPredictionError(
                "surface_m2 must be > 0 for non-forfait pollutant/material combinations.",
            )
        base_min = float(ref.cost_per_m2_min or 0)
        base_median = float(ref.cost_per_m2_median or 0)
        base_max = float(ref.cost_per_m2_max or 0)
        cost_min = round(base_min * surface * combined_coeff, 2)
        cost_median = round(base_median * surface * combined_coeff, 2)
        cost_max = round(base_max * surface * combined_coeff, 2)
        surface_used = surface

    # ── 5. Build response ────────────────────────────────────────────
    breakdown = _build_breakdown(cost_min, cost_median, cost_max)
    duration = ref.duration_days_estimate or 0

    return CostPredictionResponse(
        pollutant_type=pollutant,
        material_type=material,
        surface_m2=surface_used,
        cost_min=cost_min,
        cost_median=cost_median,
        cost_max=cost_max,
        duration_days=duration,
        complexity=ref.complexity,
        method=ref.method,
        canton_coefficient=canton_coeff,
        accessibility_coefficient=access_coeff,
        breakdown=breakdown,
    )
