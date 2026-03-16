"""
SwissBuildingOS - Remediation Domain Facade

Read-only composition point for remediation-related queries: actions,
interventions, and post-works states for a building. Thin wrapper over
existing models and services -- no new business logic.
"""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.intervention import Intervention
from app.models.post_works_state import PostWorksState

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def get_remediation_summary(
    db: AsyncSession,
    building_id: UUID,
) -> dict | None:
    """Aggregate remediation state for a building.

    Returns None if the building does not exist.

    Returns a dict with:
      - building_id
      - actions (total, open, done, blocked, by_priority)
      - interventions (total, by_status)
      - post_works_states_count
      - has_completed_remediation (bool)
    """
    # ── 0. Verify building exists ─────────────────────────────────
    result = await db.execute(select(Building).where(Building.id == building_id))
    if result.scalar_one_or_none() is None:
        return None

    # ── 1. Action items ───────────────────────────────────────────
    action_result = await db.execute(select(ActionItem).where(ActionItem.building_id == building_id))
    actions = list(action_result.scalars().all())

    actions_total = len(actions)
    actions_open = 0
    actions_done = 0
    actions_blocked = 0
    by_priority: dict[str, int] = defaultdict(int)

    for a in actions:
        status = a.status or "open"
        if status == "open":
            actions_open += 1
        elif status in ("done", "completed"):
            actions_done += 1
        elif status == "blocked":
            actions_blocked += 1
        by_priority[a.priority or "medium"] += 1

    # ── 2. Interventions ──────────────────────────────────────────
    intervention_result = await db.execute(select(Intervention).where(Intervention.building_id == building_id))
    interventions = list(intervention_result.scalars().all())

    interventions_total = len(interventions)
    by_status: dict[str, int] = defaultdict(int)
    has_completed = False

    for i in interventions:
        s = i.status or "planned"
        by_status[s] += 1
        if s == "completed":
            has_completed = True

    # ── 3. Post-works states ──────────────────────────────────────
    pws_count_result = await db.execute(
        select(func.count()).select_from(PostWorksState).where(PostWorksState.building_id == building_id)
    )
    post_works_count = pws_count_result.scalar() or 0

    # has_completed_remediation: at least one completed intervention exists
    # AND at least one post-works state exists (evidence of follow-through)
    has_completed_remediation = has_completed and post_works_count > 0

    return {
        "building_id": str(building_id),
        "actions": {
            "total": actions_total,
            "open": actions_open,
            "done": actions_done,
            "blocked": actions_blocked,
            "by_priority": dict(by_priority),
        },
        "interventions": {
            "total": interventions_total,
            "by_status": dict(by_status),
        },
        "post_works_states_count": post_works_count,
        "has_completed_remediation": has_completed_remediation,
    }
