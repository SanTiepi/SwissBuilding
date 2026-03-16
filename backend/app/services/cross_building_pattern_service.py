"""
SwissBuildingOS - Cross-Building Pattern Service

Detects systemic patterns across buildings within an organization:
- Same construction era + same pollutants = systemic issue
- Same contractor + same deficiency = contractor quality issue
- Same neighborhood + same radon levels = geographic pattern

Also provides similarity search, geographic clustering, and
undiscovered-pollutant prediction based on peer analysis.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.schemas.cross_building_pattern import (
    AffectedBuilding,
    ClusterBuilding,
    CrossBuildingPattern,
    GeographicCluster,
    GeographicClusterResult,
    PatternDetectionResult,
    PollutantPrediction,
    SimilarBuilding,
    SimilarBuildingsResult,
    UndiscoveredPollutantResult,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_POLLUTANT_TYPES = ["asbestos", "pcb", "lead", "hap", "radon"]
_ERA_BUCKET_SIZE = 10  # group by decade

# Minimum buildings sharing a trait to flag a pattern
_MIN_PATTERN_SIZE = 2

# Haversine earth radius in km
_EARTH_RADIUS_KM = 6371.0

# Cluster radius threshold (km)
_CLUSTER_RADIUS_KM = 2.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _decade_label(year: int | None) -> str | None:
    if year is None:
        return None
    return f"{(year // _ERA_BUCKET_SIZE) * _ERA_BUCKET_SIZE}s"


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in km between two lat/lon points."""
    rlat1, rlon1 = math.radians(lat1), math.radians(lon1)
    rlat2, rlon2 = math.radians(lat2), math.radians(lon2)
    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def _affected(b: Building) -> AffectedBuilding:
    return AffectedBuilding(
        building_id=b.id,
        address=b.address,
        canton=b.canton,
        construction_year=b.construction_year,
    )


async def _org_buildings(db: AsyncSession, org_id: UUID) -> list[Building]:
    """Fetch all buildings created by users that belong to *org_id*."""
    from app.services.building_data_loader import load_org_buildings

    return await load_org_buildings(db, org_id)


async def _building_pollutants(db: AsyncSession, building_id: UUID) -> set[str]:
    """Return set of pollutant_type values found (threshold exceeded) for a building."""
    stmt = (
        select(Sample.pollutant_type)
        .join(Diagnostic, Diagnostic.id == Sample.diagnostic_id)
        .where(
            Diagnostic.building_id == building_id,
            Sample.threshold_exceeded.is_(True),
            Sample.pollutant_type.isnot(None),
        )
        .distinct()
    )
    result = await db.execute(stmt)
    return {row[0] for row in result.all()}


async def _all_building_pollutants(db: AsyncSession, building_ids: list[UUID]) -> dict[UUID, set[str]]:
    """Batch-fetch pollutants for multiple buildings."""
    if not building_ids:
        return {}
    stmt = (
        select(Diagnostic.building_id, Sample.pollutant_type)
        .join(Diagnostic, Diagnostic.id == Sample.diagnostic_id)
        .where(
            Diagnostic.building_id.in_(building_ids),
            Sample.threshold_exceeded.is_(True),
            Sample.pollutant_type.isnot(None),
        )
        .distinct()
    )
    result = await db.execute(stmt)
    out: dict[UUID, set[str]] = defaultdict(set)
    for bid, pt in result.all():
        out[bid].add(pt)
    return out


# ---------------------------------------------------------------------------
# FN1: detect_patterns
# ---------------------------------------------------------------------------


async def detect_patterns(db: AsyncSession, org_id: UUID) -> PatternDetectionResult:
    """Detect cross-building patterns within an organisation."""
    buildings = await _org_buildings(db, org_id)
    if not buildings:
        return PatternDetectionResult(
            organization_id=org_id,
            patterns=[],
            total_buildings_analyzed=0,
            generated_at=datetime.now(UTC),
        )

    bids = [b.id for b in buildings]
    pollutant_map = await _all_building_pollutants(db, bids)
    b_by_id = {b.id: b for b in buildings}

    patterns: list[CrossBuildingPattern] = []

    # --- Systemic: same decade + same pollutant --------------------------
    decade_groups: dict[str, list[Building]] = defaultdict(list)
    for b in buildings:
        d = _decade_label(b.construction_year)
        if d:
            decade_groups[d].append(b)

    for decade, group in decade_groups.items():
        pollutant_counter: dict[str, list[Building]] = defaultdict(list)
        for b in group:
            for p in pollutant_map.get(b.id, set()):
                pollutant_counter[p].append(b)

        for pollutant, affected_blds in pollutant_counter.items():
            if len(affected_blds) >= _MIN_PATTERN_SIZE:
                confidence = min(1.0, len(affected_blds) / len(group))
                patterns.append(
                    CrossBuildingPattern(
                        pattern_type="systemic_pollutant",
                        label=f"{pollutant.capitalize()} in {decade} buildings",
                        description=(
                            f"{len(affected_blds)} buildings from the {decade} share "
                            f"{pollutant} contamination, suggesting era-specific "
                            f"construction materials."
                        ),
                        affected_buildings=[_affected(b) for b in affected_blds],
                        confidence=confidence,
                        recommended_action=(
                            f"Prioritise {pollutant} testing for remaining {decade} buildings in this portfolio."
                        ),
                    )
                )

    # --- Contractor quality: same intervention contractor + deficiency ---
    intervention_stmt = select(Intervention).where(Intervention.building_id.in_(bids))
    intervention_result = await db.execute(intervention_stmt)
    interventions = list(intervention_result.scalars().all())

    contractor_groups: dict[str, list[tuple[Intervention, Building]]] = defaultdict(list)
    for iv in interventions:
        contractor = getattr(iv, "contractor_name", None) or getattr(iv, "assigned_to", None)
        if contractor and iv.status == "cancelled":
            b = b_by_id.get(iv.building_id)
            if b:
                contractor_groups[str(contractor)].append((iv, b))

    for contractor, items in contractor_groups.items():
        if len(items) >= _MIN_PATTERN_SIZE:
            affected_blds = list({it[1].id: it[1] for _, it in enumerate(items)}.values())
            # deduplicate by building — items is list of (intervention, building)
            seen: dict[UUID, Building] = {}
            for _iv, b in items:
                seen[b.id] = b
            affected_blds = list(seen.values())
            confidence = min(1.0, len(items) / 5)
            patterns.append(
                CrossBuildingPattern(
                    pattern_type="contractor_quality",
                    label=f"Contractor {contractor}: repeated issues",
                    description=(
                        f"Contractor '{contractor}' has {len(items)} cancelled "
                        f"interventions across {len(affected_blds)} buildings."
                    ),
                    affected_buildings=[_affected(b) for b in affected_blds],
                    confidence=confidence,
                    recommended_action=(
                        f"Review contractor '{contractor}' performance and consider alternative providers."
                    ),
                )
            )

    # --- Geographic: same postal code + shared pollutants ----------------
    postal_groups: dict[str, list[Building]] = defaultdict(list)
    for b in buildings:
        postal_groups[b.postal_code].append(b)

    for postal, group in postal_groups.items():
        if len(group) < _MIN_PATTERN_SIZE:
            continue
        # Check if radon is common
        radon_blds = [b for b in group if "radon" in pollutant_map.get(b.id, set())]
        if len(radon_blds) >= _MIN_PATTERN_SIZE:
            confidence = min(1.0, len(radon_blds) / len(group))
            patterns.append(
                CrossBuildingPattern(
                    pattern_type="geographic",
                    label=f"Radon cluster in postal code {postal}",
                    description=(
                        f"{len(radon_blds)} buildings in postal code {postal} show "
                        f"elevated radon, suggesting geological radon exposure."
                    ),
                    affected_buildings=[_affected(b) for b in radon_blds],
                    confidence=confidence,
                    recommended_action=(f"Conduct radon measurements in all buildings within postal code {postal}."),
                )
            )

    return PatternDetectionResult(
        organization_id=org_id,
        patterns=patterns,
        total_buildings_analyzed=len(buildings),
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN2: find_similar_buildings
# ---------------------------------------------------------------------------


async def find_similar_buildings(db: AsyncSession, building_id: UUID) -> SimilarBuildingsResult:
    """Find buildings with similar characteristics to the reference building."""
    stmt = select(Building).where(Building.id == building_id)
    result = await db.execute(stmt)
    ref = result.scalar_one_or_none()
    if ref is None:
        raise ValueError(f"Building {building_id} not found")

    # Fetch candidates: same canton OR similar era
    conditions = [Building.id != building_id]
    candidate_stmt = select(Building).where(*conditions)
    cand_result = await db.execute(candidate_stmt)
    candidates = list(cand_result.scalars().all())

    ref_pollutants = await _building_pollutants(db, building_id)
    cand_ids = [c.id for c in candidates]
    cand_pollutants = await _all_building_pollutants(db, cand_ids)

    scored: list[SimilarBuilding] = []
    for c in candidates:
        score = 0.0
        traits: list[str] = []

        # Same canton
        if c.canton == ref.canton:
            score += 0.25
            traits.append(f"same_canton:{c.canton}")

        # Same decade
        if (
            c.construction_year
            and ref.construction_year
            and _decade_label(c.construction_year) == _decade_label(ref.construction_year)
        ):
            score += 0.25
            traits.append(f"same_era:{_decade_label(c.construction_year)}")

        # Similar size (within 30%)
        if c.surface_area_m2 and ref.surface_area_m2 and ref.surface_area_m2 > 0:
            ratio = c.surface_area_m2 / ref.surface_area_m2
            if 0.7 <= ratio <= 1.3:
                score += 0.15
                traits.append("similar_size")

        # Same building type
        if c.building_type == ref.building_type:
            score += 0.1
            traits.append(f"same_type:{c.building_type}")

        # Shared pollutants
        c_poll = cand_pollutants.get(c.id, set())
        shared = ref_pollutants & c_poll
        if shared:
            score += 0.25 * (len(shared) / max(len(ref_pollutants | c_poll), 1))
            traits.append(f"shared_pollutants:{','.join(sorted(shared))}")

        if score > 0 and traits:
            scored.append(
                SimilarBuilding(
                    building_id=c.id,
                    address=c.address,
                    canton=c.canton,
                    construction_year=c.construction_year,
                    similarity_score=round(min(score, 1.0), 3),
                    shared_traits=traits,
                )
            )

    scored.sort(key=lambda s: s.similarity_score, reverse=True)

    return SimilarBuildingsResult(
        reference_building_id=building_id,
        similar_buildings=scored[:20],
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN3: get_geographic_clusters
# ---------------------------------------------------------------------------


async def get_geographic_clusters(db: AsyncSession, org_id: UUID) -> GeographicClusterResult:
    """Compute spatial clusters of risk within an organisation's buildings."""
    buildings = await _org_buildings(db, org_id)
    geo_buildings = [b for b in buildings if b.latitude is not None and b.longitude is not None]

    bids = [b.id for b in geo_buildings]
    pollutant_map = await _all_building_pollutants(db, bids)

    # Simple postal-code-based clustering (works without PostGIS)
    postal_groups: dict[str, list[Building]] = defaultdict(list)
    for b in geo_buildings:
        postal_groups[b.postal_code].append(b)

    clusters: list[GeographicCluster] = []
    idx = 0
    for postal, group in postal_groups.items():
        if len(group) < _MIN_PATTERN_SIZE:
            continue

        # Determine dominant risk factor
        pollutant_counter: dict[str, int] = defaultdict(int)
        for b in group:
            for p in pollutant_map.get(b.id, set()):
                pollutant_counter[p] += 1

        risk_factor = "mixed"
        if pollutant_counter:
            risk_factor = max(pollutant_counter, key=pollutant_counter.get)  # type: ignore[arg-type]

        # Compute centroid
        avg_lat = sum(b.latitude for b in group) / len(group)  # type: ignore[arg-type]
        avg_lon = sum(b.longitude for b in group) / len(group)  # type: ignore[arg-type]

        # Compute radius
        max_dist = 0.0
        for b in group:
            d = _haversine(avg_lat, avg_lon, b.latitude, b.longitude)  # type: ignore[arg-type]
            max_dist = max(max_dist, d)

        # Determine average risk level from risk scores
        risk_stmt = select(BuildingRiskScore).where(BuildingRiskScore.building_id.in_([b.id for b in group]))
        risk_result = await db.execute(risk_stmt)
        risk_scores = list(risk_result.scalars().all())
        avg_risk = None
        if risk_scores:
            levels = [rs.overall_risk_level for rs in risk_scores if rs.overall_risk_level]
            if levels:
                avg_risk = max(set(levels), key=levels.count)

        clusters.append(
            GeographicCluster(
                cluster_id=f"cluster-{idx}",
                label=f"Cluster {postal} ({len(group)} buildings)",
                risk_factor=risk_factor,
                center_lat=round(avg_lat, 6),
                center_lon=round(avg_lon, 6),
                radius_km=round(max_dist, 2),
                buildings=[
                    ClusterBuilding(
                        building_id=b.id,
                        address=b.address,
                        latitude=b.latitude,
                        longitude=b.longitude,
                    )
                    for b in group
                ],
                avg_risk_level=avg_risk,
            )
        )
        idx += 1

    return GeographicClusterResult(
        organization_id=org_id,
        clusters=clusters,
        total_buildings=len(geo_buildings),
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN4: predict_undiscovered_pollutants
# ---------------------------------------------------------------------------


async def predict_undiscovered_pollutants(db: AsyncSession, building_id: UUID) -> UndiscoveredPollutantResult:
    """Predict untested pollutants based on peer buildings."""
    stmt = select(Building).where(Building.id == building_id)
    result = await db.execute(stmt)
    ref = result.scalar_one_or_none()
    if ref is None:
        raise ValueError(f"Building {building_id} not found")

    # Get all tested pollutant types (including not-exceeded)
    tested_stmt = (
        select(Sample.pollutant_type)
        .join(Diagnostic, Diagnostic.id == Sample.diagnostic_id)
        .where(
            Diagnostic.building_id == building_id,
            Sample.pollutant_type.isnot(None),
        )
        .distinct()
    )
    tested_result = await db.execute(tested_stmt)
    tested = {row[0] for row in tested_result.all()}

    # Find peer buildings (same canton + similar era)
    peer_conditions = [Building.id != building_id, Building.canton == ref.canton]
    if ref.construction_year:
        decade_start = (ref.construction_year // 10) * 10
        peer_conditions.append(Building.construction_year >= decade_start)
        peer_conditions.append(Building.construction_year < decade_start + 20)

    peer_stmt = select(Building).where(*peer_conditions)
    peer_result = await db.execute(peer_stmt)
    peers = list(peer_result.scalars().all())

    peer_ids = [p.id for p in peers]
    peer_pollutants = await _all_building_pollutants(db, peer_ids)

    # Count pollutant frequency across peers
    pollutant_freq: dict[str, int] = defaultdict(int)
    for _pid, pols in peer_pollutants.items():
        for p in pols:
            pollutant_freq[p] += 1

    predictions: list[PollutantPrediction] = []
    for pollutant in _POLLUTANT_TYPES:
        if pollutant in tested:
            continue  # Already tested
        freq = pollutant_freq.get(pollutant, 0)
        if freq == 0 or not peers:
            continue

        probability = round(freq / len(peers), 3)
        if probability < 0.1:
            continue  # Too low to flag

        era_note = f" ({_decade_label(ref.construction_year)})" if ref.construction_year else ""
        predictions.append(
            PollutantPrediction(
                pollutant_type=pollutant,
                probability=probability,
                basis=(
                    f"{freq}/{len(peers)} peer buildings in {ref.canton}{era_note} "
                    f"have confirmed {pollutant} contamination."
                ),
                peer_count=freq,
                recommendation=(
                    f"Schedule {pollutant} testing — {round(probability * 100)}% of similar buildings are affected."
                ),
            )
        )

    predictions.sort(key=lambda p: p.probability, reverse=True)

    return UndiscoveredPollutantResult(
        building_id=building_id,
        predictions=predictions,
        peer_buildings_used=len(peers),
        generated_at=datetime.now(UTC),
    )
