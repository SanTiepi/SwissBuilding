"""
SwissBuildingOS - Building Benchmark Service

Computes peer-based benchmarks for buildings based on canton, building_type,
and construction decade.  Provides per-dimension percentile ranking and
canton-level aggregate statistics.
"""

from __future__ import annotations

import statistics
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.building_snapshot import BuildingSnapshot
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.schemas.building_benchmark import (
    BenchmarkComparison,
    BenchmarkDimension,
    BuildingBenchmark,
    CantonBenchmark,
    PeerGroup,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_GRADE_ORD = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}
_GRADE_REVERSE = {5: "A", 4: "B", 3: "C", 2: "D", 1: "E"}


def _decade(year: int | None) -> str | None:
    if year is None:
        return None
    return f"{(year // 10) * 10}s"


def _percentile_rank(value: float, values: list[float]) -> float:
    """Compute the percentile rank of *value* within *values* (0-100)."""
    if not values:
        return 50.0
    below = sum(1 for v in values if v < value)
    equal = sum(1 for v in values if v == value)
    return ((below + 0.5 * equal) / len(values)) * 100


async def _risk_score_for_building(db: AsyncSession, building_id: UUID) -> float | None:
    """Average of the 5 pollutant probabilities from BuildingRiskScore."""
    stmt = select(BuildingRiskScore).where(BuildingRiskScore.building_id == building_id)
    result = await db.execute(stmt)
    rs = result.scalar_one_or_none()
    if rs is None:
        return None
    probs = [
        rs.asbestos_probability,
        rs.pcb_probability,
        rs.lead_probability,
        rs.hap_probability,
        rs.radon_probability,
    ]
    valid = [p for p in probs if p is not None]
    return statistics.mean(valid) if valid else None


async def _latest_snapshot(db: AsyncSession, building_id: UUID) -> BuildingSnapshot | None:
    stmt = (
        select(BuildingSnapshot)
        .where(BuildingSnapshot.building_id == building_id)
        .order_by(BuildingSnapshot.captured_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _count_diagnostics(db: AsyncSession, building_id: UUID) -> int:
    stmt = select(func.count()).select_from(Diagnostic).where(Diagnostic.building_id == building_id)
    result = await db.execute(stmt)
    return result.scalar() or 0


async def _count_samples(db: AsyncSession, building_id: UUID) -> int:
    stmt = (
        select(func.count())
        .select_from(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(Diagnostic.building_id == building_id)
    )
    result = await db.execute(stmt)
    return result.scalar() or 0


# ---------------------------------------------------------------------------
# Peer group
# ---------------------------------------------------------------------------


async def get_peer_group(db: AsyncSession, building_id: UUID) -> PeerGroup:
    """Return the peer group definition + member IDs for a building."""
    stmt = select(Building).where(Building.id == building_id)
    result = await db.execute(stmt)
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    decade = _decade(building.construction_year)
    criteria: dict = {
        "canton": building.canton,
        "building_type": building.building_type,
        "decade": decade,
    }

    # Query peers: same canton + type + decade
    peer_stmt = select(Building.id).where(
        Building.canton == building.canton,
        Building.building_type == building.building_type,
    )
    if decade is not None:
        decade_start = (building.construction_year // 10) * 10  # type: ignore[operator]
        peer_stmt = peer_stmt.where(
            Building.construction_year >= decade_start,
            Building.construction_year < decade_start + 10,
        )
    else:
        peer_stmt = peer_stmt.where(Building.construction_year.is_(None))

    result = await db.execute(peer_stmt)
    peer_ids = [row[0] for row in result.all()]

    return PeerGroup(
        criteria=criteria,
        peer_count=len(peer_ids),
        building_ids=peer_ids,
    )


# ---------------------------------------------------------------------------
# Single building benchmark
# ---------------------------------------------------------------------------


async def _collect_dimension_values(db: AsyncSession, building_ids: list[UUID]) -> dict[UUID, dict[str, float | None]]:
    """Collect raw dimension values for a set of buildings."""
    values: dict[UUID, dict[str, float | None]] = {}
    for bid in building_ids:
        risk = await _risk_score_for_building(db, bid)
        snap = await _latest_snapshot(db, bid)
        diag_count = await _count_diagnostics(db, bid)
        sample_count = await _count_samples(db, bid)

        grade_ord: float | None = None
        completeness: float | None = None
        trust: float | None = None
        if snap is not None:
            if snap.passport_grade and snap.passport_grade in _GRADE_ORD:
                grade_ord = float(_GRADE_ORD[snap.passport_grade])
            completeness = snap.completeness_score
            trust = snap.overall_trust

        values[bid] = {
            "risk_score": risk,
            "completeness_score": completeness,
            "trust_score": trust,
            "passport_grade": grade_ord,
            "diagnostic_count": float(diag_count),
            "sample_count": float(sample_count),
        }
    return values


def _build_dimensions(
    building_id: UUID,
    all_values: dict[UUID, dict[str, float | None]],
) -> list[BenchmarkDimension]:
    """Build BenchmarkDimension list for a single building against its peers."""
    bv = all_values[building_id]
    dimension_names = [
        "risk_score",
        "completeness_score",
        "trust_score",
        "passport_grade",
        "diagnostic_count",
        "sample_count",
    ]
    dims: list[BenchmarkDimension] = []

    # For risk_score, lower is better. For everything else, higher is better.
    lower_is_better = {"risk_score"}

    for name in dimension_names:
        building_value = bv[name]
        peer_values = [all_values[pid][name] for pid in all_values if all_values[pid][name] is not None]

        peer_avg: float | None = None
        peer_median: float | None = None
        percentile: float | None = None
        better: bool | None = None

        if peer_values:
            peer_avg = statistics.mean(peer_values)
            peer_median = statistics.median(peer_values)

        if building_value is not None and peer_values:
            percentile = _percentile_rank(building_value, peer_values)
            if name in lower_is_better:
                # Invert percentile for lower-is-better: 90th pctile in risk = bad
                percentile = 100.0 - percentile
                better = building_value < (peer_avg or 0)
            else:
                better = building_value > (peer_avg or 0)

        dims.append(
            BenchmarkDimension(
                name=name,
                building_value=building_value,
                peer_avg=peer_avg,
                peer_median=peer_median,
                percentile=round(percentile, 1) if percentile is not None else None,
                better_than_peers=better,
            )
        )
    return dims


async def benchmark_building(db: AsyncSession, building_id: UUID) -> BuildingBenchmark:
    """Compute benchmark for a single building against its peer group."""
    peer_group = await get_peer_group(db, building_id)
    all_values = await _collect_dimension_values(db, peer_group.building_ids)

    # If building itself is not in peer group values (shouldn't happen), add it
    if building_id not in all_values:
        all_values = await _collect_dimension_values(db, [building_id, *peer_group.building_ids])

    dimensions = _build_dimensions(building_id, all_values)

    # Overall percentile = average of non-None percentiles
    pcts = [d.percentile for d in dimensions if d.percentile is not None]
    overall = round(statistics.mean(pcts), 1) if pcts else None

    return BuildingBenchmark(
        building_id=building_id,
        peer_group=peer_group,
        dimensions=dimensions,
        overall_percentile=overall,
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Compare multiple buildings
# ---------------------------------------------------------------------------


async def compare_buildings_benchmark(db: AsyncSession, building_ids: list[UUID]) -> BenchmarkComparison:
    """Benchmark multiple buildings and identify best/worst."""
    benchmarks: list[BuildingBenchmark] = []
    for bid in building_ids:
        bm = await benchmark_building(db, bid)
        benchmarks.append(bm)

    best_id: UUID | None = None
    worst_id: UUID | None = None
    if benchmarks:
        with_pct = [(bm.building_id, bm.overall_percentile) for bm in benchmarks if bm.overall_percentile is not None]
        if with_pct:
            best_id = max(with_pct, key=lambda x: x[1])[0]  # type: ignore[arg-type]
            worst_id = min(with_pct, key=lambda x: x[1])[0]  # type: ignore[arg-type]

    return BenchmarkComparison(
        buildings=benchmarks,
        best_building_id=best_id,
        worst_building_id=worst_id,
    )


# ---------------------------------------------------------------------------
# Canton-level benchmarks
# ---------------------------------------------------------------------------


async def get_canton_benchmarks(db: AsyncSession) -> list[CantonBenchmark]:
    """Aggregate benchmark statistics per canton."""
    # Get all cantons with building counts
    canton_stmt = select(
        Building.canton,
        func.count(Building.id).label("cnt"),
    ).group_by(Building.canton)
    result = await db.execute(canton_stmt)
    canton_rows = result.all()

    benchmarks: list[CantonBenchmark] = []
    for row in canton_rows:
        canton = row[0]
        count = row[1]

        # Avg risk score
        risk_stmt = (
            select(
                func.avg(
                    (
                        BuildingRiskScore.asbestos_probability
                        + BuildingRiskScore.pcb_probability
                        + BuildingRiskScore.lead_probability
                        + BuildingRiskScore.hap_probability
                        + BuildingRiskScore.radon_probability
                    )
                    / 5.0
                )
            )
            .join(Building, BuildingRiskScore.building_id == Building.id)
            .where(Building.canton == canton)
        )
        risk_result = await db.execute(risk_stmt)
        avg_risk = risk_result.scalar()

        # Avg completeness + trust from latest snapshots
        # Use a subquery to get the latest snapshot per building
        latest_snap_subq = (
            select(
                BuildingSnapshot.building_id,
                func.max(BuildingSnapshot.captured_at).label("max_at"),
            )
            .join(Building, BuildingSnapshot.building_id == Building.id)
            .where(Building.canton == canton)
            .group_by(BuildingSnapshot.building_id)
            .subquery()
        )

        snap_stmt = select(
            func.avg(BuildingSnapshot.completeness_score),
            func.avg(BuildingSnapshot.overall_trust),
        ).join(
            latest_snap_subq,
            (BuildingSnapshot.building_id == latest_snap_subq.c.building_id)
            & (BuildingSnapshot.captured_at == latest_snap_subq.c.max_at),
        )
        snap_result = await db.execute(snap_stmt)
        snap_row = snap_result.one()
        avg_completeness = snap_row[0]
        avg_trust = snap_row[1]

        # Grade distribution from latest snapshots
        grade_stmt = (
            select(
                BuildingSnapshot.passport_grade,
                func.count().label("cnt"),
            )
            .join(
                latest_snap_subq,
                (BuildingSnapshot.building_id == latest_snap_subq.c.building_id)
                & (BuildingSnapshot.captured_at == latest_snap_subq.c.max_at),
            )
            .where(BuildingSnapshot.passport_grade.isnot(None))
            .group_by(BuildingSnapshot.passport_grade)
        )
        grade_result = await db.execute(grade_stmt)
        grade_dist = {gr[0]: gr[1] for gr in grade_result.all()}

        benchmarks.append(
            CantonBenchmark(
                canton=canton,
                building_count=count,
                avg_risk_score=round(avg_risk, 4) if avg_risk is not None else None,
                avg_completeness=round(avg_completeness, 4) if avg_completeness is not None else None,
                avg_trust=round(avg_trust, 4) if avg_trust is not None else None,
                grade_distribution=grade_dist,
            )
        )

    return benchmarks
