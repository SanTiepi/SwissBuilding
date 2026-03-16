"""
SwissBuildingOS - Building Clustering Service

Group buildings by similarity for portfolio intelligence:
- Risk profile clustering (pollutant patterns)
- Construction era clustering
- Outlier detection
- High-level cluster summary
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import ALL_POLLUTANTS, ERA_RANGES, POLLUTANT_SEVERITY
from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.schemas.building_clustering import (
    ClusterBuilding,
    ClusterSummary,
    EraCluster,
    EraClusterResult,
    OutlierBuilding,
    OutlierBuildingResult,
    RiskProfileCluster,
    RiskProfileClusterResult,
)
from app.services.building_data_loader import load_org_buildings

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ERA_RECOMMENDED_ACTIONS: dict[str, list[str]] = {
    "pre_1950": [
        "Lead paint inspection mandatory",
        "Check for asbestos in plaster and insulation",
        "Assess structural integrity before renovation",
    ],
    "1950_1975": [
        "Full asbestos diagnostic required",
        "PCB testing in sealants and coatings",
        "HAP testing in waterproofing materials",
    ],
    "1975_1991": [
        "Asbestos diagnostic for late-use materials",
        "PCB testing in electrical equipment",
        "Radon measurement recommended",
    ],
    "post_1991": [
        "Radon measurement in basement areas",
        "Verify asbestos-free certification",
        "Standard pre-renovation check",
    ],
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _era_for_year(year: int | None) -> str | None:
    """Return the era label for a construction year."""
    if year is None:
        return None
    for label, low, high in ERA_RANGES:
        if (low is None or year >= low) and (high is None or year < high):
            return label
    return None


async def _all_building_pollutants(db: AsyncSession, building_ids: list[UUID]) -> dict[UUID, set[str]]:
    """Batch-fetch confirmed pollutants (threshold exceeded) for buildings."""
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


async def _building_risk_levels(db: AsyncSession, building_ids: list[UUID]) -> dict[UUID, str]:
    """Fetch overall risk level per building from BuildingRiskScore."""
    if not building_ids:
        return {}
    stmt = select(BuildingRiskScore.building_id, BuildingRiskScore.overall_risk_level).where(
        BuildingRiskScore.building_id.in_(building_ids)
    )
    result = await db.execute(stmt)
    return {row[0]: row[1] for row in result.all()}


async def _building_diagnostic_counts(db: AsyncSession, building_ids: list[UUID]) -> dict[UUID, int]:
    """Count diagnostics per building."""
    if not building_ids:
        return {}
    stmt = (
        select(Diagnostic.building_id, func.count(Diagnostic.id))
        .where(Diagnostic.building_id.in_(building_ids))
        .group_by(Diagnostic.building_id)
    )
    result = await db.execute(stmt)
    return {row[0]: row[1] for row in result.all()}


def _risk_signature(pollutants: set[str], risk_level: str | None) -> dict[str, str]:
    """Build a pollutant -> level mapping for a building."""
    level = risk_level or "unknown"
    return {p: level for p in sorted(pollutants)} if pollutants else {"none": level}


def _signature_key(sig: dict[str, str]) -> str:
    """Create a hashable key from a risk signature."""
    return "|".join(f"{k}={v}" for k, v in sorted(sig.items()))


def _cb(b: Building) -> ClusterBuilding:
    return ClusterBuilding(building_id=b.id, address=b.address)


# ---------------------------------------------------------------------------
# FN1: cluster_by_risk_profile
# ---------------------------------------------------------------------------


async def cluster_by_risk_profile(db: AsyncSession, org_id: UUID) -> RiskProfileClusterResult:
    """Group buildings with similar risk profiles (pollutant patterns)."""
    buildings = await load_org_buildings(db, org_id)
    if not buildings:
        return RiskProfileClusterResult(
            organization_id=org_id,
            clusters=[],
            total_buildings_analyzed=0,
            generated_at=datetime.now(UTC),
        )

    bids = [b.id for b in buildings]
    pollutant_map = await _all_building_pollutants(db, bids)
    risk_levels = await _building_risk_levels(db, bids)
    b_by_id = {b.id: b for b in buildings}

    # Group by signature key
    groups: dict[str, list[UUID]] = defaultdict(list)
    sig_store: dict[str, dict[str, str]] = {}
    for b in buildings:
        sig = _risk_signature(pollutant_map.get(b.id, set()), risk_levels.get(b.id))
        key = _signature_key(sig)
        groups[key].append(b.id)
        sig_store[key] = sig

    clusters: list[RiskProfileCluster] = []
    for idx, (key, bid_list) in enumerate(groups.items()):
        sig = sig_store[key]
        # Dominant risk = pollutant with highest severity in signature
        pollutants_in_sig = [p for p in sig if p != "none"]
        if pollutants_in_sig:
            dominant = max(pollutants_in_sig, key=lambda p: POLLUTANT_SEVERITY.get(p, 0))
        else:
            dominant = "none"

        clusters.append(
            RiskProfileCluster(
                cluster_id=f"risk-{idx}",
                risk_signature=sig,
                buildings=[_cb(b_by_id[bid]) for bid in bid_list],
                cluster_size=len(bid_list),
                dominant_risk=dominant,
            )
        )

    # Sort by cluster size descending
    clusters.sort(key=lambda c: c.cluster_size, reverse=True)

    return RiskProfileClusterResult(
        organization_id=org_id,
        clusters=clusters,
        total_buildings_analyzed=len(buildings),
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN2: cluster_by_construction_era
# ---------------------------------------------------------------------------


async def cluster_by_construction_era(db: AsyncSession, org_id: UUID) -> EraClusterResult:
    """Group buildings by construction period with era-specific insights."""
    buildings = await load_org_buildings(db, org_id)

    bids = [b.id for b in buildings]
    pollutant_map = await _all_building_pollutants(db, bids) if bids else {}

    era_groups: dict[str, list[Building]] = defaultdict(list)
    for b in buildings:
        era = _era_for_year(b.construction_year)
        if era:
            era_groups[era].append(b)

    era_clusters: list[EraCluster] = []
    for era_label, _low, _high in ERA_RANGES:
        group = era_groups.get(era_label, [])
        # Collect common pollutant risks
        pollutant_counter: dict[str, int] = defaultdict(int)
        for b in group:
            for p in pollutant_map.get(b.id, set()):
                pollutant_counter[p] += 1
        common_risks = sorted(pollutant_counter.keys(), key=lambda p: pollutant_counter[p], reverse=True)

        era_clusters.append(
            EraCluster(
                era_label=era_label,
                building_count=len(group),
                buildings=[_cb(b) for b in group],
                common_pollutant_risks=common_risks,
                recommended_actions=_ERA_RECOMMENDED_ACTIONS.get(era_label, []),
            )
        )

    return EraClusterResult(
        organization_id=org_id,
        era_clusters=era_clusters,
        total_buildings_analyzed=len(buildings),
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN3: find_outlier_buildings
# ---------------------------------------------------------------------------


async def find_outlier_buildings(db: AsyncSession, org_id: UUID) -> OutlierBuildingResult:
    """Find buildings that deviate from their cluster norms."""
    buildings = await load_org_buildings(db, org_id)
    if not buildings:
        return OutlierBuildingResult(
            organization_id=org_id,
            outliers=[],
            total_buildings_analyzed=0,
            generated_at=datetime.now(UTC),
        )

    bids = [b.id for b in buildings]
    pollutant_map = await _all_building_pollutants(db, bids)
    risk_levels = await _building_risk_levels(db, bids)
    diag_counts = await _building_diagnostic_counts(db, bids)
    b_by_id = {b.id: b for b in buildings}

    # Group by era to find peers
    era_groups: dict[str, list[UUID]] = defaultdict(list)
    for b in buildings:
        era = _era_for_year(b.construction_year) or "unknown"
        era_groups[era].append(b.id)

    outliers: list[OutlierBuilding] = []
    _RISK_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4, "unknown": 0}

    for era, peer_ids in era_groups.items():
        if len(peer_ids) < 2:
            continue

        # Compute peer averages
        peer_risk_values = [_RISK_ORDER.get(risk_levels.get(pid, "unknown"), 0) for pid in peer_ids]
        avg_risk = sum(peer_risk_values) / len(peer_risk_values)

        peer_diag_counts = [diag_counts.get(pid, 0) for pid in peer_ids]
        avg_diags = sum(peer_diag_counts) / len(peer_diag_counts)

        # Common pollutants in this era group
        era_pollutant_counter: dict[str, int] = defaultdict(int)
        for pid in peer_ids:
            for p in pollutant_map.get(pid, set()):
                era_pollutant_counter[p] += 1
        common_pollutants = {p for p, c in era_pollutant_counter.items() if c >= len(peer_ids) * 0.5}

        for bid in peer_ids:
            b = b_by_id[bid]
            b_risk = _RISK_ORDER.get(risk_levels.get(bid, "unknown"), 0)
            b_pollutants = pollutant_map.get(bid, set())
            b_diags = diag_counts.get(bid, 0)

            # Check: risk higher than peers
            if avg_risk > 0 and b_risk > avg_risk * 1.5:
                severity = min((b_risk - avg_risk) / 4.0, 1.0)
                outliers.append(
                    OutlierBuilding(
                        outlier_id=bid,
                        building_address=b.address,
                        deviation_type="risk_higher_than_peers",
                        severity=round(severity, 2),
                        explanation=(
                            f"Risk level is significantly higher than {era} era peers "
                            f"(building: {risk_levels.get(bid, 'unknown')}, "
                            f"peer average: {avg_risk:.1f}/4)."
                        ),
                    )
                )

            # Check: unusual pollutant mix
            unusual = b_pollutants - common_pollutants
            if unusual and common_pollutants:
                severity = min(len(unusual) / len(ALL_POLLUTANTS), 1.0)
                outliers.append(
                    OutlierBuilding(
                        outlier_id=bid,
                        building_address=b.address,
                        deviation_type="unusual_pollutant_mix",
                        severity=round(severity, 2),
                        explanation=(
                            f"Contains uncommon pollutants for {era} era: "
                            f"{', '.join(sorted(unusual))}. "
                            f"Common in peers: {', '.join(sorted(common_pollutants))}."
                        ),
                    )
                )

            # Check: missing diagnostics vs peers
            if avg_diags > 0 and b_diags < avg_diags * 0.5:
                severity = min((avg_diags - b_diags) / max(avg_diags, 1), 1.0)
                outliers.append(
                    OutlierBuilding(
                        outlier_id=bid,
                        building_address=b.address,
                        deviation_type="missing_diagnostics_vs_peers",
                        severity=round(severity, 2),
                        explanation=(
                            f"Only {b_diags} diagnostic(s) vs peer average of {avg_diags:.1f} for {era} era buildings."
                        ),
                    )
                )

    # Sort by severity descending
    outliers.sort(key=lambda o: o.severity, reverse=True)

    return OutlierBuildingResult(
        organization_id=org_id,
        outliers=outliers,
        total_buildings_analyzed=len(buildings),
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN4: get_cluster_summary
# ---------------------------------------------------------------------------


async def get_cluster_summary(db: AsyncSession, org_id: UUID) -> ClusterSummary:
    """High-level clustering overview for the organization."""
    buildings = await load_org_buildings(db, org_id)
    if not buildings:
        return ClusterSummary(
            organization_id=org_id,
            total_buildings=0,
            total_clusters=0,
            largest_cluster_size=0,
            most_common_risk_pattern="none",
            buildings_without_cluster=0,
            diversity_score=0.0,
            generated_at=datetime.now(UTC),
        )

    bids = [b.id for b in buildings]
    pollutant_map = await _all_building_pollutants(db, bids)
    risk_levels = await _building_risk_levels(db, bids)

    # Build clusters by risk signature
    groups: dict[str, list[UUID]] = defaultdict(list)
    sig_store: dict[str, dict[str, str]] = {}
    for b in buildings:
        sig = _risk_signature(pollutant_map.get(b.id, set()), risk_levels.get(b.id))
        key = _signature_key(sig)
        groups[key].append(b.id)
        sig_store[key] = sig

    total_clusters = len(groups)
    largest_size = max(len(v) for v in groups.values()) if groups else 0

    # Most common pattern = largest cluster's signature
    most_common_key = max(groups, key=lambda k: len(groups[k])) if groups else ""
    most_common_sig = sig_store.get(most_common_key, {})
    pollutants_in_sig = [p for p in most_common_sig if p != "none"]
    if pollutants_in_sig:
        most_common_pattern = ", ".join(sorted(pollutants_in_sig))
    else:
        most_common_pattern = "no confirmed pollutants"

    # Buildings without cluster = singletons
    buildings_without = sum(1 for v in groups.values() if len(v) == 1)

    # Diversity score: normalized entropy
    import math

    n = len(buildings)
    if n <= 1 or total_clusters <= 1:
        diversity = 0.0
    else:
        entropy = 0.0
        for v in groups.values():
            p = len(v) / n
            if p > 0:
                entropy -= p * math.log2(p)
        max_entropy = math.log2(total_clusters)
        diversity = round(entropy / max_entropy, 3) if max_entropy > 0 else 0.0

    return ClusterSummary(
        organization_id=org_id,
        total_buildings=n,
        total_clusters=total_clusters,
        largest_cluster_size=largest_size,
        most_common_risk_pattern=most_common_pattern,
        buildings_without_cluster=buildings_without,
        diversity_score=min(diversity, 1.0),
        generated_at=datetime.now(UTC),
    )
