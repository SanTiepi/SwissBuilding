"""
SwissBuildingOS - Lab Result Analysis Service

Provides consolidated analysis, anomaly detection, temporal trends, and
summary reports for laboratory results attached to building diagnostics.
"""

from __future__ import annotations

import statistics
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.schemas.lab_result import (
    LabResultAnalysis,
    LabSummaryReport,
    PollutantComplianceSummary,
    PollutantStats,
    PollutantTrend,
    PollutantTrendPoint,
    ResultAnomaly,
    ResultAnomalyReport,
    ResultTrends,
    SampleResult,
)
from app.services.compliance_engine import SWISS_THRESHOLDS

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEFAULT_UNIT_FOR_POLLUTANT: dict[str, str] = {
    "asbestos": "percent_weight",
    "pcb": "mg_per_kg",
    "lead": "mg_per_kg",
    "hap": "mg_per_kg",
    "radon": "bq_per_m3",
}


def _get_threshold(pollutant: str | None, unit: str | None) -> float | None:
    """Return the Swiss regulatory threshold for a pollutant/unit pair."""
    if not pollutant:
        return None
    entries = SWISS_THRESHOLDS.get(pollutant.lower(), {})
    norm_unit = (unit or "").lower().strip()
    for entry in entries.values():
        if entry["unit"] == norm_unit:
            return entry["threshold"]
    # Fallback: first entry
    if entries:
        return next(iter(entries.values()))["threshold"]
    return None


async def _fetch_samples(db: AsyncSession, building_id: UUID) -> list[Sample]:
    """Fetch all samples for a building via its diagnostics."""
    stmt = (
        select(Sample)
        .join(Diagnostic, Diagnostic.id == Sample.diagnostic_id)
        .where(Diagnostic.building_id == building_id)
        .order_by(Sample.created_at)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _fetch_samples_with_diagnostics(db: AsyncSession, building_id: UUID) -> list[tuple[Sample, Diagnostic]]:
    """Fetch samples joined with their diagnostic."""
    stmt = (
        select(Sample, Diagnostic)
        .join(Diagnostic, Diagnostic.id == Sample.diagnostic_id)
        .where(Diagnostic.building_id == building_id)
        .order_by(Sample.created_at)
    )
    result = await db.execute(stmt)
    return [(row[0], row[1]) for row in result.all()]


# ---------------------------------------------------------------------------
# FN1: analyze_lab_results
# ---------------------------------------------------------------------------


async def analyze_lab_results(db: AsyncSession, building_id: UUID) -> LabResultAnalysis:
    """Consolidated lab result analysis: all samples with results,
    concentration vs threshold comparison, pass/fail per sample,
    statistical summary (min/max/avg/median per pollutant)."""

    samples = await _fetch_samples(db, building_id)

    sample_results: list[SampleResult] = []
    # Group by pollutant for stats
    by_pollutant: dict[str, list[Sample]] = {}

    for s in samples:
        threshold = _get_threshold(s.pollutant_type, s.unit)
        ratio = None
        exceeded = s.threshold_exceeded or False
        if s.concentration is not None and threshold is not None and threshold > 0:
            ratio = round(s.concentration / threshold, 4)
            exceeded = s.concentration >= threshold

        sample_results.append(
            SampleResult(
                sample_id=s.id,
                sample_number=s.sample_number,
                pollutant_type=s.pollutant_type,
                concentration=s.concentration,
                unit=s.unit,
                threshold=threshold,
                threshold_exceeded=exceeded,
                ratio_to_threshold=ratio,
                risk_level=s.risk_level,
                location_floor=s.location_floor,
                location_room=s.location_room,
                diagnostic_id=s.diagnostic_id,
            )
        )

        if s.pollutant_type:
            by_pollutant.setdefault(s.pollutant_type, []).append(s)

    stats_list: list[PollutantStats] = []
    for pollutant, p_samples in sorted(by_pollutant.items()):
        concentrations = [s.concentration for s in p_samples if s.concentration is not None]
        threshold = _get_threshold(pollutant, p_samples[0].unit if p_samples else None)
        pass_count = sum(1 for c in concentrations if threshold is not None and c < threshold)
        fail_count = sum(1 for c in concentrations if threshold is not None and c >= threshold)
        stats_list.append(
            PollutantStats(
                pollutant_type=pollutant,
                count=len(concentrations),
                min_concentration=min(concentrations) if concentrations else None,
                max_concentration=max(concentrations) if concentrations else None,
                avg_concentration=round(statistics.mean(concentrations), 4) if concentrations else None,
                median_concentration=round(statistics.median(concentrations), 4) if concentrations else None,
                unit=p_samples[0].unit if p_samples else None,
                threshold=threshold,
                pass_count=pass_count,
                fail_count=fail_count,
            )
        )

    samples_with_results = sum(1 for s in samples if s.concentration is not None)

    return LabResultAnalysis(
        building_id=building_id,
        total_samples=len(samples),
        samples_with_results=samples_with_results,
        sample_results=sample_results,
        stats_by_pollutant=stats_list,
        analyzed_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN2: detect_result_anomalies
# ---------------------------------------------------------------------------


async def detect_result_anomalies(db: AsyncSession, building_id: UUID) -> ResultAnomalyReport:
    """Flag suspicious results: values exactly at threshold, extreme outliers
    (>3 std dev), conflicting results in adjacent zones, results inconsistent
    with material age."""

    samples_with_diag = await _fetch_samples_with_diagnostics(db, building_id)
    anomalies: list[ResultAnomaly] = []

    # Build lookup: pollutant → list of (sample, diagnostic)
    by_pollutant: dict[str, list[tuple[Sample, Diagnostic]]] = {}
    for s, d in samples_with_diag:
        if s.pollutant_type:
            by_pollutant.setdefault(s.pollutant_type, []).append((s, d))

    # Fetch building for construction year
    bld_result = await db.execute(select(Building).where(Building.id == building_id))
    building = bld_result.scalar_one_or_none()
    construction_year = building.construction_year if building else None

    for pollutant, items in by_pollutant.items():
        concentrations = [(s, d, s.concentration) for s, d in items if s.concentration is not None]
        if not concentrations:
            continue

        values = [c for _, _, c in concentrations]
        threshold = _get_threshold(pollutant, concentrations[0][0].unit)

        # 1. Values exactly at threshold (suspicious precision)
        if threshold is not None:
            for s, _d, c in concentrations:
                if c == threshold:
                    anomalies.append(
                        ResultAnomaly(
                            anomaly_type="at_threshold",
                            severity="warning",
                            sample_id=s.id,
                            sample_number=s.sample_number,
                            description=(
                                f"Concentration ({c}) exactly equals threshold ({threshold}) "
                                f"for {pollutant} — suspicious precision"
                            ),
                            pollutant_type=pollutant,
                            concentration=c,
                        )
                    )

        # 2. Extreme outliers (>3 std dev)
        if len(values) >= 3:
            mean_val = statistics.mean(values)
            stdev_val = statistics.stdev(values)
            if stdev_val > 0:
                for s, _d, c in concentrations:
                    z_score = abs(c - mean_val) / stdev_val
                    if z_score > 3.0:
                        anomalies.append(
                            ResultAnomaly(
                                anomaly_type="extreme_outlier",
                                severity="critical",
                                sample_id=s.id,
                                sample_number=s.sample_number,
                                description=(
                                    f"Concentration ({c}) is {z_score:.1f} std deviations "
                                    f"from mean ({mean_val:.1f}) for {pollutant}"
                                ),
                                pollutant_type=pollutant,
                                concentration=c,
                            )
                        )

        # 3. Conflicting results in adjacent zones (same floor, opposite results)
        floor_groups: dict[str | None, list[tuple[Sample, Diagnostic, float]]] = {}
        for s, d, c in concentrations:
            floor_groups.setdefault(s.location_floor, []).append((s, d, c))

        for floor, floor_items in floor_groups.items():
            if floor is None or len(floor_items) < 2 or threshold is None:
                continue
            has_pass = any(c < threshold for _, _, c in floor_items)
            has_fail = any(c >= threshold for _, _, c in floor_items)
            if has_pass and has_fail:
                # Flag only the passing one as suspicious
                for s, _d, c in floor_items:
                    if c < threshold:
                        anomalies.append(
                            ResultAnomaly(
                                anomaly_type="conflicting_adjacent",
                                severity="warning",
                                sample_id=s.id,
                                sample_number=s.sample_number,
                                description=(
                                    f"Sample passes ({c}) but adjacent samples on floor '{floor}' fail for {pollutant}"
                                ),
                                pollutant_type=pollutant,
                                concentration=c,
                            )
                        )

        # 4. Age inconsistency: building post-1991 with positive asbestos/pcb
        if construction_year and construction_year >= 1991 and pollutant.lower() in ("asbestos", "pcb"):
            for s, _d, c in concentrations:
                if threshold is not None and c >= threshold:
                    anomalies.append(
                        ResultAnomaly(
                            anomaly_type="age_inconsistent",
                            severity="warning",
                            sample_id=s.id,
                            sample_number=s.sample_number,
                            description=(
                                f"Building constructed in {construction_year} (>=1991) "
                                f"but {pollutant} exceeds threshold ({c} >= {threshold})"
                            ),
                            pollutant_type=pollutant,
                            concentration=c,
                        )
                    )

    by_type: dict[str, int] = {}
    for a in anomalies:
        by_type[a.anomaly_type] = by_type.get(a.anomaly_type, 0) + 1

    return ResultAnomalyReport(
        building_id=building_id,
        anomalies=anomalies,
        total=len(anomalies),
        by_type=by_type,
        scanned_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN3: get_result_trends
# ---------------------------------------------------------------------------


async def get_result_trends(db: AsyncSession, building_id: UUID) -> ResultTrends:
    """Temporal analysis: concentration changes over time (if re-sampled),
    degradation indicators, seasonal patterns (radon)."""

    samples_with_diag = await _fetch_samples_with_diagnostics(db, building_id)

    # Group by pollutant
    by_pollutant: dict[str, list[tuple[Sample, Diagnostic]]] = {}
    for s, d in samples_with_diag:
        if s.pollutant_type and s.concentration is not None:
            by_pollutant.setdefault(s.pollutant_type, []).append((s, d))

    trends: list[PollutantTrend] = []
    for pollutant, items in sorted(by_pollutant.items()):
        # Sort by diagnostic date or sample created_at
        def _sort_key(item: tuple[Sample, Diagnostic]) -> str:
            s, d = item
            if d.date_inspection:
                return d.date_inspection.isoformat()
            if s.created_at:
                return s.created_at.isoformat() if isinstance(s.created_at, datetime) else str(s.created_at)
            return ""

        sorted_items = sorted(items, key=_sort_key)

        data_points: list[PollutantTrendPoint] = []
        for s, d in sorted_items:
            date_str = ""
            if d.date_inspection:
                date_str = d.date_inspection.isoformat()
            elif s.created_at:
                date_str = s.created_at.isoformat() if isinstance(s.created_at, datetime) else str(s.created_at)
            data_points.append(
                PollutantTrendPoint(
                    date=date_str,
                    concentration=s.concentration,  # type: ignore[arg-type]
                    sample_number=s.sample_number,
                    sample_id=s.id,
                )
            )

        # Determine trend direction
        concentrations = [dp.concentration for dp in data_points]
        trend_direction = "stable"
        if len(concentrations) >= 2:
            first_half = statistics.mean(concentrations[: len(concentrations) // 2])
            second_half = statistics.mean(concentrations[len(concentrations) // 2 :])
            if second_half > first_half * 1.1:
                trend_direction = "increasing"
            elif second_half < first_half * 0.9:
                trend_direction = "decreasing"

        # Seasonal flag for radon
        is_seasonal = pollutant.lower() == "radon"

        trends.append(
            PollutantTrend(
                pollutant_type=pollutant,
                unit=sorted_items[0][0].unit if sorted_items else None,
                data_points=data_points,
                trend_direction=trend_direction,
                is_seasonal=is_seasonal,
            )
        )

    return ResultTrends(
        building_id=building_id,
        trends=trends,
        analyzed_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN4: generate_lab_summary_report
# ---------------------------------------------------------------------------


async def generate_lab_summary_report(db: AsyncSession, building_id: UUID) -> LabSummaryReport:
    """Structured report: total samples, results by pollutant, compliance
    status, anomaly flags, recommendations for re-sampling."""

    samples = await _fetch_samples(db, building_id)
    anomaly_report = await detect_result_anomalies(db, building_id)

    samples_with_results = [s for s in samples if s.concentration is not None]
    samples_without = len(samples) - len(samples_with_results)

    # Compliance by pollutant
    by_pollutant: dict[str, list[Sample]] = {}
    for s in samples:
        if s.pollutant_type:
            by_pollutant.setdefault(s.pollutant_type, []).append(s)

    summaries: list[PollutantComplianceSummary] = []
    overall_compliance = True

    for pollutant, p_samples in sorted(by_pollutant.items()):
        threshold = _get_threshold(pollutant, p_samples[0].unit if p_samples else None)
        total = len(p_samples)
        compliant = 0
        non_compliant = 0
        for s in p_samples:
            if s.concentration is None:
                continue
            if threshold is not None and s.concentration >= threshold:
                non_compliant += 1
            else:
                compliant += 1

        if non_compliant > 0:
            overall_compliance = False

        rate = compliant / (compliant + non_compliant) if (compliant + non_compliant) > 0 else 1.0
        summaries.append(
            PollutantComplianceSummary(
                pollutant_type=pollutant,
                total_samples=total,
                compliant=compliant,
                non_compliant=non_compliant,
                compliance_rate=round(rate, 4),
            )
        )

    # Recommendations
    recommendations: list[str] = []
    if samples_without > 0:
        recommendations.append(
            f"{samples_without} sample(s) have no lab results — request results from the laboratory."
        )
    if anomaly_report.total > 0:
        recommendations.append(f"{anomaly_report.total} anomaly/anomalies detected — review flagged samples.")
    for ps in summaries:
        if ps.non_compliant > 0:
            recommendations.append(
                f"{ps.pollutant_type}: {ps.non_compliant} non-compliant sample(s) — "
                f"plan remediation or re-sample to confirm."
            )
    if not samples:
        recommendations.append("No samples found for this building — schedule a diagnostic.")

    return LabSummaryReport(
        building_id=building_id,
        total_samples=len(samples),
        samples_with_results=len(samples_with_results),
        samples_without_results=samples_without,
        pollutant_summaries=summaries,
        overall_compliance=overall_compliance,
        anomaly_count=anomaly_report.total,
        recommendations=recommendations,
        generated_at=datetime.now(UTC),
    )
