"""
BatiConnect - Component Age Tracker

Tracks the real age of each building component by combining construction year,
intervention data, and transformation episodes. Computes a "biological age"
(weighted average) vs chronological age.

Component lifespans are based on Swiss SIA 480 norms and industry standards.
"""

from __future__ import annotations

import logging
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.building_genealogy import TransformationEpisode
from app.models.intervention import Intervention

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Component definitions
# ---------------------------------------------------------------------------

COMPONENT_TYPES = [
    "structure",
    "roof",
    "facade",
    "windows",
    "plumbing",
    "electrical",
    "heating",
    "ventilation",
    "elevator",
    "insulation",
    "flooring",
    "kitchen",
    "bathroom",
]

# Expected lifespan in years (SIA 480 norms + industry standards)
EXPECTED_LIFESPANS: dict[str, int] = {
    "structure": 100,
    "roof": 40,
    "facade": 50,
    "windows": 30,
    "plumbing": 40,
    "electrical": 35,
    "heating": 25,
    "ventilation": 25,
    "elevator": 30,
    "insulation": 40,
    "flooring": 25,
    "kitchen": 25,
    "bathroom": 25,
}

# Weights for biological age computation (structural components weigh more)
COMPONENT_WEIGHTS: dict[str, float] = {
    "structure": 5.0,
    "roof": 3.0,
    "facade": 3.0,
    "windows": 2.0,
    "plumbing": 2.0,
    "electrical": 2.0,
    "heating": 2.0,
    "ventilation": 1.0,
    "elevator": 1.0,
    "insulation": 2.0,
    "flooring": 1.0,
    "kitchen": 1.0,
    "bathroom": 1.0,
}

# Keywords in intervention/transformation titles/types that map to components
_COMPONENT_KEYWORDS: dict[str, list[str]] = {
    "roof": ["toit", "toiture", "couverture", "roof", "dach"],
    "facade": ["façade", "facade", "crépi", "ravalement", "fassade"],
    "windows": ["fenêtre", "fenetre", "vitrage", "window", "fenster"],
    "plumbing": ["plomberie", "sanitaire", "canalisation", "tuyau", "plumbing"],
    "electrical": ["électri", "electri", "câblage", "tableau", "electrical"],
    "heating": ["chauffage", "chaudière", "chaudiere", "heating", "heizung"],
    "ventilation": ["ventilation", "aération", "aeration", "vmce", "lüftung"],
    "elevator": ["ascenseur", "lift", "elevator", "aufzug"],
    "insulation": ["isolation", "isolant", "insulation", "dämmung"],
    "flooring": ["sol", "parquet", "carrelage", "dalle", "flooring", "boden"],
    "kitchen": ["cuisine", "kitchen", "küche"],
    "bathroom": ["salle de bain", "douche", "bathroom", "badezimmer"],
    "structure": ["structure", "fondation", "dalle", "porteur", "gros oeuvre", "gros œuvre"],
}


def _match_component(text: str) -> str | None:
    """Match a text string to a component type using keywords."""
    text_lower = text.lower()
    for component, keywords in _COMPONENT_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return component
    return None


def _urgency_label(remaining_life: int, expected_lifespan: int) -> str:
    """Determine urgency based on remaining life as fraction of expected lifespan."""
    if remaining_life <= 0:
        return "critical"
    ratio = remaining_life / expected_lifespan if expected_lifespan > 0 else 0
    if ratio < 0.1:
        return "urgent"
    if ratio < 0.25:
        return "attention"
    return "ok"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def compute_component_ages(
    db: AsyncSession,
    building_id: UUID,
) -> dict:
    """Determine the real age of each component.

    Algorithm:
    1. Start with construction_year for all components
    2. Override with transformation episode data (if roof renovated in 2005, roof_year=2005)
    3. Override with intervention data
    4. Flag components with no renovation (original)

    Returns: {component: {year, age, source, is_original, expected_lifespan, remaining_life, urgency}}
    """
    # ── Load building ───────────────────────────────────────────
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        raise ValueError(f"Building {building_id} not found")

    today_year = date.today().year
    construction_year = building.construction_year

    # Initialize all components to construction year
    component_data: dict[str, dict] = {}
    for comp in COMPONENT_TYPES:
        base_year = construction_year
        component_data[comp] = {
            "year": base_year,
            "source": "construction" if base_year else "unknown",
            "is_original": True,
        }

    # ── Override from transformation episodes ───────────────────
    t_result = await db.execute(
        select(TransformationEpisode)
        .where(TransformationEpisode.building_id == building_id)
        .order_by(TransformationEpisode.period_start.asc().nullslast())
    )
    for t in t_result.scalars().all():
        if not t.period_start:
            continue
        year = t.period_start.year

        # Try to match to a specific component
        text = f"{t.title} {t.description or ''} {t.episode_type}"
        matched = _match_component(text)
        if matched:
            component_data[matched] = {
                "year": year,
                "source": "transformation",
                "is_original": False,
            }
        elif (
            t.episode_type in ("renovation", "modernization", "restoration")
            and t.spatial_scope
            and isinstance(t.spatial_scope, list)
        ):
            # Broad renovation may affect multiple components — check spatial_scope
            for scope_item in t.spatial_scope:
                scope_match = _match_component(str(scope_item))
                if scope_match:
                    component_data[scope_match] = {
                        "year": year,
                        "source": "transformation",
                        "is_original": False,
                    }

    # ── Override from interventions ─────────────────────────────
    i_result = await db.execute(
        select(Intervention)
        .where(Intervention.building_id == building_id)
        .order_by(Intervention.date_start.asc().nullslast())
    )
    for i in i_result.scalars().all():
        if not i.date_start:
            continue
        year = i.date_start.year

        text = f"{i.title} {i.description or ''} {i.intervention_type}"
        matched = _match_component(text)
        if matched:
            # Only update if this intervention is newer
            existing_year = component_data[matched].get("year")
            if existing_year is None or year > existing_year:
                component_data[matched] = {
                    "year": year,
                    "source": "intervention",
                    "is_original": False,
                }

    # ── Compute ages, remaining life, urgency ───────────────────
    result_dict: dict[str, dict] = {}
    for comp in COMPONENT_TYPES:
        data = component_data[comp]
        comp_year = data["year"]
        expected = EXPECTED_LIFESPANS[comp]

        if comp_year is not None:
            age = today_year - comp_year
            remaining = expected - age
        else:
            age = None
            remaining = None

        urgency = _urgency_label(remaining, expected) if remaining is not None else "unknown"

        result_dict[comp] = {
            "year": comp_year,
            "age": age,
            "source": data["source"],
            "is_original": data["is_original"],
            "expected_lifespan": expected,
            "remaining_life": remaining,
            "urgency": urgency,
        }

    return result_dict


async def compute_overall_building_age(
    db: AsyncSession,
    building_id: UUID,
) -> dict:
    """Compute weighted average age considering all components.

    "Biological age" vs chronological age.

    Returns: {chronological_age, biological_age, delta, verdict}
    verdict: "well_maintained" / "showing_age" / "needs_attention" / "critical"
    """
    # ── Load building ───────────────────────────────────────────
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        raise ValueError(f"Building {building_id} not found")

    today_year = date.today().year
    construction_year = building.construction_year

    if not construction_year:
        return {
            "chronological_age": None,
            "biological_age": None,
            "delta": None,
            "verdict": "unknown",
        }

    chronological_age = today_year - construction_year

    # ── Compute component ages ──────────────────────────────────
    component_ages = await compute_component_ages(db, building_id)

    # ── Weighted average ────────────────────────────────────────
    total_weight = 0.0
    weighted_age_sum = 0.0

    for comp in COMPONENT_TYPES:
        comp_data = component_ages.get(comp, {})
        age = comp_data.get("age")
        weight = COMPONENT_WEIGHTS.get(comp, 1.0)

        if age is not None:
            weighted_age_sum += age * weight
            total_weight += weight

    if total_weight > 0:
        biological_age = round(weighted_age_sum / total_weight, 1)
    else:
        biological_age = float(chronological_age)

    delta = round(biological_age - chronological_age, 1)

    # ── Verdict ─────────────────────────────────────────────────
    if chronological_age == 0:
        ratio = 1.0
    else:
        ratio = biological_age / chronological_age

    if ratio <= 0.7:
        verdict = "well_maintained"
    elif ratio <= 0.9:
        verdict = "showing_age"
    elif ratio <= 1.1:
        verdict = "needs_attention"
    else:
        verdict = "critical"

    return {
        "chronological_age": chronological_age,
        "biological_age": biological_age,
        "delta": delta,
        "verdict": verdict,
    }
