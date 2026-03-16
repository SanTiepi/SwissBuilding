"""
SwissBuildingOS - Action Generator Service

Automatic action generation from diagnostic results.
When a diagnostic transitions to "completed" or "validated", this service
analyses samples, compliance results, and completeness gaps to generate
actionable items.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.constants import (
    ACTION_PRIORITY_CRITICAL,
    ACTION_PRIORITY_HIGH,
    ACTION_PRIORITY_LOW,
    ACTION_PRIORITY_MEDIUM,
    ACTION_SOURCE_DIAGNOSTIC,
    ACTION_STATUS_OPEN,
    ACTION_TYPE_DOCUMENTATION,
    ACTION_TYPE_INVESTIGATION,
    ACTION_TYPE_NOTIFICATION,
    ACTION_TYPE_PROCUREMENT,
    ACTION_TYPE_REMEDIATION,
    SAMPLE_UNIT_BQ_PER_M3,
)
from app.models.action_item import ActionItem
from app.models.diagnostic import Diagnostic
from app.services.compliance_engine import (
    check_suva_notification_required,
    determine_cfst_work_category,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pollutant → action mapping
# ---------------------------------------------------------------------------

_POLLUTANT_ACTION_RULES: dict[str, dict] = {
    "asbestos": {
        "title_key": "action.auto.asbestos_remediation",
        "priority": ACTION_PRIORITY_HIGH,
        "action_type": ACTION_TYPE_REMEDIATION,
    },
    "pcb": {
        "title_key": "action.auto.pcb_decontamination",
        "priority": ACTION_PRIORITY_HIGH,
        "action_type": ACTION_TYPE_REMEDIATION,
    },
    "lead": {
        "title_key": "action.auto.lead_assessment",
        "priority": ACTION_PRIORITY_MEDIUM,
        "action_type": ACTION_TYPE_INVESTIGATION,
    },
    "hap": {
        "title_key": "action.auto.hap_remediation",
        "priority": ACTION_PRIORITY_MEDIUM,
        "action_type": ACTION_TYPE_REMEDIATION,
    },
}

# Radon has two tiers with different priorities
_RADON_REFERENCE = 300
_RADON_MANDATORY = 1000


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def generate_actions_from_diagnostic(
    db: AsyncSession,
    building_id: UUID,
    diagnostic_id: UUID,
) -> list[ActionItem]:
    """Generate action items based on diagnostic findings.

    Idempotent: checks existing actions to avoid duplicates.
    Uses source_type="diagnostic" and diagnostic_id for dedup.
    """
    # Load diagnostic with samples
    stmt = select(Diagnostic).options(selectinload(Diagnostic.samples)).where(Diagnostic.id == diagnostic_id)
    result = await db.execute(stmt)
    diagnostic = result.scalar_one_or_none()
    if diagnostic is None:
        return []

    # Only generate for completed/validated diagnostics
    if diagnostic.status not in ("completed", "validated"):
        return []

    # Load existing diagnostic-sourced actions for dedup
    existing_keys = await _load_existing_keys(db, diagnostic_id)

    created: list[ActionItem] = []

    # 1. Sample-based actions
    for sample in diagnostic.samples:
        if not sample.threshold_exceeded:
            continue

        pollutant = (sample.pollutant_type or "").lower()

        # Radon special handling
        if pollutant == "radon" and sample.concentration is not None:
            radon_actions = _build_radon_actions(sample, diagnostic_id, building_id)
            for key, spec in radon_actions.items():
                if key not in existing_keys:
                    action = _create_action_item(spec, building_id, diagnostic_id)
                    db.add(action)
                    created.append(action)
                    existing_keys.add(key)
            continue

        # Standard pollutant actions
        rule = _POLLUTANT_ACTION_RULES.get(pollutant)
        if rule is None:
            continue

        key = f"{pollutant}_remediation_{diagnostic_id}_{sample.id}"
        if key in existing_keys:
            continue

        spec = {
            "title_key": rule["title_key"],
            "priority": rule["priority"],
            "action_type": rule["action_type"],
            "system_key": key,
            "sample_id": sample.id,
            "metadata_json": {
                "system_key": key,
                "pollutant_type": pollutant,
                "sample_id": str(sample.id),
                "concentration": sample.concentration,
                "unit": sample.unit,
                "location": sample.location_detail,
            },
        }
        action = _create_action_item(spec, building_id, diagnostic_id)
        db.add(action)
        created.append(action)
        existing_keys.add(key)

    # 2. Compliance-based actions
    has_positive_asbestos = any(
        s.threshold_exceeded and (s.pollutant_type or "").lower() == "asbestos" for s in diagnostic.samples
    )

    # SUVA notification
    suva_required = check_suva_notification_required(diagnostic.diagnostic_type or "", has_positive_asbestos)
    if suva_required and not diagnostic.suva_notification_date:
        key = f"suva_notification_{diagnostic_id}"
        if key not in existing_keys:
            spec = {
                "title_key": "action.auto.suva_notification",
                "priority": ACTION_PRIORITY_HIGH,
                "action_type": ACTION_TYPE_NOTIFICATION,
                "system_key": key,
                "metadata_json": {
                    "system_key": key,
                    "notification_type": "suva",
                    "diagnostic_type": diagnostic.diagnostic_type,
                },
            }
            action = _create_action_item(spec, building_id, diagnostic_id)
            db.add(action)
            created.append(action)
            existing_keys.add(key)

    # Cantonal authority notification
    if suva_required and not diagnostic.canton_notification_date:
        key = f"authority_notification_{diagnostic_id}"
        if key not in existing_keys:
            spec = {
                "title_key": "action.auto.authority_notification",
                "priority": ACTION_PRIORITY_HIGH,
                "action_type": ACTION_TYPE_NOTIFICATION,
                "system_key": key,
                "metadata_json": {
                    "system_key": key,
                    "notification_type": "cantonal_authority",
                },
            }
            action = _create_action_item(spec, building_id, diagnostic_id)
            db.add(action)
            created.append(action)
            existing_keys.add(key)

    # Major work category → certified contractor
    if has_positive_asbestos:
        for sample in diagnostic.samples:
            if sample.threshold_exceeded and (sample.pollutant_type or "").lower() == "asbestos":
                work_cat = determine_cfst_work_category(
                    sample.material_category or "",
                    sample.material_state or "good",
                    None,
                )
                if work_cat == "major":
                    key = f"certified_contractor_{diagnostic_id}"
                    if key not in existing_keys:
                        spec = {
                            "title_key": "action.auto.certified_contractor",
                            "priority": ACTION_PRIORITY_HIGH,
                            "action_type": ACTION_TYPE_PROCUREMENT,
                            "system_key": key,
                            "metadata_json": {
                                "system_key": key,
                                "work_category": "major",
                            },
                        }
                        action = _create_action_item(spec, building_id, diagnostic_id)
                        db.add(action)
                        created.append(action)
                        existing_keys.add(key)
                    break  # Only one certified_contractor action per diagnostic

    # 3. Completeness gaps — missing report
    if not diagnostic.report_file_path:
        key = f"upload_document_{diagnostic_id}"
        if key not in existing_keys:
            spec = {
                "title_key": "action.auto.upload_document",
                "priority": ACTION_PRIORITY_LOW,
                "action_type": ACTION_TYPE_DOCUMENTATION,
                "system_key": key,
                "metadata_json": {
                    "system_key": key,
                    "document_type": "diagnostic_report",
                },
            }
            action = _create_action_item(spec, building_id, diagnostic_id)
            db.add(action)
            created.append(action)
            existing_keys.add(key)

    if created:
        await db.commit()
        for a in created:
            await db.refresh(a)

    logger.info(
        "Generated %d actions from diagnostic %s",
        len(created),
        diagnostic_id,
    )
    return created


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _load_existing_keys(db: AsyncSession, diagnostic_id: UUID) -> set[str]:
    """Load system_key values from existing diagnostic-sourced actions."""
    stmt = select(ActionItem).where(
        and_(
            ActionItem.source_type == ACTION_SOURCE_DIAGNOSTIC,
            ActionItem.diagnostic_id == diagnostic_id,
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


def _create_action_item(
    spec: dict,
    building_id: UUID,
    diagnostic_id: UUID,
) -> ActionItem:
    """Build an ActionItem from a spec dict."""
    return ActionItem(
        building_id=building_id,
        diagnostic_id=diagnostic_id,
        sample_id=spec.get("sample_id"),
        source_type=ACTION_SOURCE_DIAGNOSTIC,
        action_type=spec["action_type"],
        title=spec["title_key"],
        priority=spec["priority"],
        status=ACTION_STATUS_OPEN,
        metadata_json=spec.get("metadata_json", {"system_key": spec.get("system_key")}),
    )


def _build_radon_actions(
    sample,
    diagnostic_id: UUID,
    building_id: UUID,
) -> dict[str, dict]:
    """Build radon-specific action specs based on concentration thresholds."""
    actions: dict[str, dict] = {}
    concentration = sample.concentration or 0

    if concentration >= _RADON_MANDATORY:
        key = f"radon_urgent_{diagnostic_id}_{sample.id}"
        actions[key] = {
            "title_key": "action.auto.radon_urgent",
            "priority": ACTION_PRIORITY_CRITICAL,
            "action_type": ACTION_TYPE_REMEDIATION,
            "system_key": key,
            "sample_id": sample.id,
            "metadata_json": {
                "system_key": key,
                "pollutant_type": "radon",
                "sample_id": str(sample.id),
                "concentration": concentration,
                "unit": SAMPLE_UNIT_BQ_PER_M3,
                "threshold": _RADON_MANDATORY,
            },
        }
    elif concentration >= _RADON_REFERENCE:
        key = f"radon_mitigation_{diagnostic_id}_{sample.id}"
        actions[key] = {
            "title_key": "action.auto.radon_mitigation",
            "priority": ACTION_PRIORITY_MEDIUM,
            "action_type": ACTION_TYPE_REMEDIATION,
            "system_key": key,
            "sample_id": sample.id,
            "metadata_json": {
                "system_key": key,
                "pollutant_type": "radon",
                "sample_id": str(sample.id),
                "concentration": concentration,
                "unit": SAMPLE_UNIT_BQ_PER_M3,
                "threshold": _RADON_REFERENCE,
            },
        }

    return actions
