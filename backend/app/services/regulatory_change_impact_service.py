"""
SwissBuildingOS - Regulatory Change Impact Analyzer

Simulates the impact of regulatory threshold changes on existing buildings.
Provides sensitivity analysis and compliance forecasting for portfolio management.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.services.building_data_loader import load_org_buildings
from app.services.compliance_engine import SWISS_THRESHOLDS

# ---------------------------------------------------------------------------
# Cost estimation constants (CHF per incident, rough Swiss market rates)
# ---------------------------------------------------------------------------
_REMEDIATION_COST_PER_POLLUTANT: dict[str, float] = {
    "asbestos": 25_000.0,
    "pcb": 18_000.0,
    "lead": 12_000.0,
    "hap": 15_000.0,
    "radon": 8_000.0,
}

_DEFAULT_REMEDIATION_COST = 15_000.0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_threshold_entry(pollutant: str, measurement_type: str) -> dict | None:
    """Retrieve a threshold entry from SWISS_THRESHOLDS."""
    entries = SWISS_THRESHOLDS.get(pollutant.lower(), {})
    return entries.get(measurement_type)


def _remediation_cost(pollutant: str) -> float:
    return _REMEDIATION_COST_PER_POLLUTANT.get(pollutant.lower(), _DEFAULT_REMEDIATION_COST)


async def _load_samples_with_buildings(
    db: AsyncSession,
    pollutant: str,
    org_id: UUID | None = None,
) -> list[tuple[Sample, Building]]:
    """Load all samples for a given pollutant, joined with building info."""
    stmt = (
        select(Sample, Building)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .join(Building, Diagnostic.building_id == Building.id)
        .where(Sample.pollutant_type == pollutant.lower())
        .where(Sample.concentration.is_not(None))
    )
    if org_id is not None:
        org_buildings = await load_org_buildings(db, org_id)
        org_building_ids = [b.id for b in org_buildings]
        if not org_building_ids:
            return []
        stmt = stmt.where(Building.id.in_(org_building_ids))
    result = await db.execute(stmt)
    return list(result.all())


async def _load_all_samples_with_buildings(
    db: AsyncSession,
    org_id: UUID | None = None,
) -> list[tuple[Sample, Building]]:
    """Load all samples with concentration data, joined with buildings."""
    stmt = (
        select(Sample, Building)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .join(Building, Diagnostic.building_id == Building.id)
        .where(Sample.concentration.is_not(None))
    )
    if org_id is not None:
        org_buildings = await load_org_buildings(db, org_id)
        org_building_ids = [b.id for b in org_buildings]
        if not org_building_ids:
            return []
        stmt = stmt.where(Building.id.in_(org_building_ids))
    result = await db.execute(stmt)
    return list(result.all())


async def _count_buildings(db: AsyncSession, org_id: UUID | None = None) -> int:
    """Count total buildings, optionally filtered by org."""
    if org_id is not None:
        buildings = await load_org_buildings(db, org_id)
        return len(buildings)
    stmt = select(Building)
    result = await db.execute(stmt)
    return len(result.all())


# ---------------------------------------------------------------------------
# 1. simulate_threshold_change
# ---------------------------------------------------------------------------


async def simulate_threshold_change(
    db: AsyncSession,
    pollutant: str,
    new_threshold: float,
    measurement_type: str = "material_content",
    org_id: UUID | None = None,
) -> dict:
    """
    Simulate a regulatory threshold change for a pollutant.

    Returns impact analysis: how many buildings become newly non-compliant,
    which ones are affected, and estimated remediation costs.
    """
    entry = _get_threshold_entry(pollutant, measurement_type)
    if entry is None:
        raise ValueError(f"No threshold found for pollutant={pollutant}, measurement_type={measurement_type}")

    current_threshold = entry["threshold"]
    unit = entry["unit"]
    legal_ref = entry.get("legal_ref")

    rows = await _load_samples_with_buildings(db, pollutant, org_id)

    # Group by building — take max concentration per building
    building_max: dict[UUID, tuple[float, Building]] = {}
    for sample, building in rows:
        bid = building.id
        if bid not in building_max or sample.concentration > building_max[bid][0]:
            building_max[bid] = (sample.concentration, building)

    total_analyzed = len(building_max)
    currently_non_compliant = 0
    non_compliant_after = 0
    newly_non_compliant = 0
    affected_buildings = []

    for bid, (max_conc, building) in building_max.items():
        was_non_compliant = max_conc >= current_threshold
        is_non_compliant_after = max_conc >= new_threshold

        if was_non_compliant:
            currently_non_compliant += 1

        if is_non_compliant_after:
            non_compliant_after += 1

        becomes_newly = not was_non_compliant and is_non_compliant_after
        if becomes_newly:
            newly_non_compliant += 1

        if is_non_compliant_after:
            margin = ((max_conc - new_threshold) / new_threshold * 100) if new_threshold > 0 else 0.0
            affected_buildings.append(
                {
                    "building_id": bid,
                    "address": building.address,
                    "city": building.city,
                    "canton": building.canton,
                    "pollutant": pollutant,
                    "current_concentration": max_conc,
                    "current_threshold": current_threshold,
                    "new_threshold": new_threshold,
                    "margin_percent": round(margin, 1),
                    "was_compliant": not was_non_compliant,
                    "becomes_non_compliant": becomes_newly,
                }
            )

    # Sort affected by margin descending (worst first)
    affected_buildings.sort(key=lambda b: b["margin_percent"], reverse=True)

    return {
        "pollutant": pollutant,
        "measurement_type": measurement_type,
        "current_threshold": current_threshold,
        "new_threshold": new_threshold,
        "unit": unit,
        "legal_ref": legal_ref,
        "total_buildings_analyzed": total_analyzed,
        "currently_non_compliant": currently_non_compliant,
        "newly_non_compliant": newly_non_compliant,
        "total_non_compliant_after": non_compliant_after,
        "affected_buildings": affected_buildings,
        "estimated_additional_remediation_cost_chf": round(newly_non_compliant * _remediation_cost(pollutant), 2),
    }


# ---------------------------------------------------------------------------
# 2. analyze_regulation_impact
# ---------------------------------------------------------------------------


async def analyze_regulation_impact(
    db: AsyncSession,
    regulation_changes: list[dict],
    org_id: UUID | None = None,
) -> dict:
    """
    Analyze multi-regulation changes simultaneously.

    Each change dict must have: pollutant, new_threshold, and optionally
    measurement_type.
    """
    simulations = []
    all_affected_building_ids: dict[UUID, int] = {}  # bid -> count of changes

    for change in regulation_changes:
        sim = await simulate_threshold_change(
            db,
            pollutant=change["pollutant"],
            new_threshold=change["new_threshold"],
            measurement_type=change.get("measurement_type", "material_content"),
            org_id=org_id,
        )
        simulations.append(sim)

        for ab in sim["affected_buildings"]:
            bid = ab["building_id"]
            all_affected_building_ids[bid] = all_affected_building_ids.get(bid, 0) + 1

    # Compute cross-simulation aggregates
    unique_buildings = set()
    for sim in simulations:
        unique_buildings.update({b["building_id"] for b in sim["affected_buildings"]})

    max_analyzed = max((s["total_buildings_analyzed"] for s in simulations), default=0)

    affected_by_multiple = sum(1 for count in all_affected_building_ids.values() if count > 1)
    total_cost = sum(s["estimated_additional_remediation_cost_chf"] for s in simulations)

    return {
        "changes": simulations,
        "total_buildings_analyzed": max_analyzed,
        "buildings_affected_by_any_change": len(unique_buildings),
        "buildings_affected_by_multiple_changes": affected_by_multiple,
        "total_estimated_cost_chf": round(total_cost, 2),
    }


# ---------------------------------------------------------------------------
# 3. get_regulatory_sensitivity
# ---------------------------------------------------------------------------


async def get_regulatory_sensitivity(
    db: AsyncSession,
    building_id: UUID,
) -> dict:
    """
    Compute regulatory sensitivity for a single building.

    For each pollutant with samples, computes margin to threshold and
    predicts compliance impact if thresholds drop by 10/20/50%.
    """
    # Load building
    building_result = await db.execute(select(Building).where(Building.id == building_id))
    building = building_result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    # Load samples for this building
    stmt = (
        select(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(Diagnostic.building_id == building_id)
        .where(Sample.concentration.is_not(None))
        .where(Sample.pollutant_type.is_not(None))
    )
    result = await db.execute(stmt)
    samples = list(result.scalars().all())

    # Group samples by pollutant
    by_pollutant: dict[str, list[Sample]] = {}
    for s in samples:
        key = s.pollutant_type.lower()
        by_pollutant.setdefault(key, []).append(s)

    sensitivities = []
    vulnerability_scores = []

    for pollutant, entries_dict in SWISS_THRESHOLDS.items():
        for mtype, entry in entries_dict.items():
            threshold = entry["threshold"]
            unit = entry["unit"]

            pollutant_samples = by_pollutant.get(pollutant, [])
            sample_count = len(pollutant_samples)

            if sample_count == 0:
                sensitivities.append(
                    {
                        "pollutant": pollutant,
                        "measurement_type": mtype,
                        "current_threshold": threshold,
                        "unit": unit,
                        "max_concentration": None,
                        "margin_percent": None,
                        "is_currently_compliant": True,
                        "non_compliant_if_threshold_drops_10_pct": False,
                        "non_compliant_if_threshold_drops_20_pct": False,
                        "non_compliant_if_threshold_drops_50_pct": False,
                        "sample_count": 0,
                    }
                )
                continue

            max_conc = max(s.concentration for s in pollutant_samples)
            margin = ((threshold - max_conc) / threshold * 100) if threshold > 0 else 0.0
            is_compliant = max_conc < threshold

            sens = {
                "pollutant": pollutant,
                "measurement_type": mtype,
                "current_threshold": threshold,
                "unit": unit,
                "max_concentration": max_conc,
                "margin_percent": round(margin, 1),
                "is_currently_compliant": is_compliant,
                "non_compliant_if_threshold_drops_10_pct": max_conc >= threshold * 0.9,
                "non_compliant_if_threshold_drops_20_pct": max_conc >= threshold * 0.8,
                "non_compliant_if_threshold_drops_50_pct": max_conc >= threshold * 0.5,
                "sample_count": sample_count,
            }
            sensitivities.append(sens)

            # Vulnerability: how close to threshold (lower margin = more vulnerable)
            if is_compliant and margin is not None:
                vulnerability_scores.append(max(0, 100 - margin))

    # Overall vulnerability
    if not vulnerability_scores:
        overall = "low"
    else:
        avg_vuln = sum(vulnerability_scores) / len(vulnerability_scores)
        if avg_vuln >= 80:
            overall = "critical"
        elif avg_vuln >= 60:
            overall = "high"
        elif avg_vuln >= 40:
            overall = "medium"
        else:
            overall = "low"

    return {
        "building_id": building_id,
        "address": building.address,
        "city": building.city,
        "canton": building.canton,
        "sensitivities": sensitivities,
        "overall_vulnerability": overall,
    }


# ---------------------------------------------------------------------------
# 4. forecast_compliance_risk
# ---------------------------------------------------------------------------


async def forecast_compliance_risk(
    db: AsyncSession,
    org_id: UUID | None = None,
) -> dict:
    """
    Portfolio-level compliance risk forecast.

    Identifies buildings most vulnerable to regulatory tightening,
    ranked by proximity to current thresholds.
    """
    rows = await _load_all_samples_with_buildings(db, org_id)

    # Group by building
    building_data: dict[UUID, dict] = {}
    for sample, building in rows:
        bid = building.id
        if bid not in building_data:
            building_data[bid] = {
                "building": building,
                "samples_by_pollutant": {},
            }
        pollutant = (sample.pollutant_type or "").lower()
        if pollutant:
            building_data[bid]["samples_by_pollutant"].setdefault(pollutant, []).append(sample)

    total_buildings = await _count_buildings(db, org_id)
    currently_non_compliant = 0
    vulnerable_buildings = []

    for bid, bdata in building_data.items():
        building = bdata["building"]
        closest_margin: float | None = None
        closest_pollutant: str | None = None
        pollutants_near = 0
        is_non_compliant = False

        for pollutant, samples in bdata["samples_by_pollutant"].items():
            entries = SWISS_THRESHOLDS.get(pollutant, {})
            if not entries:
                continue

            max_conc = max(s.concentration for s in samples)

            for _mtype, entry in entries.items():
                threshold = entry["threshold"]
                if threshold <= 0:
                    continue

                margin_pct = (threshold - max_conc) / threshold * 100

                if max_conc >= threshold:
                    is_non_compliant = True

                # Near threshold: within 50% margin
                if margin_pct < 50 and margin_pct >= 0:
                    pollutants_near += 1

                if closest_margin is None or margin_pct < closest_margin:
                    closest_margin = margin_pct
                    closest_pollutant = pollutant

        if is_non_compliant:
            currently_non_compliant += 1

        # Vulnerability score: 0-100 (higher = more vulnerable)
        if closest_margin is None:
            vuln_score = 0.0
        elif closest_margin <= 0:
            vuln_score = 100.0
        else:
            vuln_score = max(0.0, min(100.0, 100.0 - closest_margin))

        vulnerable_buildings.append(
            {
                "building_id": bid,
                "address": building.address,
                "city": building.city,
                "canton": building.canton,
                "closest_margin_percent": (round(closest_margin, 1) if closest_margin is not None else None),
                "closest_margin_pollutant": closest_pollutant,
                "pollutants_near_threshold": pollutants_near,
                "vulnerability_score": round(vuln_score, 1),
            }
        )

    # Sort by vulnerability score descending
    vulnerable_buildings.sort(key=lambda b: b["vulnerability_score"], reverse=True)

    # Risk summary
    risk_buckets = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for vb in vulnerable_buildings:
        score = vb["vulnerability_score"]
        if score >= 80:
            risk_buckets["critical"] += 1
        elif score >= 60:
            risk_buckets["high"] += 1
        elif score >= 40:
            risk_buckets["medium"] += 1
        else:
            risk_buckets["low"] += 1

    return {
        "org_id": org_id,
        "total_buildings": total_buildings,
        "buildings_with_samples": len(building_data),
        "currently_non_compliant": currently_non_compliant,
        "vulnerable_buildings": vulnerable_buildings,
        "risk_summary": risk_buckets,
    }
