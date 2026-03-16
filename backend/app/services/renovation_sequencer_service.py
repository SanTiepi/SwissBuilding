"""Renovation Sequencer Service.

Plans optimal renovation sequences considering Swiss pollutant regulations:
- Asbestos removal before any interior renovation (OTConst Art. 60a/82-86)
- PCB removal before facade work (ORRChim Annexe 2.15)
- Lead abatement before occupant-facing finishes (ORRChim Annexe 2.18)
- Radon mitigation timing relative to structural work (ORaP Art. 110)
- Lab analysis buffer (2-4 weeks) between sampling and remediation
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.assignment import Assignment
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.schemas.renovation_sequencer import (
    GanttPhase,
    ParallelTrack,
    ParallelTracksResult,
    PhaseDependency,
    ReadinessBlockersResult,
    RenovationBlocker,
    RenovationPhase,
    RenovationSequence,
    RenovationTimeline,
)

# ---------------------------------------------------------------------------
# Pollutant priority order (highest hazard first)
# ---------------------------------------------------------------------------
_POLLUTANT_PRIORITY = {
    "asbestos": 1,
    "pcb": 2,
    "lead": 3,
    "hap": 4,
    "radon": 5,
}

# Estimated durations (weeks) per pollutant remediation type
_REMEDIATION_DURATIONS: dict[str, int] = {
    "asbestos": 4,
    "pcb": 3,
    "lead": 2,
    "hap": 2,
    "radon": 3,
}

LAB_ANALYSIS_BUFFER_WEEKS = 3  # 2-4 weeks, we use midpoint


def _phase_id(building_id: uuid.UUID, suffix: str) -> str:
    raw = f"{building_id}:{suffix}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


async def _get_building(db: AsyncSession, building_id: uuid.UUID) -> Building | None:
    result = await db.execute(select(Building).where(Building.id == building_id))
    return result.scalar_one_or_none()


async def _get_positive_samples(db: AsyncSession, building_id: uuid.UUID) -> list[Sample]:
    """Get samples with threshold exceeded (positive pollutant findings)."""
    result = await db.execute(
        select(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(
            Diagnostic.building_id == building_id,
            Sample.threshold_exceeded.is_(True),
        )
    )
    return list(result.scalars().all())


async def _get_diagnostics(db: AsyncSession, building_id: uuid.UUID) -> list[Diagnostic]:
    result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    return list(result.scalars().all())


async def _get_open_actions(db: AsyncSession, building_id: uuid.UUID) -> list[ActionItem]:
    result = await db.execute(
        select(ActionItem).where(
            ActionItem.building_id == building_id,
            ActionItem.status.in_(["open", "in_progress"]),
        )
    )
    return list(result.scalars().all())


async def _get_planned_interventions(db: AsyncSession, building_id: uuid.UUID) -> list[Intervention]:
    result = await db.execute(
        select(Intervention).where(
            Intervention.building_id == building_id,
            Intervention.status.in_(["planned", "in_progress"]),
        )
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# FN1: plan_renovation_sequence
# ---------------------------------------------------------------------------


async def plan_renovation_sequence(db: AsyncSession, building_id: uuid.UUID) -> RenovationSequence:
    """Return optimal ordered phases considering pollutant removal priority."""
    building = await _get_building(db, building_id)
    if not building:
        return RenovationSequence(
            building_id=building_id,
            phases=[],
            dependencies=[],
            total_phases=0,
            generated_at=datetime.now(UTC),
        )

    samples = await _get_positive_samples(db, building_id)

    phases: list[RenovationPhase] = []
    dependencies: list[PhaseDependency] = []

    # Group positive samples by pollutant
    pollutants_found: dict[str, list[Sample]] = {}
    for s in samples:
        pt = s.pollutant_type
        if pt:
            pollutants_found.setdefault(pt, []).append(s)

    # Phase 0: Lab analysis / confirmation (if any pollutant found)
    if pollutants_found:
        lab_pid = _phase_id(building_id, "lab-analysis")
        phases.append(
            RenovationPhase(
                phase_id=lab_pid,
                order=0,
                title="Laboratory analysis & confirmation",
                description="Confirm pollutant concentrations before remediation planning.",
                pollutant=None,
                priority="critical",
                estimated_duration_weeks=LAB_ANALYSIS_BUFFER_WEEKS,
                depends_on=[],
                can_parallel=False,
            )
        )

    # Remediation phases sorted by pollutant priority
    sorted_pollutants = sorted(
        pollutants_found.keys(),
        key=lambda p: _POLLUTANT_PRIORITY.get(p, 99),
    )

    order = 1
    prev_phase_id: str | None = _phase_id(building_id, "lab-analysis") if pollutants_found else None

    for pollutant in sorted_pollutants:
        p_samples = pollutants_found[pollutant]
        pid = _phase_id(building_id, f"remediation-{pollutant}")
        deps = [prev_phase_id] if prev_phase_id else []
        zones_desc = ", ".join({s.location_floor or s.location_room or "unknown" for s in p_samples})

        phases.append(
            RenovationPhase(
                phase_id=pid,
                order=order,
                title=f"{pollutant.capitalize()} remediation",
                description=f"Remove {pollutant} from affected zones: {zones_desc}.",
                pollutant=pollutant,
                priority="critical" if pollutant == "asbestos" else "high",
                estimated_duration_weeks=_REMEDIATION_DURATIONS.get(pollutant, 3),
                depends_on=deps,
                can_parallel=False,
            )
        )

        # Add dependency records
        if prev_phase_id:
            dep_reason = _dependency_reason(pollutant, prev_phase_id, building_id)
            dependencies.append(
                PhaseDependency(
                    phase_id=pid,
                    depends_on=prev_phase_id,
                    reason=dep_reason,
                )
            )

        prev_phase_id = pid
        order += 1

    # Structural work phase (after all pollutant remediation)
    structural_pid = _phase_id(building_id, "structural-work")
    structural_deps = [prev_phase_id] if prev_phase_id else []
    phases.append(
        RenovationPhase(
            phase_id=structural_pid,
            order=order,
            title="Structural renovation works",
            description="Core structural modifications after pollutant clearance.",
            pollutant=None,
            priority="medium",
            estimated_duration_weeks=6,
            depends_on=structural_deps,
            can_parallel=False,
        )
    )
    if prev_phase_id:
        dependencies.append(
            PhaseDependency(
                phase_id=structural_pid,
                depends_on=prev_phase_id,
                reason="Structural work must follow all pollutant remediation.",
            )
        )
    order += 1

    # Interior finishing phase
    finishing_pid = _phase_id(building_id, "interior-finishing")
    phases.append(
        RenovationPhase(
            phase_id=finishing_pid,
            order=order,
            title="Interior finishing & restoration",
            description="Final interior works after structural modifications.",
            pollutant=None,
            priority="low",
            estimated_duration_weeks=4,
            depends_on=[structural_pid],
            can_parallel=False,
        )
    )
    dependencies.append(
        PhaseDependency(
            phase_id=finishing_pid,
            depends_on=structural_pid,
            reason="Interior finishing requires completed structural work.",
        )
    )

    return RenovationSequence(
        building_id=building_id,
        phases=phases,
        dependencies=dependencies,
        total_phases=len(phases),
        generated_at=datetime.now(UTC),
    )


def _dependency_reason(pollutant: str, prev_id: str, building_id: uuid.UUID) -> str:
    lab_id = _phase_id(building_id, "lab-analysis")
    if prev_id == lab_id:
        return f"{pollutant.capitalize()} remediation requires confirmed lab results."
    if pollutant == "pcb":
        return "PCB removal must follow asbestos remediation for worker safety."
    if pollutant == "lead":
        return "Lead abatement follows higher-priority pollutant removal."
    if pollutant == "hap":
        return "HAP remediation follows higher-priority pollutant removal."
    if pollutant == "radon":
        return "Radon mitigation is scheduled after solid pollutant removal."
    return f"{pollutant.capitalize()} remediation depends on prior phase completion."


# ---------------------------------------------------------------------------
# FN2: estimate_renovation_timeline
# ---------------------------------------------------------------------------


async def estimate_renovation_timeline(db: AsyncSession, building_id: uuid.UUID) -> RenovationTimeline:
    """Return Gantt-chart-ready timeline with critical path."""
    sequence = await plan_renovation_sequence(db, building_id)

    gantt_phases: list[GanttPhase] = []
    phase_end_map: dict[str, int] = {}

    for phase in sequence.phases:
        # Start after all dependencies complete
        if phase.depends_on:
            start = max(phase_end_map.get(d, 0) for d in phase.depends_on)
        else:
            start = 0

        end = start + phase.estimated_duration_weeks
        phase_end_map[phase.phase_id] = end

        gantt_phases.append(
            GanttPhase(
                phase_id=phase.phase_id,
                title=phase.title,
                start_week=start,
                end_week=end,
                duration_weeks=phase.estimated_duration_weeks,
                depends_on=phase.depends_on,
                is_critical_path=False,  # computed below
                pollutant=phase.pollutant,
            )
        )

    # Compute critical path (longest dependency chain)
    total_duration = max(phase_end_map.values()) if phase_end_map else 0
    critical_ids = _compute_critical_path(gantt_phases, phase_end_map, total_duration)

    for gp in gantt_phases:
        if gp.phase_id in critical_ids:
            gp.is_critical_path = True

    return RenovationTimeline(
        building_id=building_id,
        phases=gantt_phases,
        critical_path=critical_ids,
        total_duration_weeks=total_duration,
        lab_analysis_buffer_weeks=LAB_ANALYSIS_BUFFER_WEEKS,
        generated_at=datetime.now(UTC),
    )


def _compute_critical_path(
    phases: list[GanttPhase],
    end_map: dict[str, int],
    total_duration: int,
) -> list[str]:
    """Identify phases on the critical path (zero float)."""
    if not phases:
        return []

    phase_map = {p.phase_id: p for p in phases}
    critical: list[str] = []

    # Walk backwards from the longest-ending phase
    end_phases = [p for p in phases if end_map.get(p.phase_id, 0) == total_duration]
    visited: set[str] = set()
    stack = [p.phase_id for p in end_phases]

    while stack:
        pid = stack.pop()
        if pid in visited:
            continue
        visited.add(pid)
        critical.append(pid)
        phase = phase_map.get(pid)
        if phase:
            for dep in phase.depends_on:
                stack.append(dep)

    # Return in chronological order
    order = {p.phase_id: p.start_week for p in phases}
    critical.sort(key=lambda x: order.get(x, 0))
    return critical


# ---------------------------------------------------------------------------
# FN3: identify_parallel_tracks
# ---------------------------------------------------------------------------


async def identify_parallel_tracks(db: AsyncSession, building_id: uuid.UUID) -> ParallelTracksResult:
    """Identify works that can run simultaneously."""
    sequence = await plan_renovation_sequence(db, building_id)
    samples = await _get_positive_samples(db, building_id)

    tracks: list[ParallelTrack] = []
    track_num = 0

    # Strategy 1: Independent zones — pollutants in different zones can be parallel
    zone_pollutants: dict[str, list[str]] = {}
    for s in samples:
        zone = s.location_floor or s.location_room or "unknown"
        pt = s.pollutant_type
        if pt:
            zone_pollutants.setdefault(zone, []).append(pt)

    zones_list = list(zone_pollutants.keys())
    if len(zones_list) >= 2:
        # Find zones with non-overlapping pollutants
        for i, z1 in enumerate(zones_list):
            for z2 in zones_list[i + 1 :]:
                p1 = set(zone_pollutants[z1])
                p2 = set(zone_pollutants[z2])
                if not p1 & p2:
                    track_num += 1
                    # Estimate savings: minimum duration of parallel phases
                    dur1 = sum(_REMEDIATION_DURATIONS.get(p, 3) for p in p1)
                    dur2 = sum(_REMEDIATION_DURATIONS.get(p, 3) for p in p2)
                    savings = min(dur1, dur2)

                    phase_ids = []
                    for p in p1:
                        phase_ids.append(_phase_id(building_id, f"remediation-{p}"))
                    for p in p2:
                        phase_ids.append(_phase_id(building_id, f"remediation-{p}"))

                    tracks.append(
                        ParallelTrack(
                            track_id=f"track-{track_num}",
                            phases=phase_ids,
                            reason=f"Zones '{z1}' and '{z2}' have independent pollutants — can remediate simultaneously.",
                            time_savings_weeks=savings,
                        )
                    )

    # Strategy 2: Radon mitigation can run parallel to facade/exterior work
    pollutants_found = {s.pollutant_type for s in samples if s.pollutant_type}
    if "radon" in pollutants_found and len(pollutants_found) > 1:
        exterior_pollutants = pollutants_found & {"pcb", "hap"}
        if exterior_pollutants:
            track_num += 1
            phase_ids = [_phase_id(building_id, "remediation-radon")]
            for ep in exterior_pollutants:
                phase_ids.append(_phase_id(building_id, f"remediation-{ep}"))
            tracks.append(
                ParallelTrack(
                    track_id=f"track-{track_num}",
                    phases=phase_ids,
                    reason="Radon mitigation (basement/ground) can run parallel to exterior pollutant work.",
                    time_savings_weeks=_REMEDIATION_DURATIONS.get("radon", 3),
                )
            )

    # Calculate durations
    sequential = sum(p.estimated_duration_weeks for p in sequence.phases)
    total_savings = sum(t.time_savings_weeks for t in tracks)
    optimized = max(sequential - total_savings, 1)

    return ParallelTracksResult(
        building_id=building_id,
        tracks=tracks,
        total_potential_savings_weeks=total_savings,
        sequential_duration_weeks=sequential,
        optimized_duration_weeks=optimized,
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN4: get_renovation_readiness_blockers
# ---------------------------------------------------------------------------


async def get_renovation_readiness_blockers(db: AsyncSession, building_id: uuid.UUID) -> ReadinessBlockersResult:
    """Identify what prevents renovation from starting."""
    building = await _get_building(db, building_id)
    blockers: list[RenovationBlocker] = []
    blocker_num = 0

    if not building:
        blockers.append(
            RenovationBlocker(
                blocker_id="blk-0",
                category="missing_diagnostic",
                title="Building not found",
                description="The specified building does not exist in the system.",
                severity="critical",
                resolution_path="Verify the building ID and ensure the building is registered.",
            )
        )
        return ReadinessBlockersResult(
            building_id=building_id,
            blockers=blockers,
            total_blockers=1,
            critical_blockers=1,
            is_ready=False,
            generated_at=datetime.now(UTC),
        )

    construction_year = building.construction_year

    # 1. Missing diagnostics
    diagnostics = await _get_diagnostics(db, building_id)
    completed_types = {d.diagnostic_type for d in diagnostics if d.status in ("completed", "validated")}
    draft_types = {d.diagnostic_type for d in diagnostics if d.status == "draft"}

    required_types: list[str] = []
    if construction_year and construction_year < 1991:
        required_types.append("asbestos")
    if construction_year and 1955 <= construction_year <= 1975:
        required_types.append("pcb")
    if construction_year and construction_year < 1980:
        required_types.append("lead")

    for rt in required_types:
        if rt not in completed_types:
            blocker_num += 1
            severity = "critical" if rt == "asbestos" else "high"
            in_draft = rt in draft_types
            desc = (
                f"{rt.capitalize()} diagnostic is in draft status — needs completion."
                if in_draft
                else f"No {rt} diagnostic found for this building (construction year {construction_year})."
            )
            blockers.append(
                RenovationBlocker(
                    blocker_id=f"blk-{blocker_num}",
                    category="missing_diagnostic",
                    title=f"Missing {rt} diagnostic",
                    description=desc,
                    severity=severity,
                    resolution_path=f"Commission a {rt} diagnostic and complete the analysis.",
                    estimated_resolution_weeks=4 if not in_draft else 2,
                )
            )

    # 2. Pending authority approvals (SUVA notification required but not sent)
    for d in diagnostics:
        if d.suva_notification_required and not d.suva_notification_date:
            blocker_num += 1
            blockers.append(
                RenovationBlocker(
                    blocker_id=f"blk-{blocker_num}",
                    category="pending_approval",
                    title=f"SUVA notification pending ({d.diagnostic_type})",
                    description="SUVA notification is required but has not been submitted.",
                    severity="critical",
                    resolution_path="Submit SUVA notification for the diagnostic before starting works.",
                    estimated_resolution_weeks=2,
                )
            )

    # 3. Unresolved compliance actions
    open_actions = await _get_open_actions(db, building_id)
    critical_actions = [a for a in open_actions if a.priority in ("critical", "high")]
    if critical_actions:
        blocker_num += 1
        blockers.append(
            RenovationBlocker(
                blocker_id=f"blk-{blocker_num}",
                category="compliance_gap",
                title=f"{len(critical_actions)} unresolved high-priority action(s)",
                description="Critical or high-priority actions must be resolved before renovation.",
                severity="high",
                resolution_path="Review and resolve open action items in the building dossier.",
                estimated_resolution_weeks=3,
            )
        )

    # 4. Missing contractor assignments
    result = await db.execute(
        select(func.count(Assignment.id)).where(
            Assignment.target_type == "building",
            Assignment.target_id == building_id,
            Assignment.role == "contractor_contact",
        )
    )
    contractor_count = result.scalar_one()
    if contractor_count == 0:
        blocker_num += 1
        blockers.append(
            RenovationBlocker(
                blocker_id=f"blk-{blocker_num}",
                category="missing_contractor",
                title="No contractor assigned",
                description="No contractor contact has been assigned to this building.",
                severity="high",
                resolution_path="Assign a qualified contractor contact to the building.",
                estimated_resolution_weeks=2,
            )
        )

    critical_count = sum(1 for b in blockers if b.severity == "critical")

    return ReadinessBlockersResult(
        building_id=building_id,
        blockers=blockers,
        total_blockers=len(blockers),
        critical_blockers=critical_count,
        is_ready=len(blockers) == 0,
        generated_at=datetime.now(UTC),
    )
