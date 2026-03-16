"""
SwissBuildingOS - Readiness-Driven Action Generator

Converts blocked readiness assessment results into concrete ActionItem tasks.
When a ReadinessAssessment has status "blocked" or "conditional", each failed
check maps to an action that tells the user how to resolve it.

Idempotent: uses (building_id, source_type="readiness", system_key=check_id)
as dedup key to avoid creating duplicate actions for the same blocker.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    ACTION_PRIORITY_CRITICAL,
    ACTION_PRIORITY_HIGH,
    ACTION_PRIORITY_LOW,
    ACTION_PRIORITY_MEDIUM,
    ACTION_SOURCE_READINESS,
    ACTION_STATUS_DONE,
    ACTION_STATUS_OPEN,
    ACTION_TYPE_DOCUMENTATION,
    ACTION_TYPE_INVESTIGATION,
    ACTION_TYPE_NOTIFICATION,
    ACTION_TYPE_PROCUREMENT,
    ACTION_TYPE_REMEDIATION,
)
from app.models.action_item import ActionItem
from app.models.readiness_assessment import ReadinessAssessment

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Check-ID to action mapping
# ---------------------------------------------------------------------------

_CHECK_ACTION_MAP: dict[str, dict[str, str]] = {
    "completed_diagnostic": {
        "action_type": ACTION_TYPE_INVESTIGATION,
        "priority": ACTION_PRIORITY_CRITICAL,
        "title": "Complete pollutant diagnostic",
    },
    "all_pollutants_evaluated": {
        "action_type": ACTION_TYPE_INVESTIGATION,
        "priority": ACTION_PRIORITY_HIGH,
        "title": "Evaluate missing pollutants: {detail}",
    },
    "positive_samples_classified": {
        "action_type": ACTION_TYPE_DOCUMENTATION,
        "priority": ACTION_PRIORITY_HIGH,
        "title": "Classify positive samples (risk + action)",
    },
    "suva_notification": {
        "action_type": ACTION_TYPE_NOTIFICATION,
        "priority": ACTION_PRIORITY_CRITICAL,
        "title": "File SUVA notification for asbestos",
    },
    "cfst_work_category": {
        "action_type": ACTION_TYPE_DOCUMENTATION,
        "priority": ACTION_PRIORITY_HIGH,
        "title": "Determine CFST work category for asbestos",
    },
    "waste_classified": {
        "action_type": ACTION_TYPE_DOCUMENTATION,
        "priority": ACTION_PRIORITY_MEDIUM,
        "title": "Classify waste disposal for positive samples",
    },
    "no_critical_actions": {
        "action_type": ACTION_TYPE_REMEDIATION,
        "priority": ACTION_PRIORITY_CRITICAL,
        "title": "Resolve critical/high priority actions",
    },
    "diagnostic_report": {
        "action_type": ACTION_TYPE_DOCUMENTATION,
        "priority": ACTION_PRIORITY_MEDIUM,
        "title": "Upload diagnostic report",
    },
    "cantonal_form": {
        "action_type": ACTION_TYPE_NOTIFICATION,
        "priority": ACTION_PRIORITY_MEDIUM,
        "title": "Submit cantonal form: {detail}",
    },
    "waste_elimination_plan": {
        "action_type": ACTION_TYPE_DOCUMENTATION,
        "priority": ACTION_PRIORITY_HIGH,
        "title": "Prepare waste elimination plan",
    },
    "cost_estimation": {
        "action_type": ACTION_TYPE_PROCUREMENT,
        "priority": ACTION_PRIORITY_MEDIUM,
        "title": "Create action items for cost scoping",
    },
    "zones_mapped": {
        "action_type": ACTION_TYPE_DOCUMENTATION,
        "priority": ACTION_PRIORITY_LOW,
        "title": "Map building zones for work scoping",
    },
    "interventions_completed": {
        "action_type": ACTION_TYPE_REMEDIATION,
        "priority": ACTION_PRIORITY_HIGH,
        "title": "Complete planned interventions",
    },
    "air_clearance": {
        "action_type": ACTION_TYPE_INVESTIGATION,
        "priority": ACTION_PRIORITY_CRITICAL,
        "title": "Perform air clearance measurements",
    },
    "no_critical_risk": {
        "action_type": ACTION_TYPE_REMEDIATION,
        "priority": ACTION_PRIORITY_CRITICAL,
        "title": "Address critical/high risk samples",
    },
    "post_works_inspection": {
        "action_type": ACTION_TYPE_DOCUMENTATION,
        "priority": ACTION_PRIORITY_MEDIUM,
        "title": "Upload post-works inspection report",
    },
    "diagnostic_age": {
        "action_type": ACTION_TYPE_INVESTIGATION,
        "priority": ACTION_PRIORITY_MEDIUM,
        "title": "Schedule requalification diagnostic",
    },
    "building_modifications": {
        "action_type": ACTION_TYPE_INVESTIGATION,
        "priority": ACTION_PRIORITY_MEDIUM,
        "title": "Assess post-modification diagnostic need",
    },
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def generate_readiness_actions(
    db: AsyncSession,
    building_id: UUID,
    readiness_type: str | None = None,
) -> list[ActionItem]:
    """
    Load ReadinessAssessments for the building, find blocked/conditional checks,
    and create corresponding ActionItems (idempotent).

    If readiness_type is specified, only process that type.
    Otherwise process all assessments for the building.

    Returns list of newly created ActionItem records.
    """
    # 1. Load assessments
    stmt = select(ReadinessAssessment).where(ReadinessAssessment.building_id == building_id)
    if readiness_type is not None:
        stmt = stmt.where(ReadinessAssessment.readiness_type == readiness_type)
    result = await db.execute(stmt)
    assessments = list(result.scalars().all())

    if not assessments:
        return []

    # 2. Load existing readiness-sourced actions for dedup
    existing_keys = await _load_existing_keys(db, building_id)

    # 3. Collect all current failed check_ids across assessments
    current_failed_ids: set[str] = set()
    created: list[ActionItem] = []

    for assessment in assessments:
        if assessment.status not in ("blocked", "conditional"):
            # For ready assessments, all checks pass — auto-resolve only
            _collect_passing_checks(assessment, current_failed_ids)
            continue

        checks = assessment.checks_json or []
        for check in checks:
            check_id = check.get("id")
            if not check_id:
                continue

            status = check.get("status", "")
            if status in ("fail", "conditional"):
                current_failed_ids.add(check_id)
                mapping = _CHECK_ACTION_MAP.get(check_id)
                if mapping is None:
                    continue

                system_key = f"readiness_{check_id}_{building_id}"
                if system_key in existing_keys:
                    continue

                title = _interpolate_title(mapping["title"], check)
                description = _build_description(check)

                action = ActionItem(
                    building_id=building_id,
                    source_type=ACTION_SOURCE_READINESS,
                    action_type=mapping["action_type"],
                    title=title,
                    description=description,
                    priority=mapping["priority"],
                    status=ACTION_STATUS_OPEN,
                    metadata_json={
                        "system_key": system_key,
                        "check_id": check_id,
                        "readiness_type": assessment.readiness_type,
                    },
                )
                db.add(action)
                created.append(action)
                existing_keys.add(system_key)

    # 4. Auto-resolve: mark open readiness actions as done if the check now passes
    await _auto_resolve(db, building_id, current_failed_ids)

    await db.flush()

    logger.info(
        "Generated %d readiness actions for building %s",
        len(created),
        building_id,
    )
    return created


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _collect_passing_checks(assessment: ReadinessAssessment, failed_ids: set[str]) -> None:
    """For ready assessments, we don't add anything to failed_ids — they all pass."""
    # Nothing to add: all checks pass for ready assessments.
    pass


async def _load_existing_keys(db: AsyncSession, building_id: UUID) -> set[str]:
    """Load system_key values from existing readiness-sourced actions."""
    stmt = select(ActionItem).where(
        and_(
            ActionItem.building_id == building_id,
            ActionItem.source_type == ACTION_SOURCE_READINESS,
        )
    )
    result = await db.execute(stmt)
    existing = result.scalars().all()
    keys: set[str] = set()
    for a in existing:
        meta = a.metadata_json or {}
        key = meta.get("system_key")
        if key:
            keys.add(key)
    return keys


async def _auto_resolve(
    db: AsyncSession,
    building_id: UUID,
    current_failed_ids: set[str],
) -> None:
    """Mark open readiness actions as done if their check now passes."""
    stmt = select(ActionItem).where(
        and_(
            ActionItem.building_id == building_id,
            ActionItem.source_type == ACTION_SOURCE_READINESS,
            ActionItem.status == ACTION_STATUS_OPEN,
        )
    )
    result = await db.execute(stmt)
    open_actions = result.scalars().all()

    for action in open_actions:
        meta = action.metadata_json or {}
        check_id = meta.get("check_id")
        if check_id and check_id not in current_failed_ids:
            action.status = ACTION_STATUS_DONE


def _interpolate_title(template: str, check: dict) -> str:
    """Interpolate {detail} placeholder in title with check detail."""
    detail = check.get("detail") or ""
    return template.replace("{detail}", detail)


def _build_description(check: dict) -> str:
    """Build action description from check detail and legal basis."""
    parts: list[str] = []
    detail = check.get("detail")
    if detail:
        parts.append(detail)
    legal_basis = check.get("legal_basis")
    if legal_basis:
        parts.append(f"Legal basis: {legal_basis}")
    return " — ".join(parts) if parts else ""
