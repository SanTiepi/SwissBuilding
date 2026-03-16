"""Diagnostic quality evaluation service.

Evaluates diagnostic quality across 5 dimensions:
- Sample density (samples per zone)
- Pollutant coverage (5 canonical types checked)
- Methodology completeness
- Documentation quality
- Lab accreditation status
"""

import uuid
from statistics import median

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.sample import Sample
from app.models.user import User
from app.models.zone import Zone

ALL_POLLUTANTS = ["asbestos", "pcb", "lead", "hap", "radon"]

# Weights for overall score (sum = 1.0)
W_SAMPLE_DENSITY = 0.30
W_POLLUTANT_COVERAGE = 0.25
W_METHODOLOGY = 0.15
W_DOCUMENTATION = 0.15
W_LAB_ACCREDITATION = 0.15


def _score_to_grade(score: float) -> str:
    """Convert a 0-100 score to A-F grade."""
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 40:
        return "D"
    if score >= 20:
        return "E"
    return "F"


async def evaluate_diagnostic_quality(
    db: AsyncSession,
    diagnostic_id: uuid.UUID,
) -> dict | None:
    """Evaluate quality of a single diagnostic. Returns None if not found."""
    # Fetch diagnostic
    result = await db.execute(select(Diagnostic).where(Diagnostic.id == diagnostic_id))
    diagnostic = result.scalar_one_or_none()
    if diagnostic is None:
        return None

    # Fetch samples for this diagnostic
    sample_result = await db.execute(select(Sample).where(Sample.diagnostic_id == diagnostic_id))
    samples = list(sample_result.scalars().all())

    # Fetch zones for the building
    zone_result = await db.execute(select(Zone).where(Zone.building_id == diagnostic.building_id))
    zones = list(zone_result.scalars().all())

    # Fetch documents for the building
    doc_result = await db.execute(select(Document).where(Document.building_id == diagnostic.building_id))
    documents = list(doc_result.scalars().all())

    total_samples = len(samples)
    total_zones = max(len(zones), 1)

    # 1. Sample density score (samples per zone, target >=2 per zone)
    density = total_samples / total_zones
    sample_density_score = min(density / 2.0, 1.0) * 100

    # 2. Pollutant coverage score (which of 5 types are tested)
    pollutants_tested = list({s.pollutant_type for s in samples if s.pollutant_type})
    pollutants_missing = [p for p in ALL_POLLUTANTS if p not in pollutants_tested]
    coverage_ratio = len(pollutants_tested) / len(ALL_POLLUTANTS) if ALL_POLLUTANTS else 0
    pollutant_coverage_score = coverage_ratio * 100

    # 3. Methodology score
    methodology_score = 0.0
    if diagnostic.methodology:
        methodology_score += 50.0
    if diagnostic.date_inspection:
        methodology_score += 25.0
    if diagnostic.diagnostic_context:
        methodology_score += 25.0

    # 4. Documentation score
    documentation_score = 0.0
    if diagnostic.summary:
        documentation_score += 30.0
    if diagnostic.conclusion:
        documentation_score += 30.0
    if diagnostic.report_file_path:
        documentation_score += 20.0
    if len(documents) > 0:
        documentation_score += 20.0

    # 5. Lab accreditation score
    lab_accreditation_score = 0.0
    if diagnostic.laboratory:
        lab_accreditation_score += 50.0
    if diagnostic.laboratory_report_number:
        lab_accreditation_score += 50.0

    # Overall weighted score
    overall_score = (
        sample_density_score * W_SAMPLE_DENSITY
        + pollutant_coverage_score * W_POLLUTANT_COVERAGE
        + methodology_score * W_METHODOLOGY
        + documentation_score * W_DOCUMENTATION
        + lab_accreditation_score * W_LAB_ACCREDITATION
    )

    return {
        "diagnostic_id": diagnostic_id,
        "overall_score": round(overall_score, 1),
        "grade": _score_to_grade(overall_score),
        "sample_density_score": round(sample_density_score, 1),
        "pollutant_coverage_score": round(pollutant_coverage_score, 1),
        "methodology_score": round(methodology_score, 1),
        "documentation_score": round(documentation_score, 1),
        "lab_accreditation_score": round(lab_accreditation_score, 1),
        "total_samples": total_samples,
        "total_zones": len(zones),
        "pollutants_tested": sorted(pollutants_tested),
        "pollutants_missing": sorted(pollutants_missing),
    }


async def compare_diagnostician_performance(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> dict | None:
    """Compare diagnosticians within an organization by quality metrics."""
    # Get diagnosticians in org
    user_result = await db.execute(
        select(User).where(
            User.organization_id == org_id,
            User.role == "diagnostician",
            User.is_active.is_(True),
        )
    )
    diagnosticians = list(user_result.scalars().all())

    if not diagnosticians:
        return {
            "organization_id": org_id,
            "diagnosticians": [],
            "total_diagnosticians": 0,
        }

    performances = []
    for diag_user in diagnosticians:
        # Get all diagnostics by this diagnostician
        diag_result = await db.execute(select(Diagnostic).where(Diagnostic.diagnostician_id == diag_user.id))
        diagnostics = list(diag_result.scalars().all())
        diagnostic_count = len(diagnostics)

        if diagnostic_count == 0:
            performances.append(
                {
                    "diagnostician_id": diag_user.id,
                    "diagnostician_name": f"{diag_user.first_name} {diag_user.last_name}",
                    "diagnostic_count": 0,
                    "avg_quality_score": 0.0,
                    "avg_samples_per_diagnostic": 0.0,
                    "avg_days_to_completion": None,
                    "completeness_rate": 0.0,
                    "rank": 0,
                }
            )
            continue

        # Quality scores
        quality_scores = []
        total_samples_all = 0
        for d in diagnostics:
            q = await evaluate_diagnostic_quality(db, d.id)
            if q:
                quality_scores.append(q["overall_score"])
            # Sample count
            sc_result = await db.execute(select(func.count()).select_from(Sample).where(Sample.diagnostic_id == d.id))
            total_samples_all += sc_result.scalar() or 0

        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        avg_samples = total_samples_all / diagnostic_count

        # Average days to completion (inspection → report)
        days_list = []
        for d in diagnostics:
            if d.date_inspection and d.date_report:
                delta = (d.date_report - d.date_inspection).days
                if delta >= 0:
                    days_list.append(delta)
        avg_days = sum(days_list) / len(days_list) if days_list else None

        # Completeness rate
        completed = sum(1 for d in diagnostics if d.status in ("completed", "validated"))
        completeness_rate = (completed / diagnostic_count) * 100

        performances.append(
            {
                "diagnostician_id": diag_user.id,
                "diagnostician_name": f"{diag_user.first_name} {diag_user.last_name}",
                "diagnostic_count": diagnostic_count,
                "avg_quality_score": round(avg_quality, 1),
                "avg_samples_per_diagnostic": round(avg_samples, 1),
                "avg_days_to_completion": round(avg_days, 1) if avg_days is not None else None,
                "completeness_rate": round(completeness_rate, 1),
                "rank": 0,
            }
        )

    # Rank by avg_quality_score descending
    performances.sort(key=lambda p: p["avg_quality_score"], reverse=True)
    for i, p in enumerate(performances, start=1):
        p["rank"] = i

    return {
        "organization_id": org_id,
        "diagnosticians": performances,
        "total_diagnosticians": len(performances),
    }


async def detect_diagnostic_deficiencies(
    db: AsyncSession,
    diagnostic_id: uuid.UUID,
) -> dict | None:
    """Detect specific deficiencies in a diagnostic with fix actions."""
    result = await db.execute(select(Diagnostic).where(Diagnostic.id == diagnostic_id))
    diagnostic = result.scalar_one_or_none()
    if diagnostic is None:
        return None

    sample_result = await db.execute(select(Sample).where(Sample.diagnostic_id == diagnostic_id))
    samples = list(sample_result.scalars().all())

    zone_result = await db.execute(select(Zone).where(Zone.building_id == diagnostic.building_id))
    zones = list(zone_result.scalars().all())

    deficiencies: list[dict] = []

    # 1. Insufficient sampling — zones without any samples
    for zone in zones:
        # Check if zone name or floor_number matches any sample location_floor
        zone_identifier = zone.name
        zone_has_sample = False
        for s in samples:
            if s.location_floor and (s.location_floor == zone_identifier or s.location_floor == str(zone.floor_number)):
                zone_has_sample = True
                break
        if not zone_has_sample:
            deficiencies.append(
                {
                    "deficiency_type": "insufficient_sampling",
                    "severity": "high",
                    "description": f"Zone '{zone.name}' has no associated samples",
                    "fix_action": f"Collect at least one sample in zone '{zone.name}'",
                    "zone_id": zone.id,
                    "pollutant_type": None,
                }
            )

    # 2. Missing pollutants not tested
    pollutants_tested = {s.pollutant_type for s in samples if s.pollutant_type}
    for pollutant in ALL_POLLUTANTS:
        if pollutant not in pollutants_tested:
            deficiencies.append(
                {
                    "deficiency_type": "missing_pollutant",
                    "severity": "high" if pollutant in ("asbestos", "lead") else "medium",
                    "description": f"Pollutant '{pollutant}' has not been tested",
                    "fix_action": f"Add {pollutant} testing to the diagnostic scope",
                    "zone_id": None,
                    "pollutant_type": pollutant,
                }
            )

    # 3. Outdated methodology
    if not diagnostic.methodology:
        deficiencies.append(
            {
                "deficiency_type": "outdated_methodology",
                "severity": "medium",
                "description": "No methodology specified for this diagnostic",
                "fix_action": "Specify the methodology used (e.g., SIA, FACH, VDI)",
                "zone_id": None,
                "pollutant_type": None,
            }
        )

    # 4. Incomplete report sections
    if not diagnostic.summary:
        deficiencies.append(
            {
                "deficiency_type": "incomplete_report",
                "severity": "medium",
                "description": "Diagnostic summary is missing",
                "fix_action": "Write a summary describing findings and scope",
                "zone_id": None,
                "pollutant_type": None,
            }
        )
    if not diagnostic.conclusion:
        deficiencies.append(
            {
                "deficiency_type": "incomplete_report",
                "severity": "high",
                "description": "Diagnostic conclusion is missing",
                "fix_action": "Add a conclusion with risk assessment and recommendations",
                "zone_id": None,
                "pollutant_type": None,
            }
        )
    if not diagnostic.laboratory:
        deficiencies.append(
            {
                "deficiency_type": "incomplete_report",
                "severity": "medium",
                "description": "Laboratory name is not specified",
                "fix_action": "Record the accredited laboratory used for analysis",
                "zone_id": None,
                "pollutant_type": None,
            }
        )
    if not diagnostic.report_file_path:
        deficiencies.append(
            {
                "deficiency_type": "incomplete_report",
                "severity": "medium",
                "description": "No report file attached",
                "fix_action": "Upload the diagnostic report PDF",
                "zone_id": None,
                "pollutant_type": None,
            }
        )

    # 5. No samples at all
    if not samples:
        deficiencies.append(
            {
                "deficiency_type": "insufficient_sampling",
                "severity": "critical",
                "description": "Diagnostic has no samples at all",
                "fix_action": "Collect and record samples for this diagnostic",
                "zone_id": None,
                "pollutant_type": None,
            }
        )

    critical_count = sum(1 for d in deficiencies if d["severity"] == "critical")
    high_count = sum(1 for d in deficiencies if d["severity"] == "high")

    return {
        "diagnostic_id": diagnostic_id,
        "deficiencies": deficiencies,
        "total_deficiencies": len(deficiencies),
        "critical_count": critical_count,
        "high_count": high_count,
    }


async def get_diagnostic_benchmarks(db: AsyncSession) -> dict:
    """Compute system-wide diagnostic quality benchmarks."""
    diag_result = await db.execute(select(Diagnostic))
    diagnostics = list(diag_result.scalars().all())

    if not diagnostics:
        return {
            "total_diagnostics": 0,
            "avg_quality_score": 0.0,
            "median_quality_score": 0.0,
            "avg_sample_count": 0.0,
            "avg_pollutants_tested": 0.0,
            "best_practice_threshold": 75.0,
            "grade_distribution": {},
            "pollutant_coverage_rate": {p: 0.0 for p in ALL_POLLUTANTS},
        }

    quality_scores = []
    sample_counts = []
    pollutant_counts = []
    grade_dist: dict[str, int] = {}
    pollutant_diag_count: dict[str, int] = {p: 0 for p in ALL_POLLUTANTS}

    for d in diagnostics:
        q = await evaluate_diagnostic_quality(db, d.id)
        if q is None:
            continue

        score = q["overall_score"]
        quality_scores.append(score)
        sample_counts.append(q["total_samples"])
        pollutant_counts.append(len(q["pollutants_tested"]))

        grade = q["grade"]
        grade_dist[grade] = grade_dist.get(grade, 0) + 1

        for p in q["pollutants_tested"]:
            if p in pollutant_diag_count:
                pollutant_diag_count[p] += 1

    total = len(quality_scores)
    avg_score = sum(quality_scores) / total if total else 0.0
    med_score = median(quality_scores) if total else 0.0
    avg_samples = sum(sample_counts) / total if total else 0.0
    avg_pollutants = sum(pollutant_counts) / total if total else 0.0

    pollutant_coverage_rate = {
        p: round(count / total, 2) if total else 0.0 for p, count in pollutant_diag_count.items()
    }

    return {
        "total_diagnostics": total,
        "avg_quality_score": round(avg_score, 1),
        "median_quality_score": round(med_score, 1),
        "avg_sample_count": round(avg_samples, 1),
        "avg_pollutants_tested": round(avg_pollutants, 1),
        "best_practice_threshold": 75.0,
        "grade_distribution": grade_dist,
        "pollutant_coverage_rate": pollutant_coverage_rate,
    }
