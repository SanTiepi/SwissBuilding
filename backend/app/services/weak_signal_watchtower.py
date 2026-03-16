"""Weak Signal Watchtower service.

Detects pre-blocker drift signals before readiness or trust collapses —
early warning intelligence for building portfolios.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.building_snapshot import BuildingSnapshot
from app.models.change_signal import ChangeSignal
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.unknown_issue import UnknownIssue
from app.models.user import User
from app.schemas.weak_signal import (
    PortfolioWatchReport,
    WatchRule,
    WeakSignal,
    WeakSignalReport,
)

if TYPE_CHECKING:
    from uuid import UUID

# ── Detection rule definitions ──────────────────────────────────────

WATCH_RULES: list[dict[str, Any]] = [
    {
        "rule_id": "trust_erosion",
        "rule_type": "trust_erosion",
        "description": "Trust score below 0.6 and declining vs previous snapshot",
        "threshold": 0.6,
        "enabled": True,
    },
    {
        "rule_id": "completeness_decay",
        "rule_type": "completeness_decay",
        "description": "Completeness score dropped between consecutive snapshots",
        "threshold": None,
        "enabled": True,
    },
    {
        "rule_id": "diagnostic_aging",
        "rule_type": "diagnostic_aging",
        "description": "Diagnostic older than 3 years with no renewal planned",
        "threshold": 3.0,
        "enabled": True,
    },
    {
        "rule_id": "intervention_stall",
        "rule_type": "intervention_stall",
        "description": "Intervention in_progress for more than 90 days",
        "threshold": 90.0,
        "enabled": True,
    },
    {
        "rule_id": "evidence_gap_widening",
        "rule_type": "evidence_gap_widening",
        "description": "Building has more than 3 open unknown issues",
        "threshold": 3.0,
        "enabled": True,
    },
    {
        "rule_id": "grade_risk",
        "rule_type": "grade_risk",
        "description": "Passport grade worse than B with no active improvement intervention",
        "threshold": None,
        "enabled": True,
    },
    {
        "rule_id": "unknown_accumulation",
        "rule_type": "unknown_accumulation",
        "description": "5+ open unknowns with severity high or critical",
        "threshold": 5.0,
        "enabled": True,
    },
]

SEVERITY_ORDER = {"watch": 0, "advisory": 1, "warning": 2}
GRADE_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5}


def _make_signal_id() -> str:
    return f"ws-{uuid.uuid4().hex[:12]}"


def _highest_severity(signals: list[WeakSignal]) -> str:
    if not signals:
        return "watch"
    return max(signals, key=lambda s: SEVERITY_ORDER.get(s.severity, 0)).severity


def _risk_trajectory(signals: list[WeakSignal]) -> str:
    if len(signals) >= 3:
        return "critical_path"
    if len(signals) >= 1:
        return "declining"
    return "stable"


# ── Individual detection rules ──────────────────────────────────────


async def _detect_trust_erosion(db: AsyncSession, building_id: UUID) -> WeakSignal | None:
    """Trust score < 0.6 AND declining vs previous snapshot."""
    result = await db.execute(
        select(BuildingSnapshot)
        .where(BuildingSnapshot.building_id == building_id)
        .order_by(BuildingSnapshot.captured_at.desc())
        .limit(2)
    )
    snapshots = result.scalars().all()
    if len(snapshots) < 2:
        if len(snapshots) == 1 and snapshots[0].overall_trust is not None and snapshots[0].overall_trust < 0.6:
            return WeakSignal(
                signal_id=_make_signal_id(),
                building_id=building_id,
                signal_type="trust_erosion",
                severity="advisory",
                title="Low trust score",
                description=f"Current trust score {snapshots[0].overall_trust:.2f} is below 0.6 threshold.",
                detected_at=datetime.now(UTC),
                confidence=0.7,
                metadata={"current_trust": snapshots[0].overall_trust},
            )
        return None

    latest, previous = snapshots[0], snapshots[1]
    if latest.overall_trust is None:
        return None

    if latest.overall_trust < 0.6 and (previous.overall_trust is None or latest.overall_trust < previous.overall_trust):
        decline = (previous.overall_trust or 0) - latest.overall_trust
        severity = "warning" if latest.overall_trust < 0.4 else "advisory"
        return WeakSignal(
            signal_id=_make_signal_id(),
            building_id=building_id,
            signal_type="trust_erosion",
            severity=severity,
            title="Trust score eroding",
            description=(
                f"Trust score dropped from {previous.overall_trust:.2f} to {latest.overall_trust:.2f} "
                f"(decline: {decline:.2f})."
            ),
            detected_at=datetime.now(UTC),
            confidence=0.85,
            metadata={
                "current_trust": latest.overall_trust,
                "previous_trust": previous.overall_trust,
                "decline": round(decline, 4),
            },
        )
    return None


async def _detect_completeness_decay(db: AsyncSession, building_id: UUID) -> WeakSignal | None:
    """Completeness dropped between consecutive snapshots."""
    result = await db.execute(
        select(BuildingSnapshot)
        .where(BuildingSnapshot.building_id == building_id)
        .order_by(BuildingSnapshot.captured_at.desc())
        .limit(2)
    )
    snapshots = result.scalars().all()
    if len(snapshots) < 2:
        return None

    latest, previous = snapshots[0], snapshots[1]
    if latest.completeness_score is None or previous.completeness_score is None:
        return None

    if latest.completeness_score < previous.completeness_score:
        drop = previous.completeness_score - latest.completeness_score
        severity = "warning" if drop > 0.15 else "advisory" if drop > 0.05 else "watch"
        return WeakSignal(
            signal_id=_make_signal_id(),
            building_id=building_id,
            signal_type="completeness_decay",
            severity=severity,
            title="Completeness score declining",
            description=(
                f"Completeness dropped from {previous.completeness_score:.2f} to "
                f"{latest.completeness_score:.2f} (-{drop:.2f})."
            ),
            detected_at=datetime.now(UTC),
            confidence=0.9,
            metadata={
                "current_completeness": latest.completeness_score,
                "previous_completeness": previous.completeness_score,
                "drop": round(drop, 4),
            },
        )
    return None


async def _detect_diagnostic_aging(db: AsyncSession, building_id: UUID) -> WeakSignal | None:
    """Any diagnostic older than 3 years with no renewal planned."""
    three_years_ago = datetime.now(UTC).date() - timedelta(days=3 * 365)

    result = await db.execute(
        select(Diagnostic).where(
            Diagnostic.building_id == building_id,
            Diagnostic.date_report.isnot(None),
            Diagnostic.date_report < three_years_ago,
        )
    )
    old_diagnostics = result.scalars().all()
    if not old_diagnostics:
        return None

    # Check if there's a planned intervention of type "diagnostic" or a newer diagnostic
    newer_result = await db.execute(
        select(func.count())
        .select_from(Diagnostic)
        .where(
            Diagnostic.building_id == building_id,
            Diagnostic.date_report.isnot(None),
            Diagnostic.date_report >= three_years_ago,
        )
    )
    newer_count = newer_result.scalar() or 0
    if newer_count > 0:
        return None

    oldest = min(old_diagnostics, key=lambda d: d.date_report)
    age_days = (datetime.now(UTC).date() - oldest.date_report).days
    severity = "warning" if age_days > 5 * 365 else "advisory"

    return WeakSignal(
        signal_id=_make_signal_id(),
        building_id=building_id,
        signal_type="diagnostic_aging",
        severity=severity,
        title="Diagnostic report aging",
        description=f"Oldest diagnostic is {age_days // 365} years old with no recent renewal.",
        detected_at=datetime.now(UTC),
        confidence=0.8,
        metadata={"oldest_diagnostic_age_days": age_days, "old_diagnostic_count": len(old_diagnostics)},
    )


async def _detect_intervention_stall(db: AsyncSession, building_id: UUID) -> WeakSignal | None:
    """Intervention in_progress for > 90 days."""
    ninety_days_ago = datetime.now(UTC) - timedelta(days=90)

    result = await db.execute(
        select(Intervention).where(
            Intervention.building_id == building_id,
            Intervention.status == "in_progress",
            Intervention.created_at < ninety_days_ago,
        )
    )
    stalled = result.scalars().all()
    if not stalled:
        return None

    longest = min(stalled, key=lambda i: i.created_at)
    days_stalled = (datetime.now(UTC) - longest.created_at).days
    severity = "warning" if days_stalled > 180 else "advisory"

    return WeakSignal(
        signal_id=_make_signal_id(),
        building_id=building_id,
        signal_type="intervention_stall",
        severity=severity,
        title="Intervention stalled",
        description=f"{len(stalled)} intervention(s) in progress for over 90 days (longest: {days_stalled} days).",
        detected_at=datetime.now(UTC),
        confidence=0.75,
        metadata={"stalled_count": len(stalled), "longest_stall_days": days_stalled},
    )


async def _detect_evidence_gap_widening(db: AsyncSession, building_id: UUID) -> WeakSignal | None:
    """Building has > 3 open unknown issues."""
    result = await db.execute(
        select(func.count())
        .select_from(UnknownIssue)
        .where(
            UnknownIssue.building_id == building_id,
            UnknownIssue.status == "open",
        )
    )
    open_count = result.scalar() or 0
    if open_count <= 3:
        return None

    severity = "warning" if open_count > 6 else "advisory"
    return WeakSignal(
        signal_id=_make_signal_id(),
        building_id=building_id,
        signal_type="evidence_gap_widening",
        severity=severity,
        title="Evidence gaps widening",
        description=f"{open_count} open unknown issues detected (threshold: 3).",
        detected_at=datetime.now(UTC),
        confidence=0.8,
        metadata={"open_unknown_count": open_count},
    )


async def _detect_grade_risk(db: AsyncSession, building_id: UUID) -> WeakSignal | None:
    """Grade worse than B with no active improvement intervention."""
    result = await db.execute(
        select(BuildingSnapshot)
        .where(BuildingSnapshot.building_id == building_id)
        .order_by(BuildingSnapshot.captured_at.desc())
        .limit(1)
    )
    snapshot = result.scalar_one_or_none()
    if not snapshot or not snapshot.passport_grade:
        return None

    grade = snapshot.passport_grade.upper()
    if GRADE_ORDER.get(grade, 0) <= GRADE_ORDER["B"]:
        return None

    # Check for active improvement intervention
    interv_result = await db.execute(
        select(func.count())
        .select_from(Intervention)
        .where(
            Intervention.building_id == building_id,
            Intervention.status.in_(["planned", "in_progress"]),
        )
    )
    active_count = interv_result.scalar() or 0
    if active_count > 0:
        return None

    severity = "warning" if GRADE_ORDER.get(grade, 0) >= GRADE_ORDER.get("D", 3) else "advisory"
    return WeakSignal(
        signal_id=_make_signal_id(),
        building_id=building_id,
        signal_type="grade_risk",
        severity=severity,
        title="Poor passport grade with no improvement plan",
        description=f"Building has grade {grade} with no active intervention to improve it.",
        detected_at=datetime.now(UTC),
        confidence=0.85,
        metadata={"current_grade": grade, "active_interventions": active_count},
    )


async def _detect_unknown_accumulation(db: AsyncSession, building_id: UUID) -> WeakSignal | None:
    """5+ open unknowns with severity high or critical."""
    result = await db.execute(
        select(func.count())
        .select_from(UnknownIssue)
        .where(
            UnknownIssue.building_id == building_id,
            UnknownIssue.status == "open",
            UnknownIssue.severity.in_(["high", "critical"]),
        )
    )
    count = result.scalar() or 0
    if count < 5:
        return None

    severity = "warning" if count >= 8 else "advisory"
    return WeakSignal(
        signal_id=_make_signal_id(),
        building_id=building_id,
        signal_type="unknown_accumulation",
        severity=severity,
        title="High-severity unknowns accumulating",
        description=f"{count} open high/critical unknown issues (threshold: 5).",
        detected_at=datetime.now(UTC),
        confidence=0.9,
        metadata={"high_critical_unknown_count": count},
    )


# ── Detection rule registry ────────────────────────────────────────

_DETECTORS = [
    _detect_trust_erosion,
    _detect_completeness_decay,
    _detect_diagnostic_aging,
    _detect_intervention_stall,
    _detect_evidence_gap_widening,
    _detect_grade_risk,
    _detect_unknown_accumulation,
]


# ── Public API ──────────────────────────────────────────────────────


async def scan_building_weak_signals(db: AsyncSession, building_id: UUID) -> WeakSignalReport:
    """Run all detection rules against a single building."""
    signals: list[WeakSignal] = []
    for detector in _DETECTORS:
        signal = await detector(db, building_id)
        if signal is not None:
            signals.append(signal)

    return WeakSignalReport(
        building_id=building_id,
        signals=signals,
        total_signals=len(signals),
        highest_severity=_highest_severity(signals),
        risk_trajectory=_risk_trajectory(signals),
    )


async def scan_portfolio_weak_signals(
    db: AsyncSession,
    organization_id: UUID | None = None,
    limit: int = 50,
) -> PortfolioWatchReport:
    """Scan all buildings (or filtered by org) and aggregate weak signals."""
    query = select(Building).where(Building.status == "active")

    if organization_id is not None:
        # Filter buildings whose creator belongs to the organization
        query = query.join(User, Building.created_by == User.id).where(User.organization_id == organization_id)

    query = query.limit(limit)
    result = await db.execute(query)
    buildings = result.scalars().all()

    all_signals: list[WeakSignal] = []
    buildings_with_signals = 0
    top_risk: list[dict[str, Any]] = []

    for building in buildings:
        report = await scan_building_weak_signals(db, building.id)
        if report.total_signals > 0:
            buildings_with_signals += 1
            all_signals.extend(report.signals)
            top_risk.append(
                {
                    "building_id": str(building.id),
                    "address": building.address,
                    "signal_count": report.total_signals,
                    "highest_severity": report.highest_severity,
                }
            )

    # Sort top risk buildings by signal count desc
    top_risk.sort(key=lambda b: b["signal_count"], reverse=True)

    signals_by_type: dict[str, int] = {}
    signals_by_severity: dict[str, int] = {}
    for sig in all_signals:
        signals_by_type[sig.signal_type] = signals_by_type.get(sig.signal_type, 0) + 1
        signals_by_severity[sig.severity] = signals_by_severity.get(sig.severity, 0) + 1

    return PortfolioWatchReport(
        total_buildings_scanned=len(buildings),
        buildings_with_signals=buildings_with_signals,
        signals_by_type=signals_by_type,
        signals_by_severity=signals_by_severity,
        top_risk_buildings=top_risk,
        generated_at=datetime.now(UTC),
    )


def get_watch_rules() -> list[WatchRule]:
    """Return the list of active detection rules with their thresholds."""
    return [WatchRule(**rule) for rule in WATCH_RULES]


async def get_buildings_on_critical_path(
    db: AsyncSession,
    organization_id: UUID | None = None,
) -> list[dict[str, Any]]:
    """Return buildings where 3+ weak signals are detected."""
    query = select(Building).where(Building.status == "active")

    if organization_id is not None:
        query = query.join(User, Building.created_by == User.id).where(User.organization_id == organization_id)

    result = await db.execute(query)
    buildings = result.scalars().all()

    critical: list[dict[str, Any]] = []
    for building in buildings:
        report = await scan_building_weak_signals(db, building.id)
        if report.total_signals >= 3:
            critical.append(
                {
                    "building_id": str(building.id),
                    "address": building.address,
                    "signal_count": report.total_signals,
                    "highest_severity": report.highest_severity,
                    "risk_trajectory": report.risk_trajectory,
                    "signals": [s.model_dump() for s in report.signals],
                }
            )

    critical.sort(key=lambda b: b["signal_count"], reverse=True)
    return critical


async def get_signal_history(
    db: AsyncSession,
    building_id: UUID,
    days: int = 90,
) -> list[WeakSignal]:
    """Return weak signals from ChangeSignals detected in the last N days that match weak signal patterns."""
    cutoff = datetime.now(UTC) - timedelta(days=days)

    # Weak signal type patterns that map from ChangeSignal signal_types
    weak_signal_types = {
        "trust_erosion",
        "completeness_decay",
        "diagnostic_aging",
        "intervention_stall",
        "evidence_gap_widening",
        "grade_risk",
        "unknown_accumulation",
        # Also match broader change signal types
        "trust_decline",
        "completeness_drop",
        "grade_change",
    }

    result = await db.execute(
        select(ChangeSignal).where(
            ChangeSignal.building_id == building_id,
            ChangeSignal.detected_at >= cutoff,
        )
    )
    change_signals = result.scalars().all()

    signals: list[WeakSignal] = []
    for cs in change_signals:
        if cs.signal_type not in weak_signal_types:
            continue

        # Map ChangeSignal severity to weak signal severity
        severity_map = {"info": "watch", "low": "watch", "medium": "advisory", "high": "warning", "critical": "warning"}
        mapped_severity = severity_map.get(cs.severity, "watch")

        # Map broader signal types to weak signal types
        type_map = {
            "trust_decline": "trust_erosion",
            "completeness_drop": "completeness_decay",
            "grade_change": "grade_risk",
        }
        signal_type = type_map.get(cs.signal_type, cs.signal_type)

        signals.append(
            WeakSignal(
                signal_id=f"ws-hist-{str(cs.id).replace('-', '')[:12]}",
                building_id=building_id,
                signal_type=signal_type,
                severity=mapped_severity,
                title=cs.title,
                description=cs.description or "",
                detected_at=cs.detected_at,
                confidence=0.7,
                metadata=cs.metadata_json,
            )
        )

    signals.sort(key=lambda s: s.detected_at, reverse=True)
    return signals
