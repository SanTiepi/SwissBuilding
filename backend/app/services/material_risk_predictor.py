"""Material Risk Predictor — pollutant probability from material type + age.

Uses a knowledge matrix mapping (material_type, year_range) → pollutant
probabilities, based on Swiss construction practices and regulatory history.
Cross-references predictions with existing diagnostic data to flag
contradictions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building_element import BuildingElement
from app.models.diagnostic import Diagnostic
from app.models.material import Material
from app.models.sample import Sample
from app.models.zone import Zone

if TYPE_CHECKING:
    pass

# ── Material → Pollutant probability matrix ──────────────────────
# Key: (material_type, year_start, year_end) → {pollutant: probability}
MATERIAL_POLLUTANT_MATRIX: dict[tuple[str, int, int], dict[str, float]] = {
    ("dalle_vinyle", 1960, 1985): {"asbestos": 0.85, "hap": 0.30},
    ("joint_etancheite", 1955, 1980): {"pcb": 0.75, "asbestos": 0.20},
    ("colle_carrelage", 1960, 1990): {"asbestos": 0.70},
    ("flocage", 1950, 1978): {"asbestos": 0.95},
    ("peinture", 1900, 1960): {"lead": 0.80},
    ("peinture", 1960, 1980): {"lead": 0.40, "pcb": 0.15},
    ("enduit_facade", 1900, 1960): {"lead": 0.60},
    ("isolation_technique", 1950, 1990): {"asbestos": 0.65},
    ("revetement_sol", 1960, 1985): {"asbestos": 0.50, "hap": 0.25},
}


async def predict_pollutant_risk(
    material_type: str,
    installation_year: int | None,
) -> dict[str, float]:
    """Return {pollutant: probability} based on material type and year.

    If installation_year is None, returns union of all matching material
    entries with max probability per pollutant. If no match, returns empty dict.
    """
    if installation_year is None:
        # Aggregate: return max probability for each pollutant across all year ranges
        aggregated: dict[str, float] = {}
        for (mat, _start, _end), risks in MATERIAL_POLLUTANT_MATRIX.items():
            if mat == material_type:
                for pollutant, prob in risks.items():
                    aggregated[pollutant] = max(aggregated.get(pollutant, 0.0), prob)
        return aggregated

    result: dict[str, float] = {}
    for (mat, year_start, year_end), risks in MATERIAL_POLLUTANT_MATRIX.items():
        if mat == material_type and year_start <= installation_year <= year_end:
            for pollutant, prob in risks.items():
                result[pollutant] = max(result.get(pollutant, 0.0), prob)
    return result


async def predict_building_material_risks(
    db: AsyncSession,
    building_id: UUID,
) -> list[dict]:
    """For all materials in a building, predict pollutant risks.

    Queries zones → elements → materials, runs predictions, and cross-references
    with existing diagnostic samples to flag contradictions.

    Returns list of dicts: material_id, material_name, material_type,
    installation_year, predictions, contradictions.
    """
    # Load zones for this building
    zones = list((await db.execute(select(Zone).where(Zone.building_id == building_id))).scalars().all())
    zone_ids = [z.id for z in zones]

    if not zone_ids:
        return []

    # Load elements
    elements = list(
        (await db.execute(select(BuildingElement).where(BuildingElement.zone_id.in_(zone_ids)))).scalars().all()
    )
    element_ids = [e.id for e in elements]

    if not element_ids:
        return []

    # Load materials
    materials = list((await db.execute(select(Material).where(Material.element_id.in_(element_ids)))).scalars().all())

    if not materials:
        return []

    # Load existing diagnostic data for contradiction detection
    diagnostics = list(
        (await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))).scalars().all()
    )
    diag_ids = [d.id for d in diagnostics]

    existing_samples: list[Sample] = []
    if diag_ids:
        existing_samples = list(
            (await db.execute(select(Sample).where(Sample.diagnostic_id.in_(diag_ids)))).scalars().all()
        )

    # Build lookup: pollutant_type → confirmed status from samples
    confirmed_clean: set[str] = set()
    confirmed_present: set[str] = set()
    for s in existing_samples:
        pt = (s.pollutant_type or "").lower()
        if pt:
            if s.threshold_exceeded:
                confirmed_present.add(pt)
            elif s.threshold_exceeded is False and s.concentration is not None:
                confirmed_clean.add(pt)

    results: list[dict] = []
    for mat in materials:
        predictions = await predict_pollutant_risk(mat.material_type, mat.installation_year)

        # Detect contradictions
        contradictions: list[dict] = []
        for pollutant, prob in predictions.items():
            if pollutant in confirmed_clean and prob >= 0.5:
                contradictions.append(
                    {
                        "pollutant": pollutant,
                        "predicted_probability": prob,
                        "diagnostic_result": "clean",
                        "type": "prediction_vs_diagnostic",
                    }
                )
            elif pollutant in confirmed_present and prob < 0.2:
                contradictions.append(
                    {
                        "pollutant": pollutant,
                        "predicted_probability": prob,
                        "diagnostic_result": "present",
                        "type": "prediction_vs_diagnostic",
                    }
                )

        results.append(
            {
                "material_id": str(mat.id),
                "material_name": mat.name,
                "material_type": mat.material_type,
                "installation_year": mat.installation_year,
                "predictions": predictions,
                "contradictions": contradictions,
            }
        )

    return results
