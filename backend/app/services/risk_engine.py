"""
SwissBuildingOS - Risk Engine Service

Core business logic for calculating pollutant risk scores for buildings.
Implements the complete risk assessment algorithm based on Swiss construction
history, cantonal data, building types, and renovation exposure profiles.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.services.rule_resolver import resolve_risk_calibration

# ---------------------------------------------------------------------------
# Base probability functions by construction year
# ---------------------------------------------------------------------------


def calculate_asbestos_base_probability(construction_year: int | None) -> float:
    if construction_year is None:
        return 0.5
    if construction_year < 1920:
        return 0.05
    if construction_year < 1940:
        return 0.15
    if construction_year < 1955:
        return 0.40
    if construction_year < 1970:
        return 0.85
    if construction_year < 1980:
        return 0.90
    if construction_year < 1990:
        return 0.60
    if construction_year < 1995:
        return 0.15
    return 0.02


def calculate_pcb_base_probability(construction_year: int | None) -> float:
    if construction_year is None:
        return 0.3
    if construction_year < 1955:
        return 0.02
    if construction_year < 1970:
        return 0.55
    if construction_year < 1980:
        return 0.70
    if construction_year < 1986:
        return 0.40
    return 0.02


def calculate_lead_base_probability(construction_year: int | None) -> float:
    if construction_year is None:
        return 0.3
    if construction_year < 1920:
        return 0.85
    if construction_year < 1940:
        return 0.75
    if construction_year < 1960:
        return 0.60
    if construction_year < 1980:
        return 0.35
    if construction_year < 2000:
        return 0.10
    return 0.02


def calculate_hap_base_probability(construction_year: int | None) -> float:
    if construction_year is None:
        return 0.25
    if construction_year < 1940:
        return 0.20
    if construction_year < 1970:
        return 0.55
    if construction_year < 1985:
        return 0.35
    return 0.05


def calculate_radon_base_probability(canton: str) -> float:
    HIGH_RADON = {"GR", "TI", "VS", "UR", "NW", "OW", "JU"}
    MEDIUM_RADON = {"BE", "FR", "NE", "SZ", "GL", "AI", "AR", "SG", "BL", "SO"}
    if canton in HIGH_RADON:
        return 0.60
    if canton in MEDIUM_RADON:
        return 0.30
    return 0.10


# ---------------------------------------------------------------------------
# Modifiers
# ---------------------------------------------------------------------------

BUILDING_TYPE_MODIFIERS = {
    "asbestos": {"industrial": 1.3, "commercial": 1.15, "public": 1.2, "residential": 1.0, "mixed": 1.1},
    "pcb": {"industrial": 1.2, "commercial": 1.3, "public": 1.15, "residential": 0.9, "mixed": 1.05},
    "lead": {"residential": 1.1, "industrial": 0.9, "commercial": 0.95, "public": 1.2, "mixed": 1.0},
    "hap": {"industrial": 1.2, "commercial": 1.0, "public": 0.9, "residential": 1.1, "mixed": 1.0},
}

RENOVATION_EXPOSURE = {
    "full_renovation": {"asbestos": 1.0, "pcb": 1.0, "lead": 1.0, "hap": 1.0},
    "partial_interior": {"asbestos": 0.8, "pcb": 0.4, "lead": 0.9, "hap": 0.7},
    "roof": {"asbestos": 0.9, "pcb": 0.2, "lead": 0.3, "hap": 0.6},
    "facade": {"asbestos": 0.7, "pcb": 0.9, "lead": 0.5, "hap": 0.3},
    "bathroom": {"asbestos": 0.8, "pcb": 0.3, "lead": 0.7, "hap": 0.5},
    "kitchen": {"asbestos": 0.7, "pcb": 0.3, "lead": 0.6, "hap": 0.4},
    "flooring": {"asbestos": 0.9, "pcb": 0.1, "lead": 0.2, "hap": 0.8},
    "windows": {"asbestos": 0.6, "pcb": 0.7, "lead": 0.4, "hap": 0.1},
}


def apply_modifiers(base: float, building_type: str, pollutant: str) -> float:
    """Apply building-type modifier to a base probability, clamped to [0, 1]."""
    pollutant_modifiers = BUILDING_TYPE_MODIFIERS.get(pollutant, {})
    modifier = pollutant_modifiers.get(building_type, 1.0)
    return max(0.0, min(1.0, base * modifier))


def apply_renovation_modifier(base: float, renovation_type: str, pollutant: str) -> float:
    """Apply renovation-type exposure modifier to a base probability, clamped to [0, 1]."""
    exposure = RENOVATION_EXPOSURE.get(renovation_type, {})
    modifier = exposure.get(pollutant, 1.0)
    return max(0.0, min(1.0, base * modifier))


# ---------------------------------------------------------------------------
# Aggregate scoring helpers
# ---------------------------------------------------------------------------


def calculate_overall_risk_level(scores: dict[str, float]) -> str:
    """
    Determine overall risk level from individual pollutant probabilities.

    Returns one of: critical, high, medium, low, unknown.
    """
    if not scores:
        return "unknown"

    max_score = max(scores.values())

    if max_score >= 0.80:
        return "critical"
    if max_score >= 0.55:
        return "high"
    if max_score >= 0.25:
        return "medium"
    return "low"


def calculate_confidence(
    has_diagnostics: bool,
    neighbor_count: int,
    year_known: bool,
) -> float:
    """
    Calculate confidence score (0-1) for a risk assessment.

    Factors:
      - Construction year known: +0.30
      - Has at least one diagnostic: +0.40
      - Neighbor data available: up to +0.30 scaled by count (max at 5+)
    """
    confidence = 0.0

    if year_known:
        confidence += 0.30

    if has_diagnostics:
        confidence += 0.40

    if neighbor_count > 0:
        neighbor_factor = min(neighbor_count / 5.0, 1.0) * 0.30
        confidence += neighbor_factor

    return round(min(confidence, 1.0), 2)


# ---------------------------------------------------------------------------
# Neighbor sample adjustment
# ---------------------------------------------------------------------------


def _adjust_with_neighbor_samples(
    base_scores: dict[str, float],
    neighbor_samples: list[Sample],
) -> dict[str, float]:
    """
    Adjust base probabilities using actual sample results from nearby buildings.

    If neighbors have confirmed positive samples for a pollutant the probability
    is nudged upward; confirmed negatives nudge it downward.  The adjustment
    weight is kept moderate (max +/-0.15) so that direct diagnostics always
    dominate.
    """
    if not neighbor_samples:
        return base_scores

    pollutant_positives: dict[str, int] = {}
    pollutant_totals: dict[str, int] = {}

    for sample in neighbor_samples:
        pt = (sample.pollutant_type or "").lower()
        if pt not in base_scores:
            continue
        pollutant_totals[pt] = pollutant_totals.get(pt, 0) + 1
        if sample.threshold_exceeded:
            pollutant_positives[pt] = pollutant_positives.get(pt, 0) + 1

    adjusted = dict(base_scores)
    for pollutant, total in pollutant_totals.items():
        if total == 0:
            continue
        positive_rate = pollutant_positives.get(pollutant, 0) / total
        # Shift probability toward observed rate, capped at +/- 0.15
        shift = (positive_rate - adjusted[pollutant]) * 0.30
        shift = max(-0.15, min(0.15, shift))
        adjusted[pollutant] = max(0.0, min(1.0, adjusted[pollutant] + shift))

    return adjusted


# ---------------------------------------------------------------------------
# Diagnostic override
# ---------------------------------------------------------------------------


def _apply_diagnostic_override(
    scores: dict[str, float],
    samples: list[Sample],
) -> dict[str, float]:
    """
    If the building already has diagnostic samples, override model probabilities
    with evidence-based values.

    - Confirmed positive (threshold_exceeded=True) -> set to 0.95
    - Confirmed negative (threshold_exceeded=False) -> set to 0.05
    - If mixed results for same pollutant -> set to 0.70
    """
    if not samples:
        return scores

    pollutant_results: dict[str, set[bool]] = {}
    for sample in samples:
        pt = (sample.pollutant_type or "").lower()
        if pt in scores and sample.threshold_exceeded is not None:
            pollutant_results.setdefault(pt, set()).add(sample.threshold_exceeded)

    adjusted = dict(scores)
    for pollutant, results in pollutant_results.items():
        if True in results and False in results:
            adjusted[pollutant] = 0.70
        elif True in results:
            adjusted[pollutant] = 0.95
        elif False in results:
            adjusted[pollutant] = 0.05

    return adjusted


# ---------------------------------------------------------------------------
# Main risk calculation
# ---------------------------------------------------------------------------


async def calculate_building_risk(
    db: AsyncSession,
    building: Building,
    neighbor_samples: list[Sample] | None = None,
) -> BuildingRiskScore:
    """
    Calculate complete risk profile for a building.

    Steps:
      1. Compute base probabilities from construction year / canton.
      2. Apply building-type modifiers.
      3. Adjust with neighbor sample data (if available).
      4. Override with own diagnostic results (if any).
      5. Compute overall risk level and confidence.
      6. Return a (non-persisted) BuildingRiskScore instance.
    """
    construction_year = building.construction_year
    canton = building.canton or ""
    building_type = (building.building_type or "residential").lower()

    # Step 1: base probabilities (hardcoded fallback)
    scores = {
        "asbestos": calculate_asbestos_base_probability(construction_year),
        "pcb": calculate_pcb_base_probability(construction_year),
        "lead": calculate_lead_base_probability(construction_year),
        "hap": calculate_hap_base_probability(construction_year),
        "radon": calculate_radon_base_probability(canton),
    }

    # Step 1b: override with pack-driven calibration when available
    jurisdiction_id = getattr(building, "jurisdiction_id", None)
    if jurisdiction_id is not None:
        for pollutant in ("asbestos", "pcb", "lead", "hap", "radon"):
            calibration = await resolve_risk_calibration(db, jurisdiction_id, pollutant)
            if calibration and calibration.get("base_probability") is not None:
                scores[pollutant] = calibration["base_probability"]

    # Step 2: building-type modifiers (radon is not affected by building type)
    for pollutant in ("asbestos", "pcb", "lead", "hap"):
        scores[pollutant] = apply_modifiers(scores[pollutant], building_type, pollutant)

    # Step 3: neighbor adjustment
    if neighbor_samples:
        scores = _adjust_with_neighbor_samples(scores, neighbor_samples)

    # Step 4: own diagnostics
    result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building.id))
    diagnostics = result.scalars().all()

    own_samples: list[Sample] = []
    has_diagnostics = len(diagnostics) > 0
    if has_diagnostics:
        diag_ids = [d.id for d in diagnostics]
        sample_result = await db.execute(select(Sample).where(Sample.diagnostic_id.in_(diag_ids)))
        own_samples = list(sample_result.scalars().all())
        scores = _apply_diagnostic_override(scores, own_samples)

    # Step 5: confidence & overall level
    year_known = construction_year is not None
    neighbor_count = len(neighbor_samples) if neighbor_samples else 0
    confidence = calculate_confidence(has_diagnostics, neighbor_count, year_known)
    overall_risk_level = calculate_overall_risk_level(scores)

    # Build factors detail
    factors = {
        "construction_year": construction_year,
        "canton": canton,
        "building_type": building_type,
        "has_diagnostics": has_diagnostics,
        "own_sample_count": len(own_samples),
        "neighbor_sample_count": neighbor_count,
        "pack_driven": jurisdiction_id is not None,
        "scores_detail": {k: round(v, 4) for k, v in scores.items()},
    }

    # Step 6: build BuildingRiskScore (not yet persisted)
    risk_score = BuildingRiskScore(
        building_id=building.id,
        asbestos_probability=round(scores["asbestos"], 4),
        pcb_probability=round(scores["pcb"], 4),
        lead_probability=round(scores["lead"], 4),
        hap_probability=round(scores["hap"], 4),
        radon_probability=round(scores["radon"], 4),
        overall_risk_level=overall_risk_level,
        confidence=confidence,
        factors_json=factors,
        data_source="diagnostic" if has_diagnostics else "model",
    )

    return risk_score


async def update_risk_score(
    db: AsyncSession,
    building_id: UUID,
) -> BuildingRiskScore:
    """
    Fetch the building, calculate its risk score, and upsert into the database.
    Returns the persisted BuildingRiskScore.
    """
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one()

    new_score = await calculate_building_risk(db, building)

    # Check for existing score
    existing_result = await db.execute(select(BuildingRiskScore).where(BuildingRiskScore.building_id == building_id))
    existing = existing_result.scalar_one_or_none()

    if existing:
        existing.asbestos_probability = new_score.asbestos_probability
        existing.pcb_probability = new_score.pcb_probability
        existing.lead_probability = new_score.lead_probability
        existing.hap_probability = new_score.hap_probability
        existing.radon_probability = new_score.radon_probability
        existing.overall_risk_level = new_score.overall_risk_level
        existing.confidence = new_score.confidence
        existing.factors_json = new_score.factors_json
        existing.data_source = new_score.data_source
        await db.flush()
        await db.refresh(existing)
        return existing
    else:
        db.add(new_score)
        await db.flush()
        await db.refresh(new_score)
        return new_score
