"""
BatiConnect - Accessibility Evaluator (Programme AB)

SIA 500 accessibility assessment for Swiss buildings.
Evaluates conformity based on building data, flags unknowns,
estimates conformity cost, and determines legal obligation
(LHand trigger on renovations > 300k CHF).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.intervention import Intervention

# ---------------------------------------------------------------------------
# SIA 500 checks
# ---------------------------------------------------------------------------

SIA_500_CHECKS: list[dict[str, Any]] = [
    {
        "id": "entrance_level",
        "label": "Accès de plain-pied ou rampe",
        "weight": 3.0,
        "auto_check": lambda b: b.get("floors", 1) == 1 or b.get("has_elevator"),
    },
    {
        "id": "elevator",
        "label": "Ascenseur",
        "weight": 3.0,
        "auto_check": lambda b: b.get("has_elevator", False) or b.get("floors", 1) <= 2,
    },
    {
        "id": "door_width",
        "label": "Portes ≥90cm",
        "weight": 2.0,
        "auto_check": None,
    },
    {
        "id": "corridor_width",
        "label": "Couloirs ≥120cm",
        "weight": 2.0,
        "auto_check": None,
    },
    {
        "id": "bathroom_accessible",
        "label": "Sanitaires accessibles",
        "weight": 2.5,
        "auto_check": None,
    },
    {
        "id": "parking_accessible",
        "label": "Place handicapé",
        "weight": 1.5,
        "auto_check": None,
    },
    {
        "id": "signage",
        "label": "Signalétique adaptée",
        "weight": 1.0,
        "auto_check": None,
    },
    {
        "id": "emergency_accessible",
        "label": "Évacuation PMR",
        "weight": 2.5,
        "auto_check": None,
    },
]

# ---------------------------------------------------------------------------
# Cost estimates (CHF) per failing check
# ---------------------------------------------------------------------------

COST_ESTIMATES: dict[str, float] = {
    "entrance_level": 10000.0,
    "elevator": 75000.0,
    "door_width": 3500.0,
    "corridor_width": 8000.0,
    "bathroom_accessible": 22000.0,
    "parking_accessible": 5000.0,
    "signage": 2000.0,
    "emergency_accessible": 12000.0,
}

# LHand: renovation > 300k CHF triggers accessibility obligation
LHAND_RENOVATION_THRESHOLD_CHF = 300_000.0

# Grade thresholds (score → grade)
GRADE_THRESHOLDS: list[tuple[float, str]] = [
    (90, "A"),
    (75, "B"),
    (60, "C"),
    (40, "D"),
    (20, "E"),
    (0, "F"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _score_to_grade(score: float) -> str:
    """Convert 0-100 accessibility score to A-F grade."""
    for threshold, grade in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "F"


def _building_to_dict(building: Building) -> dict[str, Any]:
    """Extract building attributes into a dict for auto_check lambdas."""
    floors = (building.floors_above or 1) + (building.floors_below or 0)
    return {
        "floors": floors,
        "floors_above": building.floors_above or 1,
        "floors_below": building.floors_below or 0,
        "construction_year": building.construction_year,
        "building_type": building.building_type,
        "surface_area_m2": building.surface_area_m2,
        # has_elevator is not a direct column — infer from interventions later
        "has_elevator": False,
    }


async def estimate_conformity_cost(checks_failed: list[str]) -> float:
    """Estimate cost to fix accessibility gaps (CHF).

    Rampe: 5-15k, Ascenseur: 50-100k, Portes: 2-5k each, Sanitaires: 15-30k.
    """
    return sum(COST_ESTIMATES.get(c, 5000.0) for c in checks_failed)


# ---------------------------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------------------------


async def evaluate_accessibility(db: AsyncSession, building_id: UUID) -> dict:
    """Score 0-100 based on SIA 500 checks.

    Auto-evaluate what can be inferred (elevator, floors).
    Flag unknown checks as "non évalué".

    Returns:
        {
            score: 0-100,
            grade: A-F,
            checks: [{id, label, status: pass/fail/unknown, auto_evaluated: bool}],
            conformity_cost_estimate: float (CHF),
            legal_obligation: bool (true if renovation >300k CHF triggers LHand),
            computed_at: ISO timestamp,
        }
    """
    # Load building
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return {
            "score": 0,
            "grade": "F",
            "checks": [],
            "conformity_cost_estimate": 0.0,
            "legal_obligation": False,
            "computed_at": datetime.now(UTC).isoformat(),
            "error": "Building not found",
        }

    # Load interventions to detect elevator installation
    interv_q = await db.execute(select(Intervention).where(Intervention.building_id == building_id))
    interventions = list(interv_q.scalars().all())

    # Build data dict for auto_checks
    b_dict = _building_to_dict(building)

    # Detect elevator from interventions
    elevator_interventions = [
        i
        for i in interventions
        if i.status == "completed"
        and (
            "ascenseur" in (i.title or "").lower()
            or "elevator" in (i.title or "").lower()
            or i.intervention_type == "elevator"
        )
    ]
    if elevator_interventions:
        b_dict["has_elevator"] = True

    # Evaluate each check
    checks_result: list[dict] = []
    checks_failed: list[str] = []
    total_weight = 0.0
    earned_weight = 0.0
    unknown_weight = 0.0

    for check in SIA_500_CHECKS:
        check_id: str = check["id"]
        auto_fn: Callable | None = check["auto_check"]
        weight: float = check["weight"]
        total_weight += weight

        if auto_fn is not None:
            try:
                passed = auto_fn(b_dict)
            except Exception:
                passed = None

            if passed is True:
                checks_result.append(
                    {
                        "id": check_id,
                        "label": check["label"],
                        "status": "pass",
                        "auto_evaluated": True,
                    }
                )
                earned_weight += weight
            elif passed is False:
                checks_result.append(
                    {
                        "id": check_id,
                        "label": check["label"],
                        "status": "fail",
                        "auto_evaluated": True,
                    }
                )
                checks_failed.append(check_id)
            else:
                # None / exception → unknown
                checks_result.append(
                    {
                        "id": check_id,
                        "label": check["label"],
                        "status": "unknown",
                        "auto_evaluated": True,
                    }
                )
                unknown_weight += weight
        else:
            # Cannot auto-evaluate
            checks_result.append(
                {
                    "id": check_id,
                    "label": check["label"],
                    "status": "unknown",
                    "auto_evaluated": False,
                }
            )
            unknown_weight += weight

    # Score calculation:
    # - passed checks contribute full weight
    # - unknown checks contribute 50% (benefit of the doubt)
    # - failed checks contribute 0%
    effective_weight = earned_weight + (unknown_weight * 0.5)
    score = round((effective_weight / total_weight * 100) if total_weight > 0 else 0, 1)

    # Cost estimate for failed checks
    cost = await estimate_conformity_cost(checks_failed)

    # Legal obligation: check if any planned/completed renovation > 300k
    total_renovation_cost = sum(
        getattr(i, "estimated_cost_chf", 0) or 0
        for i in interventions
        if i.status in ("planned", "in_progress", "completed")
    )
    legal_obligation = total_renovation_cost > LHAND_RENOVATION_THRESHOLD_CHF

    return {
        "score": score,
        "grade": _score_to_grade(score),
        "checks": checks_result,
        "conformity_cost_estimate": cost,
        "legal_obligation": legal_obligation,
        "computed_at": datetime.now(UTC).isoformat(),
    }
