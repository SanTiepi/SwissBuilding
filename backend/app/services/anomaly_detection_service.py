"""
SwissBuildingOS - Anomaly Detection Service

Scans building data for anomalies: value spikes, missing data, inconsistent
states, temporal gaps, regulatory threshold breaches, and pattern deviations
across snapshots.
"""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.building_snapshot import BuildingSnapshot
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.models.zone import Zone
from app.schemas.anomaly_detection import (
    Anomaly,
    AnomalyReport,
    AnomalySeverity,
    AnomalyTrend,
    AnomalyType,
)

# ---------------------------------------------------------------------------
# Swiss regulatory thresholds
# ---------------------------------------------------------------------------
THRESHOLDS: dict[str, tuple[float, str]] = {
    "asbestos": (0.1, "%"),  # >0.1%
    "pcb": (50.0, "mg/kg"),  # >50 mg/kg
    "lead": (5000.0, "mg/kg"),  # >5000 mg/kg
}

PRE_1991_YEAR = 1991
DIAGNOSTIC_GAP_YEARS = 3
VALUE_SPIKE_FACTOR = 10.0
TRUST_DROP_THRESHOLD = 0.2
MISSING_DATA_ZONE_COVERAGE = 0.5


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _make_anomaly(
    building_id: uuid.UUID,
    anomaly_type: AnomalyType,
    severity: AnomalySeverity,
    title: str,
    description: str,
    confidence: float,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    metadata: dict | None = None,
) -> Anomaly:
    return Anomaly(
        id=str(uuid.uuid4()),
        building_id=building_id,
        anomaly_type=anomaly_type,
        severity=severity,
        title=title,
        description=description,
        entity_type=entity_type,
        entity_id=entity_id,
        detected_at=datetime.now(UTC),
        confidence=confidence,
        metadata=metadata,
    )


def _build_report(building_id: uuid.UUID, anomalies: list[Anomaly]) -> AnomalyReport:
    by_type: dict[str, int] = Counter()
    by_severity: dict[str, int] = Counter()
    for a in anomalies:
        by_type[a.anomaly_type.value] += 1
        by_severity[a.severity.value] += 1
    return AnomalyReport(
        building_id=building_id,
        anomalies=anomalies,
        total=len(anomalies),
        by_type=dict(by_type),
        by_severity=dict(by_severity),
        scanned_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Detection rules
# ---------------------------------------------------------------------------


async def _detect_value_spikes(
    building_id: uuid.UUID,
    samples: list[Sample],
) -> list[Anomaly]:
    """Rule 1: sample concentration >10x average for same pollutant in building."""
    anomalies: list[Anomaly] = []
    by_pollutant: dict[str, list[Sample]] = {}
    for s in samples:
        if s.pollutant_type and s.concentration is not None:
            by_pollutant.setdefault(s.pollutant_type, []).append(s)

    for pollutant, group in by_pollutant.items():
        values = [s.concentration for s in group if s.concentration is not None]
        if len(values) < 2:
            continue
        avg = sum(values) / len(values)
        if avg == 0:
            continue
        for s in group:
            if s.concentration is not None and s.concentration > avg * VALUE_SPIKE_FACTOR:
                anomalies.append(
                    _make_anomaly(
                        building_id=building_id,
                        anomaly_type=AnomalyType.value_spike,
                        severity=AnomalySeverity.warning,
                        title=f"Value spike: {pollutant}",
                        description=(
                            f"Sample {s.sample_number} concentration "
                            f"({s.concentration}) is >{VALUE_SPIKE_FACTOR:.0f}x "
                            f"the building average ({avg:.2f}) for {pollutant}."
                        ),
                        confidence=0.85,
                        entity_type="sample",
                        entity_id=s.id,
                        metadata={"pollutant": pollutant, "value": s.concentration, "average": avg},
                    )
                )
    return anomalies


async def _detect_missing_data(
    building_id: uuid.UUID,
    zones: list[Zone],
    samples: list[Sample],
) -> list[Anomaly]:
    """Rule 2: building has zones but <50% have samples."""
    if not zones:
        return []

    # Build set of zone ids that have at least one sample via location info
    # Samples are linked to diagnostics, not directly to zones, so we use
    # a heuristic: count zones with elements that have materials linked to samples.
    # Simplified: if total samples < 50% of zone count, flag it.
    zone_count = len(zones)
    sample_count = len(samples)
    coverage = sample_count / zone_count if zone_count > 0 else 1.0

    if coverage < MISSING_DATA_ZONE_COVERAGE:
        return [
            _make_anomaly(
                building_id=building_id,
                anomaly_type=AnomalyType.missing_data,
                severity=AnomalySeverity.warning,
                title="Low sample coverage across zones",
                description=(
                    f"Only {sample_count} sample(s) for {zone_count} zone(s) "
                    f"({coverage:.0%} coverage). Consider additional sampling."
                ),
                confidence=0.7,
                metadata={"zone_count": zone_count, "sample_count": sample_count},
            )
        ]
    return []


async def _detect_inconsistent_state(
    building_id: uuid.UUID,
    diagnostics: list[Diagnostic],
    risk_score: BuildingRiskScore | None,
) -> list[Anomaly]:
    """Rule 3: diagnostic completed but building risk_level still 'unknown'."""
    completed = [d for d in diagnostics if d.status in ("completed", "validated")]
    if not completed:
        return []
    if risk_score and risk_score.overall_risk_level != "unknown":
        return []
    return [
        _make_anomaly(
            building_id=building_id,
            anomaly_type=AnomalyType.inconsistent_state,
            severity=AnomalySeverity.warning,
            title="Risk level not updated after diagnostic",
            description=(
                f"{len(completed)} diagnostic(s) completed but building risk "
                "level is still 'unknown'. Risk assessment should be updated."
            ),
            confidence=0.9,
        )
    ]


async def _detect_temporal_gap(
    building_id: uuid.UUID,
    building: Building,
    diagnostics: list[Diagnostic],
) -> list[Anomaly]:
    """Rule 4: no diagnostic in >3 years for pre-1991 building."""
    if building.construction_year and building.construction_year >= PRE_1991_YEAR:
        return []

    now = datetime.now(UTC)
    cutoff = now - timedelta(days=DIAGNOSTIC_GAP_YEARS * 365)

    recent = [d for d in diagnostics if d.created_at is not None and d.created_at >= cutoff]
    if recent:
        return []

    return [
        _make_anomaly(
            building_id=building_id,
            anomaly_type=AnomalyType.temporal_gap,
            severity=AnomalySeverity.critical,
            title="Diagnostic gap for pre-1991 building",
            description=(
                f"No diagnostic in the last {DIAGNOSTIC_GAP_YEARS} years for a "
                f"building constructed in {building.construction_year}. "
                "Pre-1991 buildings require regular pollutant assessments."
            ),
            confidence=0.95,
        )
    ]


async def _detect_threshold_breaches(
    building_id: uuid.UUID,
    samples: list[Sample],
) -> list[Anomaly]:
    """Rule 5: sample exceeds Swiss regulatory thresholds."""
    anomalies: list[Anomaly] = []
    for s in samples:
        if not s.pollutant_type or s.concentration is None:
            continue
        key = s.pollutant_type.lower()
        if key not in THRESHOLDS:
            continue
        limit, unit = THRESHOLDS[key]
        if s.concentration > limit:
            anomalies.append(
                _make_anomaly(
                    building_id=building_id,
                    anomaly_type=AnomalyType.threshold_breach,
                    severity=AnomalySeverity.critical,
                    title=f"Threshold breach: {s.pollutant_type}",
                    description=(
                        f"Sample {s.sample_number} has {s.pollutant_type} "
                        f"concentration {s.concentration} {unit}, exceeding the "
                        f"Swiss limit of {limit} {unit}."
                    ),
                    confidence=1.0,
                    entity_type="sample",
                    entity_id=s.id,
                    metadata={
                        "pollutant": s.pollutant_type,
                        "value": s.concentration,
                        "limit": limit,
                        "unit": unit,
                    },
                )
            )
    return anomalies


async def _detect_pattern_deviation(
    building_id: uuid.UUID,
    snapshots: list[BuildingSnapshot],
) -> list[Anomaly]:
    """Rule 6: trust score dropped >0.2 between consecutive snapshots."""
    anomalies: list[Anomaly] = []
    if len(snapshots) < 2:
        return anomalies

    sorted_snaps = sorted(snapshots, key=lambda s: s.captured_at or datetime.min)
    for i in range(1, len(sorted_snaps)):
        prev = sorted_snaps[i - 1]
        curr = sorted_snaps[i]
        if prev.overall_trust is not None and curr.overall_trust is not None:
            drop = prev.overall_trust - curr.overall_trust
            if drop > TRUST_DROP_THRESHOLD:
                anomalies.append(
                    _make_anomaly(
                        building_id=building_id,
                        anomaly_type=AnomalyType.pattern_deviation,
                        severity=AnomalySeverity.warning,
                        title="Trust score drop detected",
                        description=(
                            f"Trust score dropped from {prev.overall_trust:.2f} to "
                            f"{curr.overall_trust:.2f} (Δ{drop:.2f}) between "
                            f"consecutive snapshots."
                        ),
                        confidence=0.8,
                        metadata={
                            "previous_trust": prev.overall_trust,
                            "current_trust": curr.overall_trust,
                            "drop": drop,
                        },
                    )
                )
    return anomalies


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def detect_anomalies(
    db: AsyncSession,
    building_id: uuid.UUID,
) -> AnomalyReport:
    """Run all anomaly detection rules for a single building."""
    # Load building with relations
    result = await db.execute(
        select(Building)
        .where(Building.id == building_id)
        .options(
            selectinload(Building.diagnostics).selectinload(Diagnostic.samples),
            selectinload(Building.zones),
        )
    )
    building = result.scalar_one_or_none()
    if building is None:
        return _build_report(building_id, [])

    # Collect all samples across diagnostics
    all_samples: list[Sample] = []
    for diag in building.diagnostics:
        all_samples.extend(diag.samples)

    # Load risk score
    risk_result = await db.execute(select(BuildingRiskScore).where(BuildingRiskScore.building_id == building_id))
    risk_score = risk_result.scalar_one_or_none()

    # Load snapshots
    snap_result = await db.execute(select(BuildingSnapshot).where(BuildingSnapshot.building_id == building_id))
    snapshots = list(snap_result.scalars().all())

    # Run all detection rules
    anomalies: list[Anomaly] = []
    anomalies.extend(await _detect_value_spikes(building_id, all_samples))
    anomalies.extend(await _detect_missing_data(building_id, building.zones, all_samples))
    anomalies.extend(await _detect_inconsistent_state(building_id, building.diagnostics, risk_score))
    anomalies.extend(await _detect_temporal_gap(building_id, building, building.diagnostics))
    anomalies.extend(await _detect_threshold_breaches(building_id, all_samples))
    anomalies.extend(await _detect_pattern_deviation(building_id, snapshots))

    return _build_report(building_id, anomalies)


async def detect_portfolio_anomalies(
    db: AsyncSession,
    org_id: uuid.UUID | None = None,
    limit: int = 50,
) -> list[AnomalyReport]:
    """Scan multiple buildings for anomalies."""
    query = select(Building.id)
    if org_id is not None:
        query = query.where(
            Building.owner_id.in_(
                select(Building.created_by).where(Building.id.isnot(None))  # placeholder
            )
        )
    query = query.limit(limit)

    result = await db.execute(query)
    building_ids = [row[0] for row in result.all()]

    reports: list[AnomalyReport] = []
    for bid in building_ids:
        report = await detect_anomalies(db, bid)
        if report.total > 0:
            reports.append(report)
    return reports


async def get_anomaly_trend(
    db: AsyncSession,
    building_id: uuid.UUID,
    months: int = 12,
) -> AnomalyTrend:
    """Compute anomaly trend for a building over the past N months."""
    now = datetime.now(UTC)

    # We approximate trend by looking at snapshots over time
    # and counting how many anomaly-indicative conditions exist per period
    snap_result = await db.execute(
        select(BuildingSnapshot)
        .where(
            BuildingSnapshot.building_id == building_id,
            BuildingSnapshot.captured_at >= now - timedelta(days=months * 30),
        )
        .order_by(BuildingSnapshot.captured_at)
    )
    snapshots = list(snap_result.scalars().all())

    # Group by month
    monthly_counts: dict[str, int] = {}
    for snap in snapshots:
        if snap.captured_at:
            key = snap.captured_at.strftime("%Y-%m")
            monthly_counts[key] = monthly_counts.get(key, 0) + 1

    counts_list = [{"date": k, "count": v} for k, v in sorted(monthly_counts.items())]

    # Determine trend direction
    if len(counts_list) < 2:
        direction = "stable"
    else:
        first_half = counts_list[: len(counts_list) // 2]
        second_half = counts_list[len(counts_list) // 2 :]
        avg_first = sum(c["count"] for c in first_half) / len(first_half) if first_half else 0
        avg_second = sum(c["count"] for c in second_half) / len(second_half) if second_half else 0
        if avg_second < avg_first * 0.8:
            direction = "improving"
        elif avg_second > avg_first * 1.2:
            direction = "worsening"
        else:
            direction = "stable"

    return AnomalyTrend(
        period=f"{months}m",
        anomaly_counts=counts_list,
        trend_direction=direction,
    )


async def get_critical_anomalies(
    db: AsyncSession,
    org_id: uuid.UUID | None = None,
) -> list[Anomaly]:
    """Return only critical-severity anomalies across all buildings."""
    reports = await detect_portfolio_anomalies(db, org_id=org_id, limit=100)
    critical: list[Anomaly] = []
    for report in reports:
        for anomaly in report.anomalies:
            if anomaly.severity == AnomalySeverity.critical:
                critical.append(anomaly)
    return critical
