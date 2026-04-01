"""
SwissBuildingOS - Recommendation Engine

Unified "Next Steps" engine that synthesizes ALL intelligence sources into
a prioritized, human-readable TODO list per building. Each recommendation
shows: what to do, why, impact, estimated cost range, urgency.

Sources:
  1. Open ActionItems (from action_generator / readiness_action_generator)
  2. Blocked readiness checks (from readiness_reasoner)
  3. Open unknowns (from unknown_generator)
  4. Trust score weak dimensions (from trust_score_calculator)
"""

from __future__ import annotations

import hashlib
import logging
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    ACTION_STATUS_OPEN,
    ACTION_TYPE_DOCUMENTATION,
    ACTION_TYPE_INVESTIGATION,
    ACTION_TYPE_NOTIFICATION,
    ACTION_TYPE_PROCUREMENT,
    ACTION_TYPE_REMEDIATION,
)
from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.readiness_assessment import ReadinessAssessment
from app.models.unknown_issue import UnknownIssue

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Priority mapping: string → numeric (1=critical .. 4=low)
# ---------------------------------------------------------------------------

_PRIORITY_MAP: dict[str, int] = {
    "critical": 1,
    "high": 2,
    "medium": 3,
    "low": 4,
}

# ---------------------------------------------------------------------------
# Action type → recommendation category
# ---------------------------------------------------------------------------

_ACTION_TYPE_TO_CATEGORY: dict[str, str] = {
    ACTION_TYPE_REMEDIATION: "remediation",
    ACTION_TYPE_INVESTIGATION: "investigation",
    ACTION_TYPE_DOCUMENTATION: "documentation",
    ACTION_TYPE_NOTIFICATION: "compliance",
    ACTION_TYPE_PROCUREMENT: "remediation",
}

# ---------------------------------------------------------------------------
# Unknown type → recommendation category
# ---------------------------------------------------------------------------

_UNKNOWN_TYPE_TO_CATEGORY: dict[str, str] = {
    "missing_diagnostic": "investigation",
    "uninspected_zone": "investigation",
    "missing_document": "documentation",
    "missing_sample": "investigation",
    "regulatory_gap": "compliance",
    "missing_intervention": "remediation",
    "missing_lab_result": "investigation",
}

# ---------------------------------------------------------------------------
# Swiss market cost ranges (CHF)
# ---------------------------------------------------------------------------

_COST_RANGES: dict[str, dict] = {
    "asbestos_remediation": {"min": 15000, "max": 80000, "confidence": "market_data"},
    "pcb_remediation": {"min": 20000, "max": 100000, "confidence": "market_data"},
    "lead_remediation": {"min": 10000, "max": 50000, "confidence": "market_data"},
    "hap_remediation": {"min": 10000, "max": 60000, "confidence": "estimated"},
    "radon_mitigation": {"min": 5000, "max": 25000, "confidence": "market_data"},
    "diagnostic": {"min": 2000, "max": 8000, "confidence": "market_data"},
    "documentation": {"min": 500, "max": 2000, "confidence": "estimated"},
    "suva_notification": {"min": 0, "max": 0, "confidence": "fixed"},
    "lab_analysis": {"min": 500, "max": 3000, "confidence": "market_data"},
    "investigation": {"min": 1000, "max": 5000, "confidence": "estimated"},
    "monitoring": {"min": 500, "max": 3000, "confidence": "estimated"},
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stable_id(*parts: str) -> str:
    """Generate a stable short ID from key parts."""
    raw = ":".join(parts)
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _cost_for_action(action: ActionItem) -> dict | None:
    """Determine cost estimate based on action metadata."""
    meta = action.metadata_json or {}
    pollutant = meta.get("pollutant_type", "")
    action_type = action.action_type or ""

    # Pollutant-specific remediation
    key = f"{pollutant}_remediation"
    if key in _COST_RANGES:
        return _COST_RANGES[key]

    # Notification types are free
    if "notification" in action_type.lower() or "suva" in action.title.lower():
        return _COST_RANGES["suva_notification"]

    # Fall back by action type
    type_map = {
        ACTION_TYPE_REMEDIATION: "diagnostic",
        ACTION_TYPE_INVESTIGATION: "investigation",
        ACTION_TYPE_DOCUMENTATION: "documentation",
        ACTION_TYPE_PROCUREMENT: "diagnostic",
    }
    fallback_key = type_map.get(action_type)
    if fallback_key and fallback_key in _COST_RANGES:
        return _COST_RANGES[fallback_key]
    return None


def _cost_for_unknown(unknown: UnknownIssue) -> dict | None:
    """Determine cost estimate for resolving an unknown."""
    utype = unknown.unknown_type or ""
    if "diagnostic" in utype:
        return _COST_RANGES["diagnostic"]
    if "sample" in utype or "lab" in utype:
        return _COST_RANGES["lab_analysis"]
    if "document" in utype:
        return _COST_RANGES["documentation"]
    if "intervention" in utype:
        return _COST_RANGES["investigation"]
    return _COST_RANGES.get("investigation")


def _impact_for_priority(priority_str: str) -> float:
    """Map priority string to an impact score."""
    return {
        "critical": 1.0,
        "high": 0.8,
        "medium": 0.5,
        "low": 0.2,
    }.get(priority_str, 0.3)


def _urgency_for_action(action: ActionItem) -> int | None:
    """Compute urgency in days from action metadata."""
    if action.due_date:
        from datetime import date

        delta = (action.due_date - date.today()).days
        return max(0, delta)
    priority = (action.priority or "medium").lower()
    if priority == "critical":
        return 7
    if priority == "high":
        return 30
    return None


def _sort_key(rec: dict) -> tuple:
    """Sort: priority ASC, impact_score DESC, urgency_days ASC (nulls last)."""
    urgency = rec.get("urgency_days")
    urgency_sort = urgency if urgency is not None else 999999
    return (rec["priority"], -rec["impact_score"], urgency_sort)


def _make_cost_dict(cost_data: dict | None) -> dict | None:
    if cost_data is None:
        return None
    return {
        "min": cost_data["min"],
        "max": cost_data["max"],
        "currency": "CHF",
        "confidence": cost_data.get("confidence", "estimated"),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def generate_recommendations(
    db: AsyncSession,
    building_id: UUID,
    limit: int = 10,
) -> list[dict]:
    """Generate a prioritized list of recommendations for a building.

    Aggregates from 4 sources:
      1. Open ActionItems
      2. Blocked readiness checks
      3. Open unknowns
      4. Trust score weak dimensions

    Returns empty list if building not found.
    """
    # 0. Verify building exists
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        return []

    recommendations: list[dict] = []

    # --- Source 1: Open ActionItems ---
    action_stmt = select(ActionItem).where(
        and_(
            ActionItem.building_id == building_id,
            ActionItem.status == ACTION_STATUS_OPEN,
        )
    )
    action_result = await db.execute(action_stmt)
    open_actions = list(action_result.scalars().all())

    for action in open_actions:
        priority_str = (action.priority or "medium").lower()
        category = _ACTION_TYPE_TO_CATEGORY.get(action.action_type or "", "documentation")
        cost = _make_cost_dict(_cost_for_action(action))

        rec = {
            "id": _stable_id("action", str(action.id)),
            "priority": _PRIORITY_MAP.get(priority_str, 3),
            "category": category,
            "title": action.title or "Resolve open action",
            "description": action.description or action.title or "",
            "why": f"Open action ({action.source_type}) requires attention to maintain building compliance.",
            "impact_score": _impact_for_priority(priority_str),
            "cost_estimate": cost,
            "urgency_days": _urgency_for_action(action),
            "source": "action_generator",
            "related_entity": {
                "entity_type": "action_item",
                "entity_id": str(action.id),
            },
        }
        recommendations.append(rec)

    # --- Source 2: Blocked readiness checks ---
    readiness_stmt = select(ReadinessAssessment).where(
        and_(
            ReadinessAssessment.building_id == building_id,
            ReadinessAssessment.status.in_(["blocked", "conditional"]),
        )
    )
    readiness_result = await db.execute(readiness_stmt)
    blocked_assessments = list(readiness_result.scalars().all())

    seen_check_ids: set[str] = set()
    for assessment in blocked_assessments:
        checks = assessment.checks_json or []
        for check in checks:
            check_id = check.get("id", "")
            status = check.get("status", "")
            if status not in ("fail", "conditional"):
                continue
            if check_id in seen_check_ids:
                continue
            seen_check_ids.add(check_id)

            label = check.get("label", check_id)
            detail = check.get("detail", "")
            legal_basis = check.get("legal_basis", "")

            why_parts = [f"Blocks {assessment.readiness_type} readiness."]
            if legal_basis:
                why_parts.append(f"Legal basis: {legal_basis}")

            rec = {
                "id": _stable_id("readiness", check_id, str(building_id)),
                "priority": 2,  # blocked readiness = high
                "category": "compliance",
                "title": f"Fix: {label}",
                "description": detail or f"Resolve blocked check '{check_id}' to unlock {assessment.readiness_type}.",
                "why": " ".join(why_parts),
                "impact_score": 0.85,
                "cost_estimate": None,
                "urgency_days": 30,
                "source": "readiness_reasoner",
                "related_entity": {
                    "entity_type": "readiness_assessment",
                    "entity_id": str(assessment.id),
                },
            }
            recommendations.append(rec)

    # --- Source 3: Open unknowns ---
    unknown_stmt = select(UnknownIssue).where(
        and_(
            UnknownIssue.building_id == building_id,
            UnknownIssue.status == "open",
        )
    )
    unknown_result = await db.execute(unknown_stmt)
    open_unknowns = list(unknown_result.scalars().all())

    for unknown in open_unknowns:
        severity = (unknown.severity or "medium").lower()
        category = _UNKNOWN_TYPE_TO_CATEGORY.get(unknown.unknown_type or "", "investigation")
        cost = _make_cost_dict(_cost_for_unknown(unknown))

        why = f"Data gap ({unknown.unknown_type}) reduces building intelligence quality."
        if unknown.blocks_readiness:
            why += " This gap blocks readiness assessment."

        rec = {
            "id": _stable_id("unknown", str(unknown.id)),
            "priority": _PRIORITY_MAP.get(severity, 3),
            "category": category,
            "title": unknown.title or "Investigate unknown gap",
            "description": unknown.description or unknown.title or "",
            "why": why,
            "impact_score": _impact_for_priority(severity),
            "cost_estimate": cost,
            "urgency_days": 14 if unknown.blocks_readiness else None,
            "source": "unknown_generator",
            "related_entity": {
                "entity_type": unknown.entity_type or "unknown_issue",
                "entity_id": str(unknown.entity_id) if unknown.entity_id else None,
            },
        }
        recommendations.append(rec)

    # --- Source 4: Trust score weak dimensions ---
    from app.models.building_trust_score_v2 import BuildingTrustScore

    trust_stmt = (
        select(BuildingTrustScore)
        .where(BuildingTrustScore.building_id == building_id)
        .order_by(BuildingTrustScore.assessed_at.desc())
        .limit(1)
    )
    trust_result = await db.execute(trust_stmt)
    trust_obj = trust_result.scalar_one_or_none()

    if trust_obj is not None:
        # Declared data too high
        declared_pct = trust_obj.percent_declared or 0.0
        if declared_pct >= 0.3:
            recommendations.append(
                {
                    "id": _stable_id("trust", "declared", str(building_id)),
                    "priority": 3,
                    "category": "documentation",
                    "title": "Reduce declared-only data",
                    "description": f"{int(declared_pct * 100)}% of data points are declared-only. "
                    "Provide evidence documents or lab results to convert them to proven status.",
                    "why": "Declared-only data has low trust weight (0.3). "
                    "Converting to proven data significantly improves trust score.",
                    "impact_score": min(declared_pct, 1.0),
                    "cost_estimate": _make_cost_dict(_COST_RANGES["documentation"]),
                    "urgency_days": None,
                    "source": "trust_score",
                    "related_entity": {
                        "entity_type": "building",
                        "entity_id": str(building_id),
                    },
                }
            )

        # Obsolete data
        obsolete_pct = trust_obj.percent_obsolete or 0.0
        if obsolete_pct >= 0.1:
            recommendations.append(
                {
                    "id": _stable_id("trust", "obsolete", str(building_id)),
                    "priority": 3,
                    "category": "monitoring",
                    "title": "Update obsolete data",
                    "description": f"{int(obsolete_pct * 100)}% of data points are obsolete (>5 years). "
                    "Schedule updated inspections or diagnostic renewals.",
                    "why": "Obsolete data has minimal trust weight (0.1). "
                    "Fresh data is needed to maintain accurate building intelligence.",
                    "impact_score": min(obsolete_pct * 2, 1.0),
                    "cost_estimate": _make_cost_dict(_COST_RANGES["diagnostic"]),
                    "urgency_days": 90,
                    "source": "trust_score",
                    "related_entity": {
                        "entity_type": "building",
                        "entity_id": str(building_id),
                    },
                }
            )

        # Contradictory data
        contradictory_pct = trust_obj.percent_contradictory or 0.0
        if contradictory_pct >= 0.05:
            recommendations.append(
                {
                    "id": _stable_id("trust", "contradictory", str(building_id)),
                    "priority": 2,
                    "category": "investigation",
                    "title": "Resolve data contradictions",
                    "description": f"{int(contradictory_pct * 100)}% of data points have contradictions. "
                    "Review conflicting evidence and resolve discrepancies.",
                    "why": "Contradictory data has zero trust weight. "
                    "Resolving contradictions immediately improves trust score.",
                    "impact_score": min(contradictory_pct * 5, 1.0),
                    "cost_estimate": _make_cost_dict(_COST_RANGES["investigation"]),
                    "urgency_days": 14,
                    "source": "trust_score",
                    "related_entity": {
                        "entity_type": "building",
                        "entity_id": str(building_id),
                    },
                }
            )

        # Low overall trust
        if trust_obj.overall_score < 0.5:
            recommendations.append(
                {
                    "id": _stable_id("trust", "low_overall", str(building_id)),
                    "priority": 2,
                    "category": "documentation",
                    "title": "Improve overall trust score",
                    "description": f"Trust score is {trust_obj.overall_score:.0%}. "
                    "Upload evidence documents, complete diagnostics, and resolve unknowns "
                    "to raise data reliability.",
                    "why": "A low trust score indicates the building intelligence is unreliable. "
                    "Improving trust is essential for regulatory readiness.",
                    "impact_score": 0.9,
                    "cost_estimate": _make_cost_dict(_COST_RANGES["documentation"]),
                    "urgency_days": 30,
                    "source": "trust_score",
                    "related_entity": {
                        "entity_type": "building",
                        "entity_id": str(building_id),
                    },
                }
            )

    # Sort and limit
    recommendations.sort(key=_sort_key)
    return recommendations[:limit]
