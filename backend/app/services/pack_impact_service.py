"""Pack Impact Service — predicts which evidence packs become stale or invalid
after planned interventions/works."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.evidence_pack import EvidencePack
from app.models.intervention import Intervention
from app.models.zone import Zone
from app.schemas.pack_impact import (
    AffectedPack,
    PackImpactSimulation,
    PackImpactSummary,
    PackImpactType,
)

logger = logging.getLogger(__name__)

# Intervention types that invalidate existing evidence
_INVALIDATING_TYPES = {"demolition", "renovation", "asbestos_removal", "decontamination"}

# Intervention types that degrade existing evidence (incomplete after)
_DEGRADING_TYPES = {"construction", "modification", "repair", "installation"}

# Intervention types that improve evidence quality
_IMPROVING_TYPES = {"inspection", "diagnostic", "maintenance"}

# Trust degradation penalties
_PENALTY_INVALIDATED = 0.30
_PENALTY_DEGRADED = 0.15


def _compute_risk_level(invalidated: int, degraded: int) -> str:
    """Compute risk level from invalidated + degraded pack counts."""
    total_impacted = invalidated + degraded
    if invalidated >= 3 or total_impacted >= 5:
        return "critical"
    if invalidated >= 2 or total_impacted >= 3:
        return "high"
    if invalidated >= 1 or total_impacted >= 1:
        return "medium"
    return "low"


def _intervention_affects_pack(
    intervention: Intervention,
    pack: EvidencePack,
    zone_ids: set[UUID],
) -> PackImpactType:
    """Determine how an intervention affects a specific evidence pack.

    Uses zones_affected JSON from the intervention to check overlap with
    zones relevant to the building (and thus referenced by packs).
    """
    itype = intervention.intervention_type or ""

    # Check zone overlap between intervention and pack's building zones
    intervention_zone_ids: set[str] = set()
    if intervention.zones_affected:
        if isinstance(intervention.zones_affected, list):
            intervention_zone_ids = {str(z) for z in intervention.zones_affected}
        elif isinstance(intervention.zones_affected, dict):
            # Could be {"zone_ids": [...]}
            for v in intervention.zones_affected.values():
                if isinstance(v, list):
                    intervention_zone_ids.update(str(z) for z in v)

    # Check if the intervention targets zones relevant to this building
    has_zone_overlap = bool(intervention_zone_ids & {str(z) for z in zone_ids}) or not intervention_zone_ids

    if itype in _INVALIDATING_TYPES and has_zone_overlap:
        return PackImpactType.invalidated

    if itype in _DEGRADING_TYPES and has_zone_overlap:
        return PackImpactType.degraded

    if itype in _IMPROVING_TYPES:
        return PackImpactType.improved

    # For unknown types with zone overlap, mark as degraded
    if has_zone_overlap and intervention_zone_ids:
        return PackImpactType.degraded

    return PackImpactType.unaffected


def _build_reason(impact_type: PackImpactType, intervention: Intervention) -> str:
    """Build a human-readable reason for the impact."""
    title = intervention.title or intervention.intervention_type
    if impact_type == PackImpactType.invalidated:
        return f"Pack invalidated by intervention '{title}' — structural changes require full re-assessment"
    if impact_type == PackImpactType.degraded:
        return f"Pack degraded by intervention '{title}' — may be incomplete after works"
    if impact_type == PackImpactType.improved:
        return f"Pack improved by intervention '{title}' — new evidence collected"
    return f"Pack unaffected by intervention '{title}'"


def _build_remediation_actions(
    impact_type: PackImpactType,
    intervention: Intervention,
) -> list[str]:
    """Generate remediation actions for affected packs."""
    actions: list[str] = []
    title = intervention.title or intervention.intervention_type

    if impact_type == PackImpactType.invalidated:
        actions.append(f"Re-run full diagnostic after completion of '{title}'")
        actions.append("Reassemble evidence pack with post-intervention data")
        actions.append("Update compliance artefacts for affected zones")
    elif impact_type == PackImpactType.degraded:
        actions.append(f"Update pack to include new elements from '{title}'")
        actions.append("Review affected sections for completeness")
    elif impact_type == PackImpactType.improved:
        actions.append("Incorporate new evidence into pack")

    return actions


def _build_affected_sections(
    impact_type: PackImpactType,
    intervention: Intervention,
) -> list[str]:
    """Identify which pack sections are affected."""
    sections: list[str] = []
    itype = intervention.intervention_type or ""

    if impact_type in (PackImpactType.invalidated, PackImpactType.degraded):
        sections.append("diagnostic_results")
        if itype in ("demolition", "renovation", "asbestos_removal", "decontamination"):
            sections.append("risk_assessment")
            sections.append("compliance_status")
        if itype in ("construction", "modification", "installation"):
            sections.append("material_inventory")
            sections.append("zone_mapping")

    if impact_type == PackImpactType.improved:
        sections.append("evidence_chain")

    return sections


def _generate_recommendations(
    summary: PackImpactSummary,
    risk_level: str,
) -> list[str]:
    """Generate overall recommendations based on impact analysis."""
    recs: list[str] = []

    if summary.invalidated_count > 0:
        recs.append(
            f"{summary.invalidated_count} pack(s) will be invalidated — "
            "schedule post-intervention diagnostics before submitting to authorities"
        )

    if summary.degraded_count > 0:
        recs.append(
            f"{summary.degraded_count} pack(s) will be degraded — "
            "review and update affected sections after interventions complete"
        )

    if risk_level in ("high", "critical"):
        recs.append("Consider staggering interventions to maintain at least one valid evidence pack")

    if summary.improved_count > 0:
        recs.append(f"{summary.improved_count} pack(s) will be improved — incorporate new evidence promptly")

    if not recs:
        recs.append("No pack impact detected — planned interventions do not affect existing evidence packs")

    return recs


async def simulate_pack_impact(
    db: AsyncSession,
    building_id: UUID,
    intervention_ids: list[UUID] | None = None,
) -> PackImpactSimulation | None:
    """Simulate the impact of planned interventions on evidence packs.

    If intervention_ids is None, all planned (not completed/cancelled)
    interventions for the building are analyzed.
    """
    # Verify building exists
    building_result = await db.execute(select(Building).where(Building.id == building_id))
    building = building_result.scalar_one_or_none()
    if building is None:
        return None

    # Load interventions
    if intervention_ids is not None:
        interv_result = await db.execute(
            select(Intervention).where(
                Intervention.id.in_(intervention_ids),
                Intervention.building_id == building_id,
            )
        )
    else:
        interv_result = await db.execute(
            select(Intervention).where(
                Intervention.building_id == building_id,
                Intervention.status.in_(["planned", "in_progress"]),
            )
        )
    interventions = list(interv_result.scalars().all())

    # Load evidence packs
    packs_result = await db.execute(select(EvidencePack).where(EvidencePack.building_id == building_id))
    packs = list(packs_result.scalars().all())

    # Load zones for zone overlap checks
    zones_result = await db.execute(select(Zone).where(Zone.building_id == building_id))
    zones = list(zones_result.scalars().all())
    zone_ids = {z.id for z in zones}

    # Analyze impact of each intervention on each pack
    affected_packs: list[AffectedPack] = []
    impact_counts = {
        PackImpactType.invalidated: 0,
        PackImpactType.degraded: 0,
        PackImpactType.unaffected: 0,
        PackImpactType.improved: 0,
    }

    for pack in packs:
        # Determine the worst-case impact across all interventions
        worst_impact = PackImpactType.unaffected
        worst_intervention: Intervention | None = None
        all_sections: list[str] = []
        all_remediation: list[str] = []

        for intervention in interventions:
            impact = _intervention_affects_pack(intervention, pack, zone_ids)

            # Track the worst impact (invalidated > degraded > improved > unaffected)
            impact_order = {
                PackImpactType.invalidated: 3,
                PackImpactType.degraded: 2,
                PackImpactType.improved: 1,
                PackImpactType.unaffected: 0,
            }
            if impact_order[impact] > impact_order[worst_impact]:
                worst_impact = impact
                worst_intervention = intervention

            sections = _build_affected_sections(impact, intervention)
            all_sections.extend(s for s in sections if s not in all_sections)

            remediation = _build_remediation_actions(impact, intervention)
            all_remediation.extend(r for r in remediation if r not in all_remediation)

        # Compute projected trust score
        current_trust: float | None = None
        projected_trust: float | None = None

        # Use a heuristic trust score based on pack status
        status_trust = {
            "complete": 0.85,
            "submitted": 0.80,
            "assembling": 0.60,
            "draft": 0.40,
            "expired": 0.20,
        }
        current_trust = status_trust.get(pack.status or "draft", 0.50)

        if worst_impact == PackImpactType.invalidated:
            projected_trust = max(0.0, current_trust - _PENALTY_INVALIDATED)
        elif worst_impact == PackImpactType.degraded:
            projected_trust = max(0.0, current_trust - _PENALTY_DEGRADED)
        elif worst_impact == PackImpactType.improved:
            projected_trust = min(1.0, current_trust + 0.05)
        else:
            projected_trust = current_trust

        reason = (
            _build_reason(worst_impact, worst_intervention)
            if worst_intervention
            else "No interventions affect this pack"
        )

        affected_packs.append(
            AffectedPack(
                pack_id=pack.id,
                pack_type=pack.pack_type,
                impact_type=worst_impact,
                reason=reason,
                affected_sections=all_sections,
                current_trust_score=round(current_trust, 4) if current_trust is not None else None,
                projected_trust_score=round(projected_trust, 4) if projected_trust is not None else None,
                remediation_actions=all_remediation,
            )
        )
        impact_counts[worst_impact] += 1

    summary = PackImpactSummary(
        invalidated_count=impact_counts[PackImpactType.invalidated],
        degraded_count=impact_counts[PackImpactType.degraded],
        unaffected_count=impact_counts[PackImpactType.unaffected],
        improved_count=impact_counts[PackImpactType.improved],
    )

    risk_level = _compute_risk_level(summary.invalidated_count, summary.degraded_count)
    recommendations = _generate_recommendations(summary, risk_level)

    return PackImpactSimulation(
        building_id=building_id,
        simulation_date=datetime.now(UTC),
        interventions_analyzed=len(interventions),
        packs_analyzed=len(packs),
        affected_packs=affected_packs,
        summary=summary,
        risk_level=risk_level,
        recommendations=recommendations,
    )


async def get_stale_packs(
    db: AsyncSession,
    building_id: UUID,
) -> list[AffectedPack]:
    """Identify evidence packs that are already stale.

    A pack is stale if:
    - Its updated_at is older than the most recent completed intervention date, or
    - Referenced zones/elements have been modified since pack creation.
    """
    # Load packs
    packs_result = await db.execute(select(EvidencePack).where(EvidencePack.building_id == building_id))
    packs = list(packs_result.scalars().all())

    if not packs:
        return []

    # Load completed interventions
    interv_result = await db.execute(
        select(Intervention).where(
            Intervention.building_id == building_id,
            Intervention.status == "completed",
        )
    )
    completed_interventions = list(interv_result.scalars().all())

    # Load zones with their updated_at
    zones_result = await db.execute(select(Zone).where(Zone.building_id == building_id))
    zones = list(zones_result.scalars().all())

    # Find most recent intervention completion date
    latest_intervention_date: datetime | None = None
    for interv in completed_interventions:
        interv_date = interv.updated_at or interv.created_at
        if interv_date and (latest_intervention_date is None or interv_date > latest_intervention_date):
            latest_intervention_date = interv_date

    # Find most recent zone modification
    latest_zone_date: datetime | None = None
    for zone in zones:
        zone_date = zone.updated_at or zone.created_at
        if zone_date and (latest_zone_date is None or zone_date > latest_zone_date):
            latest_zone_date = zone_date

    stale_packs: list[AffectedPack] = []
    for pack in packs:
        pack_date = pack.updated_at or pack.created_at
        is_stale = False
        reason_parts: list[str] = []

        # Check against intervention dates
        if latest_intervention_date and pack_date and pack_date < latest_intervention_date:
            is_stale = True
            reason_parts.append("Pack predates completed interventions")

        # Check against zone modification dates
        if latest_zone_date and pack_date and pack_date < latest_zone_date:
            is_stale = True
            reason_parts.append("Zones modified since pack creation")

        if is_stale:
            stale_packs.append(
                AffectedPack(
                    pack_id=pack.id,
                    pack_type=pack.pack_type,
                    impact_type=PackImpactType.degraded,
                    reason=" — ".join(reason_parts),
                    affected_sections=["diagnostic_results", "zone_mapping"],
                    current_trust_score=None,
                    projected_trust_score=None,
                    remediation_actions=[
                        "Review and update pack with latest intervention data",
                        "Verify zone mappings are current",
                    ],
                )
            )

    return stale_packs
