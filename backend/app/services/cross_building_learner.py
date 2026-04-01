"""
SwissBuildingOS - Cross-Building Learner

Learns patterns across similar buildings to predict risks, recommend actions,
and surface diagnostic coverage gaps. Extends cross_building_pattern_service
with a learning/recommendation engine.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import ALL_POLLUTANTS
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ERA_BUCKET = 10  # Match buildings within +-10 years
_DEFAULT_LIMIT = 20


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_building(db: AsyncSession, building_id: UUID) -> Building:
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")
    return building


async def _find_candidates(
    db: AsyncSession,
    ref: Building,
    limit: int,
) -> list[Building]:
    """Find candidate buildings with similar characteristics."""
    conditions = [Building.id != ref.id]

    # Same canton
    if ref.canton:
        conditions.append(Building.canton == ref.canton)

    # Construction year +-10
    if ref.construction_year:
        conditions.append(Building.construction_year >= ref.construction_year - _ERA_BUCKET)
        conditions.append(Building.construction_year <= ref.construction_year + _ERA_BUCKET)

    stmt = select(Building).where(*conditions).limit(limit * 3)  # Over-fetch for scoring
    result = await db.execute(stmt)
    return list(result.scalars().all())


def _similarity_score(ref: Building, candidate: Building) -> float:
    """Compute 0-1 similarity score between two buildings."""
    score = 0.0

    # Same canton: 0.3
    if ref.canton and candidate.canton and ref.canton == candidate.canton:
        score += 0.3

    # Construction year proximity: 0.3 (linear decay over 10 years)
    if ref.construction_year and candidate.construction_year:
        diff = abs(ref.construction_year - candidate.construction_year)
        if diff <= _ERA_BUCKET:
            score += 0.3 * (1 - diff / _ERA_BUCKET)

    # Same building type: 0.2
    if ref.building_type and candidate.building_type and ref.building_type == candidate.building_type:
        score += 0.2

    # Similar surface (within 30%): 0.2
    if ref.surface_area_m2 and candidate.surface_area_m2 and ref.surface_area_m2 > 0:
        ratio = candidate.surface_area_m2 / ref.surface_area_m2
        if 0.7 <= ratio <= 1.3:
            score += 0.2 * (1 - abs(1 - ratio) / 0.3)

    return round(min(1.0, score), 3)


async def _batch_diagnostics(
    db: AsyncSession,
    building_ids: list[UUID],
) -> dict[UUID, list[Diagnostic]]:
    """Fetch diagnostics for multiple buildings."""
    if not building_ids:
        return {}
    stmt = select(Diagnostic).where(Diagnostic.building_id.in_(building_ids))
    result = await db.execute(stmt)
    out: dict[UUID, list[Diagnostic]] = defaultdict(list)
    for d in result.scalars().all():
        out[d.building_id].append(d)
    return out


async def _batch_samples(
    db: AsyncSession,
    diag_ids: list[UUID],
) -> dict[UUID, list[Sample]]:
    """Fetch samples for multiple diagnostics, keyed by diagnostic_id."""
    if not diag_ids:
        return {}
    stmt = select(Sample).where(Sample.diagnostic_id.in_(diag_ids))
    result = await db.execute(stmt)
    out: dict[UUID, list[Sample]] = defaultdict(list)
    for s in result.scalars().all():
        out[s.diagnostic_id].append(s)
    return out


async def _batch_interventions(
    db: AsyncSession,
    building_ids: list[UUID],
) -> dict[UUID, list[Intervention]]:
    """Fetch interventions for multiple buildings."""
    if not building_ids:
        return {}
    stmt = select(Intervention).where(Intervention.building_id.in_(building_ids))
    result = await db.execute(stmt)
    out: dict[UUID, list[Intervention]] = defaultdict(list)
    for iv in result.scalars().all():
        out[iv.building_id].append(iv)
    return out


# ---------------------------------------------------------------------------
# Public API — FN1: find_similar_buildings
# ---------------------------------------------------------------------------


async def find_similar_buildings(
    db: AsyncSession,
    building_id: UUID,
    limit: int = _DEFAULT_LIMIT,
) -> list[dict]:
    """Find buildings with similar characteristics.

    Matches on:
    - construction_year +/-10 years
    - same canton
    - same building_type (if known)
    - similar surface area

    Returns list sorted by similarity_score descending.
    """
    ref = await _get_building(db, building_id)
    candidates = await _find_candidates(db, ref, limit)

    scored: list[dict] = []
    for c in candidates:
        sim = _similarity_score(ref, c)
        if sim > 0:
            scored.append(
                {
                    "building_id": c.id,
                    "address": c.address,
                    "canton": c.canton,
                    "construction_year": c.construction_year,
                    "building_type": c.building_type,
                    "similarity_score": sim,
                }
            )

    scored.sort(key=lambda x: x["similarity_score"], reverse=True)
    return scored[:limit]


# ---------------------------------------------------------------------------
# Public API — FN2: learn_from_similar
# ---------------------------------------------------------------------------


async def learn_from_similar(db: AsyncSession, building_id: UUID) -> dict:
    """Analyze diagnostics/interventions across similar buildings.

    Returns:
        diagnostic_coverage: gaps compared to peers
        common_findings: frequent pollutant/material combinations
        common_interventions: typical intervention types with cost/duration
        predicted_risks: probability of pollutants based on peer sample size
        recommendations: actionable suggestions based on peer analysis
    """
    await _get_building(db, building_id)  # Validates building exists
    similar = await find_similar_buildings(db, building_id, limit=_DEFAULT_LIMIT)

    if not similar:
        return {
            "peer_count": 0,
            "diagnostic_coverage": [],
            "common_findings": [],
            "common_interventions": [],
            "predicted_risks": [],
            "recommendations": [],
            "generated_at": datetime.now(UTC).isoformat(),
        }

    peer_ids = [s["building_id"] for s in similar]
    all_ids = [building_id, *peer_ids]
    peer_count = len(peer_ids)

    # Fetch all diagnostics and samples
    diag_map = await _batch_diagnostics(db, all_ids)
    all_diag_ids = [d.id for ds in diag_map.values() for d in ds]
    sample_map = await _batch_samples(db, all_diag_ids)
    intervention_map = await _batch_interventions(db, all_ids)

    # --- Reference building's diagnostic types ---
    ref_diags = diag_map.get(building_id, [])
    ref_diag_types = {d.diagnostic_type for d in ref_diags}

    # --- Diagnostic coverage across peers ---
    peer_diag_type_counts: dict[str, int] = defaultdict(int)
    for pid in peer_ids:
        for d in diag_map.get(pid, []):
            peer_diag_type_counts[d.diagnostic_type] += 1

    diagnostic_coverage: list[dict] = []
    for dtype, count in sorted(peer_diag_type_counts.items(), key=lambda x: -x[1]):
        pct = round(count / peer_count * 100, 1)
        has_it = dtype in ref_diag_types
        diagnostic_coverage.append(
            {
                "diagnostic_type": dtype,
                "peer_coverage_pct": pct,
                "you_have_it": has_it,
                "message": (
                    f"{pct}% des bâtiments similaires ont un diagnostic {dtype}"
                    + (" — vous aussi" if has_it else " — le vôtre en est dépourvu")
                ),
            }
        )

    # --- Common findings: pollutant + material combinations ---
    finding_counter: dict[tuple[str, str], int] = defaultdict(int)
    for pid in peer_ids:
        for d in diag_map.get(pid, []):
            for s in sample_map.get(d.id, []):
                if s.threshold_exceeded and s.pollutant_type:
                    material = s.material_category or "unknown"
                    finding_counter[(s.pollutant_type, material)] += 1

    common_findings: list[dict] = []
    for (pollutant, material), count in sorted(finding_counter.items(), key=lambda x: -x[1]):
        freq = round(count / peer_count * 100, 1)
        common_findings.append(
            {
                "pollutant": pollutant,
                "material": material,
                "frequency_pct": freq,
                "peer_count": count,
            }
        )

    # --- Common interventions ---
    intervention_type_stats: dict[str, list[dict]] = defaultdict(list)
    for pid in peer_ids:
        for iv in intervention_map.get(pid, []):
            intervention_type_stats[iv.intervention_type].append(
                {
                    "cost": iv.cost_chf,
                    "duration_days": ((iv.date_end - iv.date_start).days if iv.date_start and iv.date_end else None),
                }
            )

    common_interventions: list[dict] = []
    for itype, stats in sorted(intervention_type_stats.items(), key=lambda x: -len(x[1])):
        costs = [s["cost"] for s in stats if s["cost"] is not None]
        durations = [s["duration_days"] for s in stats if s["duration_days"] is not None]
        common_interventions.append(
            {
                "type": itype,
                "count": len(stats),
                "avg_cost_chf": round(sum(costs) / len(costs), 2) if costs else None,
                "avg_duration_days": round(sum(durations) / len(durations), 1) if durations else None,
            }
        )

    # --- Predicted risks: untested pollutants ---
    ref_sample_pollutants: set[str] = set()
    for d in ref_diags:
        for s in sample_map.get(d.id, []):
            if s.pollutant_type:
                ref_sample_pollutants.add(s.pollutant_type)

    pollutant_positive_count: dict[str, int] = defaultdict(int)
    for pid in peer_ids:
        for d in diag_map.get(pid, []):
            for s in sample_map.get(d.id, []):
                if s.threshold_exceeded and s.pollutant_type:
                    pollutant_positive_count[s.pollutant_type] += 1

    predicted_risks: list[dict] = []
    for pollutant in ALL_POLLUTANTS:
        if pollutant in ref_sample_pollutants:
            continue
        count = pollutant_positive_count.get(pollutant, 0)
        if count == 0:
            continue
        probability = round(count / peer_count, 3)
        if probability < 0.05:
            continue
        predicted_risks.append(
            {
                "pollutant": pollutant,
                "probability": probability,
                "based_on_sample_size": peer_count,
            }
        )

    predicted_risks.sort(key=lambda x: -x["probability"])

    # --- Recommendations ---
    recommendations: list[dict] = []

    # Missing diagnostics that peers commonly have
    for dc in diagnostic_coverage:
        if not dc["you_have_it"] and dc["peer_coverage_pct"] >= 50:
            recommendations.append(
                {
                    "action": f"Planifier un diagnostic {dc['diagnostic_type']}",
                    "reason": dc["message"],
                    "urgency": "high" if dc["peer_coverage_pct"] >= 75 else "medium",
                }
            )

    # Predicted untested pollutants
    for pr in predicted_risks[:3]:
        if pr["probability"] >= 0.3:
            recommendations.append(
                {
                    "action": f"Tester le polluant {pr['pollutant']}",
                    "reason": (f"{round(pr['probability'] * 100)}% des bâtiments similaires sont positifs"),
                    "urgency": "high" if pr["probability"] >= 0.5 else "medium",
                }
            )

    return {
        "peer_count": peer_count,
        "diagnostic_coverage": diagnostic_coverage,
        "common_findings": common_findings[:10],
        "common_interventions": common_interventions[:10],
        "predicted_risks": predicted_risks,
        "recommendations": recommendations,
        "generated_at": datetime.now(UTC).isoformat(),
    }
