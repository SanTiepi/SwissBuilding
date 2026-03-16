"""
SwissBuildingOS - Unknown Issue Generator Service

Automatic detection of data gaps in building records.
Generates UnknownIssue records for missing diagnostics, pollutant evaluations,
uninspected zones, unconfirmed materials, missing plans, undocumented
interventions, and missing lab results.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.material import Material
from app.models.sample import Sample
from app.models.technical_plan import TechnicalPlan
from app.models.unknown_issue import UnknownIssue
from app.models.zone import Zone

logger = logging.getLogger(__name__)

DETECTED_BY = "unknown_generator"

# ---------------------------------------------------------------------------
# Pollutant applicability by construction year
# ---------------------------------------------------------------------------

_POLLUTANT_YEAR_RULES: dict[str, tuple[int | None, int | None]] = {
    "asbestos": (None, 1990),  # pre-1990
    "pcb": (1955, 1975),  # 1955-1975
    "lead": (None, 2006),  # pre-2006
    "hap": (None, None),  # always
    "radon": (None, None),  # always
}


def _pollutant_applicable(pollutant: str, construction_year: int | None) -> bool:
    """Check if a pollutant evaluation is applicable given the construction year."""
    if construction_year is None:
        return True  # unknown year → assume applicable
    year_from, year_to = _POLLUTANT_YEAR_RULES.get(pollutant, (None, None))
    if year_from is not None and construction_year < year_from:
        return False
    return not (year_to is not None and construction_year > year_to)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def generate_unknowns(
    db: AsyncSession,
    building_id: UUID,
) -> list[UnknownIssue]:
    """Detect data gaps and generate UnknownIssue records for a building.

    Idempotent: skips duplicates and auto-resolves issues that no longer apply.
    Returns list of newly created UnknownIssue records.
    """
    # Load building
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        return []

    # Load related data
    diagnostics = await _load_diagnostics(db, building_id)
    samples = await _load_samples(db, diagnostics)
    zones = await _load_zones(db, building_id)
    materials = await _load_materials(db, zones)
    plans = await _load_plans(db, building_id)
    interventions = await _load_interventions(db, building_id)
    documents = await _load_documents(db, building_id)

    # Load existing open unknowns for dedup + auto-resolve
    existing_open = await _load_existing_open(db, building_id)

    # Detect all current gaps
    detected: list[dict] = []
    detected.extend(_detect_missing_diagnostic(building, diagnostics))
    detected.extend(_detect_missing_pollutant_evaluation(building, samples))
    detected.extend(_detect_uninspected_zones(zones))
    detected.extend(_detect_unconfirmed_materials(materials))
    detected.extend(_detect_missing_plan(building_id, zones, plans))
    detected.extend(_detect_undocumented_interventions(interventions, documents))
    detected.extend(_detect_missing_lab_results(samples))

    # Build a set of detected keys for auto-resolve
    detected_keys: set[tuple[str, str | None, str | None]] = set()
    for gap in detected:
        detected_keys.add(
            (
                gap["unknown_type"],
                gap.get("entity_type"),
                str(gap["entity_id"]) if gap.get("entity_id") else None,
            )
        )

    # Auto-resolve unknowns that are no longer detected
    for existing in existing_open:
        key = (
            existing.unknown_type,
            existing.entity_type,
            str(existing.entity_id) if existing.entity_id else None,
        )
        if key not in detected_keys:
            existing.status = "resolved"
            existing.resolved_at = datetime.now(UTC)
            existing.resolution_notes = "Auto-resolved: gap no longer detected"

    # Create new unknowns (skip duplicates)
    existing_keys: set[tuple[str, str | None, str | None]] = set()
    for ex in existing_open:
        existing_keys.add(
            (
                ex.unknown_type,
                ex.entity_type,
                str(ex.entity_id) if ex.entity_id else None,
            )
        )

    created: list[UnknownIssue] = []
    for gap in detected:
        key = (
            gap["unknown_type"],
            gap.get("entity_type"),
            str(gap["entity_id"]) if gap.get("entity_id") else None,
        )
        if key in existing_keys:
            continue

        issue = UnknownIssue(
            building_id=building_id,
            unknown_type=gap["unknown_type"],
            severity=gap.get("severity", "medium"),
            status="open",
            title=gap["title"],
            description=gap.get("description"),
            entity_type=gap.get("entity_type"),
            entity_id=gap.get("entity_id"),
            blocks_readiness=gap.get("blocks_readiness", False),
            readiness_types_affected=gap.get("readiness_types_affected"),
            detected_by=DETECTED_BY,
        )
        db.add(issue)
        created.append(issue)
        existing_keys.add(key)

    await db.flush()

    logger.info(
        "Generated %d unknowns for building %s",
        len(created),
        building_id,
    )
    return created


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------


async def _load_diagnostics(db: AsyncSession, building_id: UUID) -> list[Diagnostic]:
    result = await db.execute(
        select(Diagnostic).options(selectinload(Diagnostic.samples)).where(Diagnostic.building_id == building_id)
    )
    return list(result.scalars().all())


async def _load_samples(db: AsyncSession, diagnostics: list[Diagnostic]) -> list[Sample]:
    all_samples: list[Sample] = []
    for diag in diagnostics:
        all_samples.extend(diag.samples)
    return all_samples


async def _load_zones(db: AsyncSession, building_id: UUID) -> list[Zone]:
    result = await db.execute(select(Zone).options(selectinload(Zone.elements)).where(Zone.building_id == building_id))
    return list(result.scalars().all())


async def _load_materials(db: AsyncSession, zones: list[Zone]) -> list[Material]:
    element_ids = []
    for z in zones:
        for el in z.elements:
            element_ids.append(el.id)
    if not element_ids:
        return []
    result = await db.execute(select(Material).where(Material.element_id.in_(element_ids)))
    return list(result.scalars().all())


async def _load_plans(db: AsyncSession, building_id: UUID) -> list[TechnicalPlan]:
    result = await db.execute(select(TechnicalPlan).where(TechnicalPlan.building_id == building_id))
    return list(result.scalars().all())


async def _load_interventions(db: AsyncSession, building_id: UUID) -> list[Intervention]:
    result = await db.execute(select(Intervention).where(Intervention.building_id == building_id))
    return list(result.scalars().all())


async def _load_documents(db: AsyncSession, building_id: UUID) -> list[Document]:
    result = await db.execute(select(Document).where(Document.building_id == building_id))
    return list(result.scalars().all())


async def _load_existing_open(db: AsyncSession, building_id: UUID) -> list[UnknownIssue]:
    result = await db.execute(
        select(UnknownIssue).where(
            and_(
                UnknownIssue.building_id == building_id,
                UnknownIssue.status == "open",
                UnknownIssue.detected_by == DETECTED_BY,
            )
        )
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Gap detectors
# ---------------------------------------------------------------------------


def _detect_missing_diagnostic(building: Building, diagnostics: list[Diagnostic]) -> list[dict]:
    """Pre-1991 building with no completed diagnostic."""
    year = building.construction_year
    if year is not None and year > 1991:
        return []
    has_completed = any(d.status in ("completed", "validated") for d in diagnostics)
    if has_completed:
        return []
    return [
        {
            "unknown_type": "missing_diagnostic",
            "severity": "high",
            "blocks_readiness": True,
            "readiness_types_affected": "safe_to_start",
            "title": "Missing pollutant diagnostic",
            "description": (
                f"Building constructed {'before 1991' if year is None else f'in {year}'} "
                "requires a pollutant diagnostic before any renovation work."
            ),
            "entity_type": "building",
            "entity_id": building.id,
        }
    ]


def _detect_missing_pollutant_evaluation(building: Building, samples: list[Sample]) -> list[dict]:
    """For each applicable pollutant, check if samples exist."""
    year = building.construction_year
    sampled_pollutants = {(s.pollutant_type or "").lower() for s in samples if s.pollutant_type}
    gaps: list[dict] = []
    for pollutant in ("asbestos", "pcb", "lead", "hap", "radon"):
        if not _pollutant_applicable(pollutant, year):
            continue
        if pollutant in sampled_pollutants:
            continue
        gaps.append(
            {
                "unknown_type": "missing_pollutant_evaluation",
                "severity": "high",
                "blocks_readiness": True,
                "readiness_types_affected": "safe_to_start",
                "title": f"Missing {pollutant} evaluation",
                "description": (f"No {pollutant} samples found for this building. A pollutant evaluation is required."),
                "entity_type": f"pollutant:{pollutant}",
                "entity_id": building.id,
            }
        )
    return gaps


def _detect_uninspected_zones(zones: list[Zone]) -> list[dict]:
    """Zones with no elements defined."""
    gaps: list[dict] = []
    for zone in zones:
        if not zone.elements:
            gaps.append(
                {
                    "unknown_type": "uninspected_zone",
                    "severity": "medium",
                    "blocks_readiness": False,
                    "title": f"Uninspected zone: {zone.name}",
                    "description": f"Zone '{zone.name}' has no building elements defined.",
                    "entity_type": "zone",
                    "entity_id": zone.id,
                }
            )
    return gaps


def _detect_unconfirmed_materials(materials: list[Material]) -> list[dict]:
    """Materials where contains_pollutant is None."""
    gaps: list[dict] = []
    for mat in materials:
        if mat.contains_pollutant is None:
            gaps.append(
                {
                    "unknown_type": "unconfirmed_material",
                    "severity": "medium",
                    "blocks_readiness": False,
                    "title": f"Unconfirmed material: {mat.name}",
                    "description": (f"Material '{mat.name}' has not been evaluated for pollutant content."),
                    "entity_type": "material",
                    "entity_id": mat.id,
                }
            )
    return gaps


def _detect_missing_plan(
    building_id: UUID,
    zones: list[Zone],
    plans: list[TechnicalPlan],
) -> list[dict]:
    """Building with zones but no floor_plan technical plans."""
    if not zones:
        return []
    has_floor_plan = any(p.plan_type == "floor_plan" for p in plans)
    if has_floor_plan:
        return []
    return [
        {
            "unknown_type": "missing_plan",
            "severity": "low",
            "blocks_readiness": False,
            "title": "Missing floor plan",
            "description": "Building has zones defined but no floor plan uploaded.",
            "entity_type": "building",
            "entity_id": building_id,
        }
    ]


def _detect_undocumented_interventions(
    interventions: list[Intervention],
    documents: list[Document],
) -> list[dict]:
    """Completed interventions with no related documents."""
    completed = [i for i in interventions if i.status == "completed"]
    if not completed:
        return []
    if documents:
        return []
    gaps: list[dict] = []
    for intervention in completed:
        gaps.append(
            {
                "unknown_type": "undocumented_intervention",
                "severity": "medium",
                "blocks_readiness": False,
                "title": f"Undocumented intervention: {intervention.title}",
                "description": (f"Completed intervention '{intervention.title}' has no associated documents."),
                "entity_type": "intervention",
                "entity_id": intervention.id,
            }
        )
    return gaps


def _detect_missing_lab_results(samples: list[Sample]) -> list[dict]:
    """Samples missing concentration or unit."""
    gaps: list[dict] = []
    for sample in samples:
        if sample.concentration is None or sample.unit is None:
            gaps.append(
                {
                    "unknown_type": "missing_lab_results",
                    "severity": "high",
                    "blocks_readiness": True,
                    "readiness_types_affected": "safe_to_start",
                    "title": f"Missing lab results for sample {sample.sample_number}",
                    "description": (f"Sample '{sample.sample_number}' is missing concentration or unit data."),
                    "entity_type": "sample",
                    "entity_id": sample.id,
                }
            )
    return gaps
