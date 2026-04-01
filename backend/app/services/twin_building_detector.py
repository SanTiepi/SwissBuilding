"""
BatiConnect - Twin Building Detector

Finds buildings that are likely identical (same architect, same era, same street)
and suggests findings propagation between twins. In Swiss construction, entire
streets were often built by the same developer in the same period with identical
materials — if one has asbestos, the twin probably does too.
"""

from __future__ import annotations

import logging
import re
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scoring weights
# ---------------------------------------------------------------------------

WEIGHT_CONSTRUCTION_YEAR = 3
WEIGHT_SAME_STREET = 2
WEIGHT_SAME_FLOORS = 2
WEIGHT_SAME_TYPE = 1
WEIGHT_WITHIN_RADIUS = 1
WEIGHT_SAME_ORG = 0.5

MAX_SCORE = (
    WEIGHT_CONSTRUCTION_YEAR
    + WEIGHT_SAME_STREET
    + WEIGHT_SAME_FLOORS
    + WEIGHT_SAME_TYPE
    + WEIGHT_WITHIN_RADIUS
    + WEIGHT_SAME_ORG
)


def _extract_street(address: str) -> str:
    """Extract street name from address, removing the number.

    Examples:
        'Rue de Lausanne 15' -> 'Rue de Lausanne'
        'Avenue des Alpes 3a' -> 'Avenue des Alpes'
        'Chemin du Bois 7-9' -> 'Chemin du Bois'
    """
    # Remove trailing house numbers (digits possibly followed by letter)
    cleaned = re.sub(r"\s+\d+[\w\-]*$", "", address.strip())
    return cleaned.lower()


def _compute_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Approximate distance between two points in km using equirectangular projection.

    Good enough for distances under 1 km in Switzerland (~46-47 N latitude).
    """
    import math

    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = lat2_r - lat1_r
    dlon = math.radians(lon2 - lon1) * math.cos((lat1_r + lat2_r) / 2)
    return math.sqrt(dlat**2 + dlon**2) * 6371  # Earth radius in km


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def find_twin_buildings(
    db: AsyncSession,
    building_id: UUID,
    radius_m: float = 200,
) -> list[dict]:
    """Find buildings likely identical to this one.

    Criteria (scored):
    - Same construction_year +/- 3 years (weight 3)
    - Same street/address prefix (weight 2)
    - Same number of floors (weight 2)
    - Same building_type (weight 1)
    - Within radius_m meters (weight 1)
    - Same organization (weight 0.5)

    Returns sorted by similarity_score (descending):
    [{building_id, address, construction_year, similarity_score,
      matching_criteria, shared_diagnostics_count, recommendation}]
    """
    # ── Load source building ────────────────────────────────────
    result = await db.execute(select(Building).where(Building.id == building_id))
    source = result.scalar_one_or_none()
    if not source:
        raise ValueError(f"Building {building_id} not found")

    # ── Find candidates (same city, same canton) ────────────────
    query = select(Building).where(
        and_(
            Building.id != building_id,
            Building.canton == source.canton,
            Building.city == source.city,
            Building.status == "active",
        )
    )
    candidates_result = await db.execute(query)
    candidates = list(candidates_result.scalars().all())

    if not candidates:
        return []

    # ── Source diagnostics (for recommendation) ─────────────────
    source_diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    source_diagnostics = list(source_diag_result.scalars().all())

    # Get positive findings from source
    source_positive_materials: list[str] = []
    for diag in source_diagnostics:
        s_result = await db.execute(
            select(Sample).where(
                Sample.diagnostic_id == diag.id,
                Sample.threshold_exceeded.is_(True),
            )
        )
        for sample in s_result.scalars().all():
            mat = sample.material_category or sample.material_description
            if mat:
                source_positive_materials.append(mat)

    source_street = _extract_street(source.address)
    radius_km = radius_m / 1000

    # ── Score each candidate ────────────────────────────────────
    twins: list[dict] = []

    for candidate in candidates:
        score = 0.0
        matching_criteria: list[str] = []

        # 1. Construction year (+/- 3 years)
        if source.construction_year and candidate.construction_year:
            year_diff = abs(source.construction_year - candidate.construction_year)
            if year_diff <= 3:
                score += WEIGHT_CONSTRUCTION_YEAR
                matching_criteria.append(f"construction_year (±{year_diff})")

        # 2. Same street
        candidate_street = _extract_street(candidate.address)
        if source_street and candidate_street and source_street == candidate_street:
            score += WEIGHT_SAME_STREET
            matching_criteria.append("same_street")

        # 3. Same number of floors
        if (
            source.floors_above is not None
            and candidate.floors_above is not None
            and source.floors_above == candidate.floors_above
        ):
            score += WEIGHT_SAME_FLOORS
            matching_criteria.append("same_floors")

        # 4. Same building type
        if source.building_type == candidate.building_type:
            score += WEIGHT_SAME_TYPE
            matching_criteria.append("same_type")

        # 5. Within radius (needs coordinates)
        if (
            source.latitude is not None
            and source.longitude is not None
            and candidate.latitude is not None
            and candidate.longitude is not None
        ):
            dist = _compute_distance_km(
                source.latitude,
                source.longitude,
                candidate.latitude,
                candidate.longitude,
            )
            if dist <= radius_km:
                score += WEIGHT_WITHIN_RADIUS
                matching_criteria.append(f"within_{radius_m}m")

        # 6. Same organization
        if source.organization_id and candidate.organization_id and source.organization_id == candidate.organization_id:
            score += WEIGHT_SAME_ORG
            matching_criteria.append("same_organization")

        # Minimum threshold: at least 2 criteria must match
        if score < 2.0:
            continue

        # ── Count shared diagnostic types ───────────────────────
        candidate_diag_result = await db.execute(
            select(func.count())
            .select_from(Diagnostic)
            .where(
                Diagnostic.building_id == candidate.id,
                Diagnostic.diagnostic_type.in_([d.diagnostic_type for d in source_diagnostics])
                if source_diagnostics
                else Diagnostic.id.is_(None),
            )
        )
        shared_diag_count = candidate_diag_result.scalar() or 0

        # ── Generate recommendation ─────────────────────────────
        recommendation = _generate_recommendation(source, candidate, source_positive_materials, matching_criteria)

        twins.append(
            {
                "building_id": str(candidate.id),
                "address": candidate.address,
                "construction_year": candidate.construction_year,
                "similarity_score": round(score, 1),
                "max_score": MAX_SCORE,
                "matching_criteria": matching_criteria,
                "shared_diagnostics_count": shared_diag_count,
                "recommendation": recommendation,
            }
        )

    # Sort by similarity score descending
    twins.sort(key=lambda t: t["similarity_score"], reverse=True)
    return twins


def _generate_recommendation(
    source: Building,
    candidate: Building,
    source_positive_materials: list[str],
    matching_criteria: list[str],
) -> str | None:
    """Generate a French recommendation based on twin comparison."""
    if source_positive_materials:
        unique_materials = list(set(source_positive_materials))[:3]
        materials_str = ", ".join(unique_materials)
        return f"Ce bâtiment jumeau a un diagnostic positif dans {materials_str} — vérifiez le vôtre"

    criteria_count = len(matching_criteria)
    if criteria_count >= 4:
        return "Forte similarité structurelle — les diagnostics du bâtiment source pourraient s'appliquer à celui-ci"

    if "same_street" in matching_criteria and "construction_year" in [c.split(" ")[0] for c in matching_criteria]:
        return "Même rue et même époque de construction — matériaux probablement similaires"

    return None


async def propagate_findings(
    db: AsyncSession,
    source_building_id: UUID,
    target_building_id: UUID,
) -> list[dict]:
    """Suggest what findings from source could apply to target.

    For each positive sample in the source building, checks if the target
    is a twin and generates a propagation suggestion with confidence.
    """
    # ── Verify both buildings exist ─────────────────────────────
    source_result = await db.execute(select(Building).where(Building.id == source_building_id))
    source = source_result.scalar_one_or_none()
    if not source:
        raise ValueError(f"Source building {source_building_id} not found")

    target_result = await db.execute(select(Building).where(Building.id == target_building_id))
    target = target_result.scalar_one_or_none()
    if not target:
        raise ValueError(f"Target building {target_building_id} not found")

    # ── Compute twin score for confidence weighting ─────────────
    twins = await find_twin_buildings(db, source_building_id)
    twin_entry = next(
        (t for t in twins if t["building_id"] == str(target_building_id)),
        None,
    )

    if not twin_entry:
        return []

    similarity = twin_entry["similarity_score"] / MAX_SCORE

    # ── Fetch positive findings from source ─────────────────────
    source_diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == source_building_id))
    source_diagnostics = list(source_diag_result.scalars().all())

    suggestions: list[dict] = []

    for diag in source_diagnostics:
        s_result = await db.execute(
            select(Sample).where(
                Sample.diagnostic_id == diag.id,
                Sample.threshold_exceeded.is_(True),
            )
        )
        for sample in s_result.scalars().all():
            material = sample.material_category or sample.material_description or "matériau inconnu"
            pollutant = sample.pollutant_type or diag.diagnostic_type

            # Check if target already has a diagnostic for this pollutant
            existing = await db.execute(
                select(func.count())
                .select_from(Diagnostic)
                .where(
                    Diagnostic.building_id == target_building_id,
                    Diagnostic.diagnostic_type == diag.diagnostic_type,
                )
            )
            already_diagnosed = (existing.scalar() or 0) > 0

            confidence_label = "élevée" if similarity >= 0.7 else "moyenne" if similarity >= 0.4 else "faible"

            suggestions.append(
                {
                    "pollutant": pollutant,
                    "material": material,
                    "location": sample.location_detail or sample.location_room or sample.location_floor,
                    "source_diagnostic_id": str(diag.id),
                    "source_sample_id": str(sample.id),
                    "confidence": round(similarity, 2),
                    "confidence_label": confidence_label,
                    "already_diagnosed": already_diagnosed,
                    "suggestion": (
                        f"Probabilité {confidence_label} de {pollutant} dans {material} (basé sur bâtiment jumeau)"
                    ),
                }
            )

    return suggestions
