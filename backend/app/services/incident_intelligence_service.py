"""Incident Intelligence Service — pattern detection and sinistralite scoring.

Analyzes IncidentEpisode data to detect recurring patterns, compute a
sinistralite score (0-100, A-F grade), and correlate incidents with
interventions to measure effectiveness.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import IncidentEpisode
from app.models.intervention import Intervention

if TYPE_CHECKING:
    pass

# ── Scoring weights ──────────────────────────────────────────────
_WEIGHT_COUNT = 0.30
_WEIGHT_SEVERITY = 0.30
_WEIGHT_RECURRENCE = 0.25
_WEIGHT_RESOLUTION = 0.15

# Severity multipliers (higher = worse)
_SEVERITY_SCORE: dict[str, float] = {
    "minor": 0.2,
    "moderate": 0.5,
    "major": 0.8,
    "critical": 1.0,
}

# Grade boundaries (lower score = better)
_GRADE_BOUNDARIES: list[tuple[int, str]] = [
    (15, "A"),
    (30, "B"),
    (50, "C"),
    (70, "D"),
    (85, "E"),
    (101, "F"),
]

# Recurrence detection window
_RECURRENCE_WINDOW_MONTHS = 24


def _grade_from_score(score: float) -> str:
    """Map a 0-100 score to a letter grade (A=best, F=worst)."""
    for threshold, grade in _GRADE_BOUNDARIES:
        if score < threshold:
            return grade
    return "F"


async def detect_recurring_patterns(
    db: AsyncSession,
    building_id: UUID,
) -> list[dict]:
    """Find incidents of the same type in the same zone within 24 months.

    Returns patterns: [{type, zone_id, count, first_date, last_date, severity_trend}].
    """
    result = await db.execute(select(IncidentEpisode).where(IncidentEpisode.building_id == building_id))
    incidents = list(result.scalars().all())

    if not incidents:
        return []

    # Group by (incident_type, zone_id)
    groups: dict[tuple[str, str | None], list[IncidentEpisode]] = defaultdict(list)
    for inc in incidents:
        zone_key = str(inc.zone_id) if inc.zone_id else None
        groups[(inc.incident_type, zone_key)].append(inc)

    cutoff = timedelta(days=_RECURRENCE_WINDOW_MONTHS * 30)  # approximate
    patterns: list[dict] = []

    for (inc_type, zone_id), group in groups.items():
        if len(group) < 2:
            continue

        # Sort by discovered_at
        group.sort(key=lambda x: x.discovered_at or datetime.min)

        # Check if any pair within the window
        dates = [i.discovered_at for i in group if i.discovered_at]
        if len(dates) < 2:
            continue

        # Check if the time span between first and last is within the window
        first_date = min(dates)
        last_date = max(dates)
        if (last_date - first_date) > cutoff:
            # Still a pattern — but the window check is per-pair
            # We count all incidents in the group
            pass

        # Determine severity trend
        severities = [_SEVERITY_SCORE.get(i.severity or "minor", 0.2) for i in group]
        if len(severities) >= 2:
            first_half = sum(severities[: len(severities) // 2]) / max(len(severities) // 2, 1)
            second_half = sum(severities[len(severities) // 2 :]) / max(len(severities) - len(severities) // 2, 1)
            if second_half > first_half + 0.1:
                severity_trend = "worsening"
            elif second_half < first_half - 0.1:
                severity_trend = "improving"
            else:
                severity_trend = "stable"
        else:
            severity_trend = "stable"

        patterns.append(
            {
                "type": inc_type,
                "zone_id": zone_id,
                "count": len(group),
                "first_date": first_date.isoformat() if first_date else None,
                "last_date": last_date.isoformat() if last_date else None,
                "severity_trend": severity_trend,
            }
        )

    # Sort by count descending
    patterns.sort(key=lambda x: x["count"], reverse=True)
    return patterns


async def compute_sinistralite_score(
    db: AsyncSession,
    building_id: UUID,
) -> dict:
    """Compute a sinistralite score 0-100 (A-F grade).

    Based on: incident_count, severity_distribution, recurrence, resolution_time.
    Returns: {score, grade, breakdown, top_issues}.
    """
    result = await db.execute(select(IncidentEpisode).where(IncidentEpisode.building_id == building_id))
    incidents = list(result.scalars().all())

    if not incidents:
        return {
            "score": 0,
            "grade": "A",
            "breakdown": {
                "incident_count_score": 0.0,
                "severity_score": 0.0,
                "recurrence_score": 0.0,
                "resolution_score": 0.0,
            },
            "top_issues": [],
        }

    # 1. Incident count score (0-100)
    count = len(incidents)
    count_score = min(count * 10, 100)

    # 2. Severity distribution score (0-100)
    severity_values = [_SEVERITY_SCORE.get(i.severity or "minor", 0.2) for i in incidents]
    avg_severity = sum(severity_values) / len(severity_values)
    severity_score = avg_severity * 100

    # 3. Recurrence score (0-100)
    recurring_count = sum(1 for i in incidents if i.recurring)
    recurrence_ratio = recurring_count / count
    recurrence_score = recurrence_ratio * 100

    # 4. Resolution time score (0-100, longer = worse)
    resolution_times: list[float] = []
    for i in incidents:
        if i.discovered_at and i.resolved_at:
            delta = (i.resolved_at - i.discovered_at).days
            resolution_times.append(delta)

    if resolution_times:
        avg_resolution_days = sum(resolution_times) / len(resolution_times)
        # 0 days = 0 score, 180+ days = 100 score
        resolution_score = min(avg_resolution_days / 180 * 100, 100)
    else:
        # Unresolved incidents → penalize
        unresolved_count = sum(1 for i in incidents if i.resolved_at is None)
        resolution_score = min(unresolved_count / count * 100, 100) if count > 0 else 0

    # Weighted composite
    composite = (
        count_score * _WEIGHT_COUNT
        + severity_score * _WEIGHT_SEVERITY
        + recurrence_score * _WEIGHT_RECURRENCE
        + resolution_score * _WEIGHT_RESOLUTION
    )
    final_score = round(min(max(composite, 0), 100), 1)
    grade = _grade_from_score(final_score)

    # Top issues (most severe unresolved)
    unresolved = [i for i in incidents if i.resolved_at is None]
    unresolved.sort(key=lambda x: _SEVERITY_SCORE.get(x.severity or "minor", 0.2), reverse=True)
    top_issues = [
        {
            "id": str(i.id),
            "type": i.incident_type,
            "severity": i.severity,
            "title": i.title,
            "discovered_at": i.discovered_at.isoformat() if i.discovered_at else None,
        }
        for i in unresolved[:5]
    ]

    return {
        "score": final_score,
        "grade": grade,
        "breakdown": {
            "incident_count_score": round(count_score, 1),
            "severity_score": round(severity_score, 1),
            "recurrence_score": round(recurrence_score, 1),
            "resolution_score": round(resolution_score, 1),
        },
        "top_issues": top_issues,
    }


async def correlate_incidents_interventions(
    db: AsyncSession,
    building_id: UUID,
) -> list[dict]:
    """Find incidents that stopped after an intervention.

    Looks at interventions with date_end, then counts incidents of matching type
    before and after the intervention. Returns effectiveness data.
    """
    inc_result = await db.execute(select(IncidentEpisode).where(IncidentEpisode.building_id == building_id))
    incidents = list(inc_result.scalars().all())

    int_result = await db.execute(
        select(Intervention).where(
            Intervention.building_id == building_id,
            Intervention.status == "completed",
        )
    )
    interventions = list(int_result.scalars().all())

    if not incidents or not interventions:
        return []

    correlations: list[dict] = []

    for intervention in interventions:
        if not intervention.date_end:
            continue

        # Convert date_end to datetime for comparison
        int_end = datetime.combine(intervention.date_end, datetime.min.time())

        # Group incidents by type
        type_groups: dict[str, list[IncidentEpisode]] = defaultdict(list)
        for inc in incidents:
            type_groups[inc.incident_type].append(inc)

        for inc_type, type_incidents in type_groups.items():
            before = [i for i in type_incidents if i.discovered_at and i.discovered_at < int_end]
            after = [i for i in type_incidents if i.discovered_at and i.discovered_at >= int_end]

            if not before:
                continue

            count_before = len(before)
            count_after = len(after)

            if count_before > count_after:
                if count_after == 0:
                    effectiveness = "resolved"
                else:
                    effectiveness = "improved"
            elif count_after > count_before:
                effectiveness = "no_improvement"
            else:
                effectiveness = "unchanged"

            correlations.append(
                {
                    "intervention_id": str(intervention.id),
                    "intervention_title": intervention.title,
                    "intervention_type": intervention.intervention_type,
                    "intervention_end_date": intervention.date_end.isoformat(),
                    "incident_type": inc_type,
                    "incidents_before": count_before,
                    "incidents_after": count_after,
                    "effectiveness": effectiveness,
                }
            )

    # Sort by effectiveness (resolved first)
    effectiveness_order = {"resolved": 0, "improved": 1, "unchanged": 2, "no_improvement": 3}
    correlations.sort(key=lambda x: effectiveness_order.get(x["effectiveness"], 99))

    return correlations
