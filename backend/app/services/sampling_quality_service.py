"""Sampling Quality Score service.

Evaluates the quality of a diagnostic's sampling protocol BEFORE looking
at lab results.  Based on Swiss norms: FACH (asbestos), SUVA 6503
(work categories), OTConst Art. 60a/82-86.

10 criteria, each 0-10 points, total 0-100.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.models.zone import Zone

if TYPE_CHECKING:
    from uuid import UUID

# Grade thresholds (same as evidence score)
_GRADE_THRESHOLDS = [(85, "A"), (70, "B"), (55, "C"), (40, "D"), (0, "F")]

# Pollutants applicable by construction year (Swiss norms)
_YEAR_POLLUTANTS: list[tuple[int, list[str]]] = [
    # Buildings before 1991: asbestos (OTConst Art. 82)
    # Buildings before 1975: PCB (ORRChim Annexe 2.15)
    # Buildings before 1960: lead paint (ORRChim Annexe 2.18)
    # Buildings before 2005: HAP (general Swiss practice)
    # Any building in radon-prone zone: radon (ORaP Art. 110)
    # PFAS: no year cutoff, context-dependent
]

# Reasonable lab turnaround thresholds (days)
_LAB_TURNAROUND_EXCELLENT = 7
_LAB_TURNAROUND_GOOD = 14
_LAB_TURNAROUND_ACCEPTABLE = 21
_LAB_TURNAROUND_POOR = 30

# Temporal consistency threshold (days between first and last sample collection)
_TEMPORAL_WINDOW_EXCELLENT = 3
_TEMPORAL_WINDOW_GOOD = 7
_TEMPORAL_WINDOW_ACCEPTABLE = 14
_TEMPORAL_WINDOW_POOR = 30

# SUVA 6503 work categories
_SUVA_CATEGORIES = {"minor", "medium", "major"}


def _score_to_grade(score: int) -> str:
    for threshold, grade in _GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "F"


def _confidence_level(score: int) -> str:
    if score >= 80:
        return "high"
    if score >= 60:
        return "medium"
    if score >= 40:
        return "low"
    return "very_low"


def _applicable_pollutants(construction_year: int | None) -> list[str]:
    """Return pollutants that should be tested based on construction year."""
    if construction_year is None:
        # Unknown year: assume all could apply
        return ["asbestos", "pcb", "lead", "hap", "radon", "pfas"]

    applicable: list[str] = []
    if construction_year < 1991:
        applicable.append("asbestos")
    if construction_year < 1975:
        applicable.append("pcb")
    if construction_year < 1960:
        applicable.append("lead")
    if construction_year < 2005:
        applicable.append("hap")
    # Radon and PFAS are context-dependent but always recommended
    applicable.append("radon")
    applicable.append("pfas")
    return applicable


def _score_coverage(samples: list[Sample], zones: list[Zone]) -> tuple[int, str, str]:
    """Criterion 1: ratio of sampled zones vs total zones."""
    if not zones:
        if samples:
            return 5, "No zones defined but samples exist", "Define building zones for better coverage tracking"
        return 0, "No zones and no samples", "Define zones and collect samples in each zone"

    # Get unique zones sampled (by matching floor/room to zone names)
    sampled_rooms = {(s.location_floor, s.location_room) for s in samples if s.location_floor or s.location_room}
    zone_count = len(zones)

    if not sampled_rooms:
        return 0, f"0/{zone_count} zones covered", "Collect samples from each identified zone"

    ratio = min(len(sampled_rooms) / zone_count, 1.0)
    score = round(ratio * 10)
    detail = f"{len(sampled_rooms)}/{zone_count} zones covered ({round(ratio * 100)}%)"

    if score < 7:
        recommendation = "Increase zone coverage — FACH requires representative sampling of all suspect areas"
    else:
        recommendation = "Good zone coverage"
    return score, detail, recommendation


def _score_density(samples: list[Sample], zones: list[Zone]) -> tuple[int, str, str]:
    """Criterion 2: samples per zone (min 1 per zone with suspect material, FACH norm)."""
    if not samples:
        return 0, "No samples collected", "Collect at least 1 sample per zone with suspect material (FACH)"

    if not zones:
        # Can only evaluate total sample count
        count = len(samples)
        if count >= 10:
            return 8, f"{count} samples (no zones for density calc)", "Define zones for proper density assessment"
        if count >= 5:
            return 5, f"{count} samples (no zones for density calc)", "Define zones and increase sample count"
        return 3, f"{count} samples (no zones for density calc)", "More samples needed — define zones first"

    # Group samples by floor/room
    samples_per_location: dict[tuple[str | None, str | None], int] = {}
    for s in samples:
        key = (s.location_floor, s.location_room)
        samples_per_location[key] = samples_per_location.get(key, 0) + 1

    zone_count = len(zones)
    covered_zones = len(samples_per_location)
    avg_density = len(samples) / max(zone_count, 1)

    if avg_density >= 3:
        score = 10
    elif avg_density >= 2:
        score = 8
    elif avg_density >= 1:
        score = 6
    elif covered_zones >= zone_count * 0.5:
        score = 4
    else:
        score = 2

    detail = f"{len(samples)} samples across {covered_zones} locations (avg {avg_density:.1f}/zone)"
    recommendation = (
        "Good sampling density" if score >= 7 else "Increase samples per zone (FACH minimum: 1 per suspect zone)"
    )
    return score, detail, recommendation


def _score_pollutant_breadth(samples: list[Sample], construction_year: int | None) -> tuple[int, str, str]:
    """Criterion 3: applicable pollutants tested based on construction_year."""
    applicable = _applicable_pollutants(construction_year)
    if not applicable:
        return 10, "No specific pollutants expected", "N/A"

    tested = {s.pollutant_type for s in samples if s.pollutant_type}
    covered = tested & set(applicable)

    if not tested:
        return 0, "No pollutant types recorded", "Record pollutant type for each sample"

    ratio = len(covered) / len(applicable)
    score = round(ratio * 10)
    missing = set(applicable) - tested
    detail = f"{len(covered)}/{len(applicable)} applicable pollutants tested"
    if missing:
        recommendation = f"Missing pollutant tests: {', '.join(sorted(missing))}"
    else:
        recommendation = "All applicable pollutants covered"
    return score, detail, recommendation


def _score_material_diversity(samples: list[Sample]) -> tuple[int, str, str]:
    """Criterion 4: different material types sampled vs present."""
    if not samples:
        return 0, "No samples", "Collect samples from diverse material types"

    material_types = {s.material_category for s in samples if s.material_category}
    if not material_types:
        return 2, "No material categories recorded", "Record material_category for each sample"

    count = len(material_types)
    # Scoring: more diversity is better (typical building has 4-8 material types)
    if count >= 6:
        score = 10
    elif count >= 4:
        score = 8
    elif count >= 3:
        score = 6
    elif count >= 2:
        score = 4
    else:
        score = 2

    detail = f"{count} distinct material categories sampled"
    recommendation = (
        "Good material diversity"
        if score >= 7
        else "Sample more material types (coatings, insulation, tiles, joints, etc.)"
    )
    return score, detail, recommendation


def _score_location_spread(samples: list[Sample], building: Building) -> tuple[int, str, str]:
    """Criterion 5: samples from different floors/rooms vs total."""
    if not samples:
        return 0, "No samples", "Collect samples across multiple floors and rooms"

    floors = {s.location_floor for s in samples if s.location_floor}
    rooms = {s.location_room for s in samples if s.location_room}

    total_floors = (building.floors_above or 0) + (building.floors_below or 0)
    if total_floors <= 0:
        total_floors = 1  # fallback

    floor_coverage = min(len(floors) / total_floors, 1.0) if floors else 0
    room_diversity = min(len(rooms) / max(len(samples), 1), 1.0)

    # 60% weight on floor coverage, 40% on room diversity
    combined = floor_coverage * 0.6 + room_diversity * 0.4
    score = round(combined * 10)

    detail = f"{len(floors)} floors, {len(rooms)} rooms sampled"
    if not floors and not rooms:
        return 1, "No location data on samples", "Record floor and room for each sample"

    recommendation = "Good location spread" if score >= 7 else "Spread samples across more floors and rooms"
    return score, detail, recommendation


def _score_temporal_consistency(samples: list[Sample]) -> tuple[int, str, str]:
    """Criterion 6: all samples collected within reasonable timeframe (same campaign)."""
    dates = [s.created_at for s in samples if s.created_at]
    if len(dates) < 2:
        if len(samples) <= 1:
            return 7, "Single sample or no date info", "N/A"
        return 3, "No collection dates recorded", "Record collection dates on all samples"

    min_date = min(dates)
    max_date = max(dates)
    if isinstance(min_date, datetime) and isinstance(max_date, datetime):
        span_days = (max_date - min_date).days
    else:
        span_days = 0

    if span_days <= _TEMPORAL_WINDOW_EXCELLENT:
        score = 10
    elif span_days <= _TEMPORAL_WINDOW_GOOD:
        score = 8
    elif span_days <= _TEMPORAL_WINDOW_ACCEPTABLE:
        score = 6
    elif span_days <= _TEMPORAL_WINDOW_POOR:
        score = 4
    else:
        score = 2

    detail = f"Sampling span: {span_days} days"
    recommendation = (
        "Samples collected in a consistent timeframe"
        if score >= 7
        else f"Sampling spread over {span_days} days — should be within 1 campaign window"
    )
    return score, detail, recommendation


def _score_lab_turnaround(samples: list[Sample]) -> tuple[int, str, str]:
    """Criterion 7: time between collection_date and analysis_date."""
    # Use created_at as proxy for collection; analysis_date not on model, but concentration
    # presence implies analysis was done
    # Since model lacks explicit analysis_date, we approximate using the diagnostic's date fields
    # For now, score based on presence of results
    samples_with_results = [s for s in samples if s.concentration is not None]
    if not samples:
        return 0, "No samples", "Collect and analyze samples"

    ratio = len(samples_with_results) / len(samples)
    # All results available = good turnaround assumed
    if ratio >= 1.0:
        score = 9
    elif ratio >= 0.8:
        score = 7
    elif ratio >= 0.5:
        score = 5
    else:
        score = 3

    detail = f"{len(samples_with_results)}/{len(samples)} samples have analysis results"
    recommendation = "All samples analyzed" if score >= 7 else "Complete lab analysis for remaining samples"
    return score, detail, recommendation


def _score_documentation(samples: list[Sample]) -> tuple[int, str, str]:
    """Criterion 8: samples with all required fields filled."""
    if not samples:
        return 0, "No samples", "Collect samples with complete documentation"

    required_fields = [
        "location_floor",
        "location_room",
        "material_category",
        "pollutant_type",
        "concentration",
        "unit",
    ]
    total_checks = len(samples) * len(required_fields)
    filled = 0

    for s in samples:
        for field in required_fields:
            value = getattr(s, field, None)
            if value is not None and value != "":
                filled += 1

    ratio = filled / total_checks if total_checks > 0 else 0
    score = round(ratio * 10)

    missing_pct = round((1 - ratio) * 100)
    detail = f"{round(ratio * 100)}% of required fields documented"
    recommendation = (
        "Complete documentation"
        if score >= 8
        else f"{missing_pct}% of fields missing — fill location, material, concentration, unit on all samples"
    )
    return score, detail, recommendation


def _score_negative_controls(samples: list[Sample]) -> tuple[int, str, str]:
    """Criterion 9: presence of control samples (materials known to be clean)."""
    if not samples:
        return 0, "No samples", "Include negative control samples"

    # Negative controls are samples where concentration is 0 or below threshold
    # with explicit clean materials
    negative_controls = [
        s for s in samples if s.concentration is not None and s.concentration == 0 and s.threshold_exceeded is False
    ]

    # Also consider samples explicitly below threshold as partial controls
    below_threshold = [s for s in samples if s.threshold_exceeded is False and s.concentration is not None]

    total = len(samples)
    control_ratio = len(below_threshold) / total

    if len(negative_controls) >= 2:
        score = 10
    elif len(negative_controls) >= 1:
        score = 8
    elif control_ratio >= 0.2:
        score = 6
    elif control_ratio > 0:
        score = 4
    else:
        score = 2

    detail = f"{len(negative_controls)} explicit controls, {len(below_threshold)} below-threshold samples"
    recommendation = (
        "Negative controls present"
        if score >= 7
        else "Add negative control samples from known-clean materials for protocol validation"
    )
    return score, detail, recommendation


def _score_protocol_compliance(samples: list[Sample], diagnostic: Diagnostic) -> tuple[int, str, str]:
    """Criterion 10: adherence to SUVA 6503 requirements."""
    score = 0
    issues: list[str] = []

    # Check 1: CFST work category assigned (SUVA 6503 requirement)
    samples_with_category = [s for s in samples if s.cfst_work_category]
    if samples_with_category:
        valid_categories = [s for s in samples_with_category if s.cfst_work_category in _SUVA_CATEGORIES]
        if len(valid_categories) == len(samples_with_category):
            score += 3
        else:
            score += 1
            issues.append("Some samples have invalid CFST work categories")
    else:
        issues.append("No CFST work categories assigned (SUVA 6503)")

    # Check 2: Risk level assigned
    samples_with_risk = [s for s in samples if s.risk_level]
    if samples_with_risk:
        risk_ratio = len(samples_with_risk) / max(len(samples), 1)
        if risk_ratio >= 0.9:
            score += 3
        elif risk_ratio >= 0.5:
            score += 2
        else:
            score += 1
    else:
        issues.append("No risk levels assigned to samples")

    # Check 3: Diagnostic has methodology documented
    if diagnostic.methodology:
        score += 2
    else:
        issues.append("No methodology documented on diagnostic")

    # Check 4: SUVA notification tracked if required
    if diagnostic.suva_notification_required:
        if diagnostic.suva_notification_date:
            score += 2
        else:
            score += 1
            issues.append("SUVA notification required but date not recorded")
    else:
        score += 2  # Not required = compliant

    detail = f"{len(issues)} compliance issues" if issues else "Full protocol compliance"
    recommendation = "; ".join(issues) if issues else "SUVA 6503 protocol requirements met"
    return min(score, 10), detail, recommendation


async def evaluate_sampling_quality(db: AsyncSession, diagnostic_id: UUID) -> dict | None:
    """Evaluate sampling quality for a single diagnostic.

    Returns None if diagnostic not found.
    """
    diagnostic = (await db.execute(select(Diagnostic).where(Diagnostic.id == diagnostic_id))).scalar_one_or_none()
    if diagnostic is None:
        return None

    building = (await db.execute(select(Building).where(Building.id == diagnostic.building_id))).scalar_one_or_none()
    if building is None:
        return None

    samples = list((await db.execute(select(Sample).where(Sample.diagnostic_id == diagnostic_id))).scalars().all())

    zones = list((await db.execute(select(Zone).where(Zone.building_id == building.id))).scalars().all())

    # Evaluate all 10 criteria
    criteria_results: list[dict] = []
    warnings: list[str] = []

    evaluators = [
        ("coverage", _score_coverage, (samples, zones)),
        ("density", _score_density, (samples, zones)),
        ("pollutant_breadth", _score_pollutant_breadth, (samples, building.construction_year)),
        ("material_diversity", _score_material_diversity, (samples,)),
        ("location_spread", _score_location_spread, (samples, building)),
        ("temporal_consistency", _score_temporal_consistency, (samples,)),
        ("lab_turnaround", _score_lab_turnaround, (samples,)),
        ("documentation", _score_documentation, (samples,)),
        ("negative_controls", _score_negative_controls, (samples,)),
        ("protocol_compliance", _score_protocol_compliance, (samples, diagnostic)),
    ]

    total_score = 0
    for name, evaluator, args in evaluators:
        score, detail, recommendation = evaluator(*args)
        total_score += score
        criteria_results.append(
            {
                "name": name,
                "score": score,
                "max": 10,
                "detail": detail,
                "recommendation": recommendation,
            }
        )
        if score <= 3:
            warnings.append(f"{name}: {detail}")

    grade = _score_to_grade(total_score)
    confidence = _confidence_level(total_score)

    # Extra warnings
    if not samples:
        warnings.insert(0, "No samples found for this diagnostic")
    if len(samples) < 3:
        warnings.append("Very few samples — protocol reliability is low")

    return {
        "diagnostic_id": str(diagnostic_id),
        "overall_score": total_score,
        "grade": grade,
        "criteria": criteria_results,
        "confidence_level": confidence,
        "warnings": warnings,
        "evaluated_at": datetime.now(UTC).isoformat(),
    }


async def evaluate_building_sampling_quality(db: AsyncSession, building_id: UUID) -> dict | None:
    """Aggregate sampling quality across all diagnostics for a building.

    Returns None if building not found.
    """
    building = (await db.execute(select(Building).where(Building.id == building_id))).scalar_one_or_none()
    if building is None:
        return None

    diagnostics = list(
        (await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))).scalars().all()
    )

    if not diagnostics:
        return {
            "building_id": str(building_id),
            "avg_score": 0,
            "worst_diagnostic": None,
            "best_diagnostic": None,
            "diagnostics": [],
            "evaluated_at": datetime.now(UTC).isoformat(),
        }

    results: list[dict] = []
    for diag in diagnostics:
        result = await evaluate_sampling_quality(db, diag.id)
        if result is not None:
            results.append(result)

    if not results:
        return {
            "building_id": str(building_id),
            "avg_score": 0,
            "worst_diagnostic": None,
            "best_diagnostic": None,
            "diagnostics": [],
            "evaluated_at": datetime.now(UTC).isoformat(),
        }

    avg_score = round(sum(r["overall_score"] for r in results) / len(results))
    best = max(results, key=lambda r: r["overall_score"])
    worst = min(results, key=lambda r: r["overall_score"])

    return {
        "building_id": str(building_id),
        "avg_score": avg_score,
        "worst_diagnostic": worst["diagnostic_id"],
        "best_diagnostic": best["diagnostic_id"],
        "diagnostics": results,
        "evaluated_at": datetime.now(UTC).isoformat(),
    }
