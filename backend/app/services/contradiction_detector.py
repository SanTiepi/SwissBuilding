"""
SwissBuildingOS - Contradiction Detector Service

Scans building data for contradictions and inconsistencies.
Detected contradictions are stored as DataQualityIssue records
with issue_type = "contradiction".

Contradictions detected:
1. conflicting_sample_results: Two samples in the same location with contradicting results
2. inconsistent_risk_levels: Sample risk_level doesn't match the threshold_exceeded flag
3. pollutant_type_discrepancy: Same material_category with conflicting pollutant findings
4. duplicate_samples: Samples with same location and pollutant in different diagnostics
5. construction_year_conflict: Building construction_year doesn't match diagnostic metadata

All detections are idempotent -- same contradictions are not re-flagged.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.building import Building
from app.models.data_quality_issue import DataQualityIssue
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample

logger = logging.getLogger(__name__)

DETECTED_BY = "contradiction_detector"
ISSUE_TYPE = "contradiction"


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------


async def _load_building(db: AsyncSession, building_id: UUID) -> Building | None:
    result = await db.execute(select(Building).where(Building.id == building_id))
    return result.scalar_one_or_none()


async def _load_diagnostics(db: AsyncSession, building_id: UUID) -> list[Diagnostic]:
    result = await db.execute(
        select(Diagnostic).options(selectinload(Diagnostic.samples)).where(Diagnostic.building_id == building_id)
    )
    return list(result.scalars().all())


async def _load_all_samples(diagnostics: list[Diagnostic]) -> list[Sample]:
    samples: list[Sample] = []
    for diag in diagnostics:
        samples.extend(diag.samples)
    return samples


async def _load_existing_open(db: AsyncSession, building_id: UUID) -> list[DataQualityIssue]:
    result = await db.execute(
        select(DataQualityIssue).where(
            and_(
                DataQualityIssue.building_id == building_id,
                DataQualityIssue.issue_type == ISSUE_TYPE,
                DataQualityIssue.status == "open",
                DataQualityIssue.detected_by == DETECTED_BY,
            )
        )
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Contradiction detectors
# ---------------------------------------------------------------------------


def _detect_conflicting_sample_results(
    samples: list[Sample],
    diagnostics: list[Diagnostic],
) -> list[dict]:
    """Find samples from the same building where the same location_room + pollutant_type
    combination has one sample with threshold_exceeded=True and another with False."""
    contradictions: list[dict] = []

    # Group samples by (location_room, pollutant_type)
    groups: dict[tuple[str, str], list[Sample]] = defaultdict(list)
    for s in samples:
        if s.location_room and s.pollutant_type:
            groups[(s.location_room, s.pollutant_type)].append(s)

    for (room, pollutant), group in groups.items():
        has_positive = any(s.threshold_exceeded is True for s in group)
        has_negative = any(s.threshold_exceeded is False for s in group)
        if has_positive and has_negative:
            # Use the first positive sample as source entity
            source = next(s for s in group if s.threshold_exceeded is True)
            contradictions.append(
                {
                    "field_name": "conflicting_sample_results",
                    "entity_type": "sample",
                    "entity_id": source.id,
                    "severity": "high",
                    "description": (
                        f"Conflicting results for {pollutant} in '{room}': "
                        f"some samples exceed threshold, others do not."
                    ),
                    "suggestion": (
                        "Review samples for this location and pollutant. Consider re-sampling if results are ambiguous."
                    ),
                }
            )

    return contradictions


def _detect_inconsistent_risk_levels(samples: list[Sample]) -> list[dict]:
    """Find samples where threshold_exceeded doesn't match risk_level."""
    contradictions: list[dict] = []

    for s in samples:
        if s.threshold_exceeded is None or s.risk_level is None:
            continue

        inconsistent = False
        desc = ""
        if s.threshold_exceeded is True and s.risk_level in ("low", "unknown"):
            inconsistent = True
            desc = (
                f"Sample {s.sample_number}: threshold exceeded but risk_level is '{s.risk_level}'. "
                f"Expected 'high' or 'critical'."
            )
        elif s.threshold_exceeded is False and s.risk_level in ("high", "critical"):
            inconsistent = True
            desc = (
                f"Sample {s.sample_number}: threshold not exceeded but risk_level is '{s.risk_level}'. "
                f"Expected 'low' or 'medium'."
            )

        if inconsistent:
            contradictions.append(
                {
                    "field_name": "inconsistent_risk_levels",
                    "entity_type": "sample",
                    "entity_id": s.id,
                    "severity": "medium",
                    "description": desc,
                    "suggestion": "Verify threshold and risk level consistency for this sample.",
                }
            )

    return contradictions


def _detect_pollutant_type_discrepancy(samples: list[Sample]) -> list[dict]:
    """Find samples with the same material_category where one finds pollutant positive
    and another doesn't for the same pollutant type."""
    contradictions: list[dict] = []

    # Group by (material_category, pollutant_type)
    groups: dict[tuple[str, str], list[Sample]] = defaultdict(list)
    for s in samples:
        if s.material_category and s.pollutant_type:
            groups[(s.material_category, s.pollutant_type)].append(s)

    for (material, pollutant), group in groups.items():
        has_positive = any(s.threshold_exceeded is True for s in group)
        has_negative = any(s.threshold_exceeded is False for s in group)
        if has_positive and has_negative:
            source = next(s for s in group if s.threshold_exceeded is True)
            contradictions.append(
                {
                    "field_name": "pollutant_type_discrepancy",
                    "entity_type": "sample",
                    "entity_id": source.id,
                    "severity": "high",
                    "description": (
                        f"Conflicting {pollutant} findings for material '{material}': "
                        f"some samples positive, others negative."
                    ),
                    "suggestion": ("Investigate whether material composition varies or if sampling error occurred."),
                }
            )

    return contradictions


def _detect_duplicate_samples(
    samples: list[Sample],
    diagnostics: list[Diagnostic],
) -> list[dict]:
    """Find samples with the same location_room + pollutant_type + material_category
    across different diagnostics (potential duplicates)."""
    contradictions: list[dict] = []

    # Group by (location_room, pollutant_type, material_category)
    groups: dict[tuple[str, str, str], list[Sample]] = defaultdict(list)
    for s in samples:
        if s.location_room and s.pollutant_type and s.material_category:
            groups[(s.location_room, s.pollutant_type, s.material_category)].append(s)

    for (room, pollutant, material), group in groups.items():
        # Check if samples come from different diagnostics
        diag_ids = {s.diagnostic_id for s in group}
        if len(diag_ids) < 2:
            continue

        source = group[0]
        diag_count = len(diag_ids)
        contradictions.append(
            {
                "field_name": "duplicate_samples",
                "entity_type": "sample",
                "entity_id": source.id,
                "severity": "low",
                "description": (
                    f"Potential duplicate: {pollutant} in '{room}' ({material}) "
                    f"sampled across {diag_count} different diagnostics."
                ),
                "suggestion": ("Review whether these samples are intentional re-tests or accidental duplicates."),
            }
        )

    return contradictions


def _detect_construction_year_conflict(
    building: Building,
    diagnostics: list[Diagnostic],
) -> list[dict]:
    """Check if building construction_year conflicts with diagnostic metadata."""
    contradictions: list[dict] = []

    if building.construction_year is None:
        return contradictions

    for diag in diagnostics:
        # Check source_metadata_json on building for year conflicts
        # Diagnostic doesn't have metadata_json, but if date_inspection is before
        # construction_year, that's a conflict
        if diag.date_inspection and diag.date_inspection.year < building.construction_year:
            contradictions.append(
                {
                    "field_name": "construction_year_conflict",
                    "entity_type": "diagnostic",
                    "entity_id": diag.id,
                    "severity": "medium",
                    "description": (
                        f"Diagnostic inspection date ({diag.date_inspection}) "
                        f"is before building construction year ({building.construction_year})."
                    ),
                    "suggestion": ("Verify the building's construction year or the diagnostic inspection date."),
                }
            )

    return contradictions


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_DETECTORS = [
    lambda b, s, d: _detect_conflicting_sample_results(s, d),
    lambda b, s, d: _detect_inconsistent_risk_levels(s),
    lambda b, s, d: _detect_pollutant_type_discrepancy(s),
    lambda b, s, d: _detect_duplicate_samples(s, d),
    lambda b, s, d: _detect_construction_year_conflict(b, d),
]


async def detect_contradictions(
    db: AsyncSession,
    building_id: UUID,
) -> list[DataQualityIssue]:
    """Scan building data for contradictions.

    Creates DataQualityIssue records for each detected contradiction.
    Idempotent: same issues are not re-created.
    Auto-resolves: issues that no longer exist are marked as resolved.
    Returns list of newly created issues.
    """
    building = await _load_building(db, building_id)
    if building is None:
        return []

    diagnostics = await _load_diagnostics(db, building_id)
    samples = await _load_all_samples(diagnostics)

    # Load existing open issues for dedup + auto-resolve
    existing_open = await _load_existing_open(db, building_id)

    # Run all detectors
    detected: list[dict] = []
    for detector in _DETECTORS:
        detected.extend(detector(building, samples, diagnostics))

    # Build detected keys for auto-resolve
    detected_keys: set[tuple[str, str | None, str | None]] = set()
    for item in detected:
        detected_keys.add(
            (
                item["field_name"],
                item.get("entity_type"),
                str(item["entity_id"]) if item.get("entity_id") else None,
            )
        )

    # Auto-resolve issues that no longer exist
    for existing in existing_open:
        key = (
            existing.field_name,
            existing.entity_type,
            str(existing.entity_id) if existing.entity_id else None,
        )
        if key not in detected_keys:
            existing.status = "resolved"
            existing.resolved_at = datetime.now(UTC)
            existing.resolution_notes = "Auto-resolved: contradiction no longer detected"

    # Dedup: skip already-existing issues
    existing_keys: set[tuple[str, str | None, str | None]] = set()
    for ex in existing_open:
        existing_keys.add(
            (
                ex.field_name,
                ex.entity_type,
                str(ex.entity_id) if ex.entity_id else None,
            )
        )

    created: list[DataQualityIssue] = []
    for item in detected:
        key = (
            item["field_name"],
            item.get("entity_type"),
            str(item["entity_id"]) if item.get("entity_id") else None,
        )
        if key in existing_keys:
            continue

        issue = DataQualityIssue(
            building_id=building_id,
            issue_type=ISSUE_TYPE,
            severity=item.get("severity", "medium"),
            status="open",
            entity_type=item.get("entity_type"),
            entity_id=item.get("entity_id"),
            field_name=item["field_name"],
            description=item["description"],
            suggestion=item.get("suggestion"),
            detected_by=DETECTED_BY,
        )
        db.add(issue)
        created.append(issue)
        existing_keys.add(key)

    await db.flush()

    logger.info(
        "Detected %d new contradictions for building %s",
        len(created),
        building_id,
    )
    return created


async def get_contradiction_summary(
    db: AsyncSession,
    building_id: UUID,
) -> dict:
    """Return summary of contradictions for a building.

    Returns: {total, by_type, resolved, unresolved}
    """
    result = await db.execute(
        select(DataQualityIssue).where(
            and_(
                DataQualityIssue.building_id == building_id,
                DataQualityIssue.issue_type == ISSUE_TYPE,
                DataQualityIssue.detected_by == DETECTED_BY,
            )
        )
    )
    issues = result.scalars().all()

    by_type: dict[str, int] = {}
    resolved = 0
    unresolved = 0

    for issue in issues:
        field = issue.field_name or "unknown"
        by_type[field] = by_type.get(field, 0) + 1
        if issue.status == "resolved":
            resolved += 1
        else:
            unresolved += 1

    return {
        "total": len(issues),
        "by_type": by_type,
        "resolved": resolved,
        "unresolved": unresolved,
    }
