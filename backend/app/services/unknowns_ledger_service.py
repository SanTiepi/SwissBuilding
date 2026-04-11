"""
BatiConnect - Unknowns Ledger Service

Comprehensive detection, tracking, and resolution of building unknowns.
Combines outputs from unknown_generator, completeness_engine,
predictive_readiness, and spatial analysis into a unified ledger.

All scanning is idempotent (dedup by building_id + unknown_type + subject).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.sample import Sample
from app.models.unknowns_ledger import UnknownEntry
from app.models.zone import Zone

logger = logging.getLogger(__name__)

DETECTED_BY_LEDGER = "unknowns_ledger"

# Diagnostic validity in days (Swiss standard)
DIAGNOSTIC_VALIDITY_DAYS = 3 * 365

# Pollutant year rules (from unknown_generator)
_POLLUTANT_YEAR_RULES: dict[str, tuple[int | None, int | None]] = {
    "asbestos": (None, 1990),
    "pcb": (1955, 1975),
    "lead": (None, 2006),
    "hap": (None, None),
    "radon": (None, None),
    "pfas": (None, None),
}


def _pollutant_applicable(pollutant: str, construction_year: int | None) -> bool:
    if construction_year is None:
        return True
    year_from, year_to = _POLLUTANT_YEAR_RULES.get(pollutant, (None, None))
    if year_from is not None and construction_year < year_from:
        return False
    return not (year_to is not None and construction_year > year_to)


# ---------------------------------------------------------------------------
# Dedup key helper
# ---------------------------------------------------------------------------


def _entry_key(entry: UnknownEntry) -> tuple[str, str]:
    return (entry.unknown_type, entry.subject)


def _gap_key(gap: dict) -> tuple[str, str]:
    return (gap["unknown_type"], gap["subject"])


# ---------------------------------------------------------------------------
# Gap detectors
# ---------------------------------------------------------------------------


def _detect_missing_diagnostics(
    building: Building,
    diagnostics: list[Diagnostic],
) -> list[dict]:
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
            "subject": "Diagnostic polluants manquant",
            "description": (
                f"Batiment construit {'avant 1991' if year is None else f'en {year}'} "
                "necessite un diagnostic polluants avant travaux."
            ),
            "severity": "critical",
            "blocks_safe_to_x": ["start"],
            "blocks_pack_types": ["authority"],
            "risk_of_acting": "Travaux sans diagnostic: exposition polluants, responsabilite penale.",
            "estimated_resolution_effort": "partner_required",
            "source_type": "unknown_generator",
        }
    ]


def _detect_expired_diagnostics(
    diagnostics: list[Diagnostic],
) -> list[dict]:
    """Diagnostics older than 3 years."""
    now = datetime.now(UTC)
    gaps: list[dict] = []
    for diag in diagnostics:
        if diag.status not in ("completed", "validated"):
            continue
        report_date = diag.date_report or (diag.created_at.date() if diag.created_at else None)
        if report_date is None:
            continue
        # date_report is a Date, convert now to date for comparison
        age_days = (now.date() if hasattr(now, "date") else now) - report_date
        age_days = age_days.days if hasattr(age_days, "days") else int(age_days)
        if age_days > DIAGNOSTIC_VALIDITY_DAYS:
            gaps.append(
                {
                    "unknown_type": "expired_diagnostic",
                    "subject": f"Diagnostic expire: {diag.diagnostic_type or 'polluants'} ({age_days} jours)",
                    "description": (
                        f"Le diagnostic date de {age_days} jours, "
                        f"au-dela de la validite de {DIAGNOSTIC_VALIDITY_DAYS // 365} ans."
                    ),
                    "severity": "high",
                    "blocks_safe_to_x": ["start"],
                    "blocks_pack_types": ["authority"],
                    "risk_of_acting": "Un diagnostic expire ne garantit plus l'etat reel du batiment.",
                    "estimated_resolution_effort": "partner_required",
                    "source_type": "predictive_readiness",
                }
            )
    return gaps


def _detect_missing_documents(
    documents: list[Document],
    diagnostics: list[Diagnostic],
) -> list[dict]:
    """Missing critical document types."""
    gaps: list[dict] = []
    doc_types = {(d.document_type or "").lower() for d in documents}

    has_completed_diag = any(d.status in ("completed", "validated") for d in diagnostics)
    if has_completed_diag and "diagnostic_report" not in doc_types and "report" not in doc_types:
        gaps.append(
            {
                "unknown_type": "missing_document",
                "subject": "Rapport de diagnostic manquant",
                "description": "Diagnostic complete mais aucun rapport televerse.",
                "severity": "high",
                "blocks_safe_to_x": ["start", "sell"],
                "blocks_pack_types": ["authority", "insurer"],
                "risk_of_acting": "Sans rapport, les conclusions du diagnostic ne sont pas prouvees.",
                "estimated_resolution_effort": "moderate",
                "source_type": "completeness_engine",
            }
        )
    return gaps


def _detect_spatial_gaps(
    zones: list[Zone],
) -> list[dict]:
    """Zones with no elements inspected."""
    gaps: list[dict] = []
    for zone in zones:
        if not zone.elements:
            gaps.append(
                {
                    "unknown_type": "spatial_gap",
                    "subject": f"Zone non inspectee: {zone.name}",
                    "description": f"La zone '{zone.name}' n'a aucun element defini.",
                    "severity": "medium",
                    "blocks_safe_to_x": [],
                    "risk_of_acting": "Des polluants pourraient etre presents dans cette zone non inspectee.",
                    "estimated_resolution_effort": "moderate",
                    "source_type": "unknown_generator",
                    "zone_id": zone.id,
                }
            )
    return gaps


def _detect_scope_gaps(
    building: Building,
    samples: list[Sample],
) -> list[dict]:
    """Missing pollutant evaluations for applicable pollutants."""
    year = building.construction_year
    sampled = {(s.pollutant_type or "").lower() for s in samples if s.pollutant_type}
    gaps: list[dict] = []
    for pollutant in ("asbestos", "pcb", "lead", "hap", "radon", "pfas"):
        if not _pollutant_applicable(pollutant, year):
            continue
        if pollutant in sampled:
            continue
        gaps.append(
            {
                "unknown_type": "scope_gap",
                "subject": f"Evaluation {pollutant} manquante",
                "description": f"Aucun echantillon {pollutant} pour ce batiment.",
                "severity": "high",
                "blocks_safe_to_x": ["start"],
                "blocks_pack_types": ["authority"],
                "risk_of_acting": f"Le {pollutant} pourrait etre present sans evaluation.",
                "estimated_resolution_effort": "partner_required",
                "source_type": "completeness_engine",
            }
        )
    return gaps


def _detect_stale_evidence(
    samples: list[Sample],
) -> list[dict]:
    """Samples missing lab results (concentration or unit)."""
    gaps: list[dict] = []
    for sample in samples:
        if sample.concentration is None or sample.unit is None:
            gaps.append(
                {
                    "unknown_type": "stale_evidence",
                    "subject": f"Resultats labo manquants: echantillon {sample.sample_number}",
                    "description": (f"L'echantillon '{sample.sample_number}' n'a pas de concentration ou d'unite."),
                    "severity": "high",
                    "blocks_safe_to_x": ["start"],
                    "risk_of_acting": "Sans resultats labo, le niveau de risque est inconnu.",
                    "estimated_resolution_effort": "moderate",
                    "source_type": "unknown_generator",
                }
            )
    return gaps


def _detect_coverage_gaps(
    zones: list[Zone],
    samples: list[Sample],
) -> list[dict]:
    """Zones that have elements but no samples linked."""
    # Build set of zone_ids that have at least one sample
    # (samples are linked via diagnostic, not zone directly -- approximate check)
    if not zones:
        return []
    zones_with_elements = [z for z in zones if z.elements]
    if not zones_with_elements or not samples:
        return []
    # If there are zones with elements but zero samples at all, that's a coverage gap
    # (More granular zone-sample linkage would require element->sample join)
    return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def scan_building(
    db: AsyncSession,
    building_id: UUID,
) -> dict:
    """Comprehensive scan for all unknowns on a building.

    Combines multiple detection sources. Creates/updates UnknownEntry records.
    Idempotent: deduplicates by (unknown_type, subject).

    Returns: {total, by_type, by_severity, blocking_safe_to_x, created, resolved}
    """
    # Load building
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        return {
            "total": 0,
            "by_type": {},
            "by_severity": {},
            "blocking_safe_to_x": {},
            "created": 0,
            "resolved": 0,
        }

    # Load related data
    from sqlalchemy.orm import selectinload

    diag_result = await db.execute(
        select(Diagnostic).options(selectinload(Diagnostic.samples)).where(Diagnostic.building_id == building_id)
    )
    diagnostics = list(diag_result.scalars().all())

    samples: list[Sample] = []
    for diag in diagnostics:
        samples.extend(diag.samples)

    zone_result = await db.execute(
        select(Zone).options(selectinload(Zone.elements)).where(Zone.building_id == building_id)
    )
    zones = list(zone_result.scalars().all())

    doc_result = await db.execute(select(Document).where(Document.building_id == building_id))
    documents = list(doc_result.scalars().all())

    # Load existing open entries for dedup + auto-resolve
    existing_result = await db.execute(
        select(UnknownEntry).where(
            and_(
                UnknownEntry.building_id == building_id,
                UnknownEntry.status.in_(["open", "investigating"]),
            )
        )
    )
    existing_open = list(existing_result.scalars().all())

    # Run all detectors
    detected: list[dict] = []
    detected.extend(_detect_missing_diagnostics(building, diagnostics))
    detected.extend(_detect_expired_diagnostics(diagnostics))
    detected.extend(_detect_missing_documents(documents, diagnostics))
    detected.extend(_detect_spatial_gaps(zones))
    detected.extend(_detect_scope_gaps(building, samples))
    detected.extend(_detect_stale_evidence(samples))

    # Build keys for auto-resolve
    detected_keys: set[tuple[str, str]] = {_gap_key(g) for g in detected}

    # Auto-resolve entries that are no longer detected
    resolved_count = 0
    for entry in existing_open:
        if entry.detected_by == DETECTED_BY_LEDGER and _entry_key(entry) not in detected_keys:
            entry.status = "resolved"
            entry.resolved_at = datetime.now(UTC)
            entry.resolution_method = "auto_resolved"
            entry.resolution_note = "Auto-resolved: gap no longer detected"
            resolved_count += 1

    # Dedup: existing keys
    existing_keys: set[tuple[str, str]] = {_entry_key(e) for e in existing_open}

    # Create new entries
    created_count = 0
    for gap in detected:
        key = _gap_key(gap)
        if key in existing_keys:
            continue

        entry = UnknownEntry(
            building_id=building_id,
            unknown_type=gap["unknown_type"],
            subject=gap["subject"],
            description=gap.get("description"),
            severity=gap.get("severity", "medium"),
            blocks_safe_to_x=gap.get("blocks_safe_to_x"),
            blocks_pack_types=gap.get("blocks_pack_types"),
            risk_of_acting=gap.get("risk_of_acting"),
            estimated_resolution_effort=gap.get("estimated_resolution_effort"),
            source_type=gap.get("source_type"),
            detected_by=DETECTED_BY_LEDGER,
            zone_id=gap.get("zone_id"),
            element_id=gap.get("element_id"),
        )
        db.add(entry)
        created_count += 1
        existing_keys.add(key)

    await db.flush()

    # Build result summary
    all_result = await db.execute(
        select(UnknownEntry).where(
            and_(
                UnknownEntry.building_id == building_id,
                UnknownEntry.status.in_(["open", "investigating"]),
            )
        )
    )
    all_open = list(all_result.scalars().all())

    by_type: dict[str, int] = defaultdict(int)
    by_severity: dict[str, int] = defaultdict(int)
    blocking: dict[str, int] = defaultdict(int)
    for e in all_open:
        by_type[e.unknown_type] += 1
        by_severity[e.severity or "medium"] += 1
        for b in e.blocks_safe_to_x or []:
            blocking[b] += 1

    logger.info(
        "Unknowns ledger scan for building %s: %d total, %d created, %d resolved",
        building_id,
        len(all_open),
        created_count,
        resolved_count,
    )

    return {
        "total": len(all_open),
        "by_type": dict(by_type),
        "by_severity": dict(by_severity),
        "blocking_safe_to_x": dict(blocking),
        "created": created_count,
        "resolved": resolved_count,
    }


async def get_ledger(
    db: AsyncSession,
    building_id: UUID,
    status: str | None = "open",
    severity: str | None = None,
    case_id: UUID | None = None,
) -> list[UnknownEntry]:
    """Get the unknowns ledger for a building."""
    query = select(UnknownEntry).where(UnknownEntry.building_id == building_id)
    if status:
        query = query.where(UnknownEntry.status == status)
    if severity:
        query = query.where(UnknownEntry.severity == severity)
    if case_id:
        query = query.where(UnknownEntry.case_id == case_id)
    query = query.order_by(
        # Critical first, then high, etc.
        case(
            (UnknownEntry.severity == "critical", 0),
            (UnknownEntry.severity == "high", 1),
            (UnknownEntry.severity == "medium", 2),
            (UnknownEntry.severity == "low", 3),
            else_=4,
        ),
        UnknownEntry.created_at.desc(),
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def resolve_unknown(
    db: AsyncSession,
    unknown_id: UUID,
    resolved_by_id: UUID,
    method: str,
    note: str | None = None,
) -> UnknownEntry:
    """Mark an unknown as resolved."""
    result = await db.execute(select(UnknownEntry).where(UnknownEntry.id == unknown_id))
    entry = result.scalar_one_or_none()
    if entry is None:
        raise ValueError(f"UnknownEntry {unknown_id} not found")

    entry.status = "resolved"
    entry.resolved_at = datetime.now(UTC)
    entry.resolved_by_id = resolved_by_id
    entry.resolution_method = method
    entry.resolution_note = note
    await db.flush()
    return entry


async def accept_risk(
    db: AsyncSession,
    unknown_id: UUID,
    accepted_by_id: UUID,
    note: str,
) -> UnknownEntry:
    """Accept the risk of an unknown without resolving it. Requires note."""
    if not note or not note.strip():
        raise ValueError("Risk acceptance requires a note")

    result = await db.execute(select(UnknownEntry).where(UnknownEntry.id == unknown_id))
    entry = result.scalar_one_or_none()
    if entry is None:
        raise ValueError(f"UnknownEntry {unknown_id} not found")

    entry.status = "accepted_risk"
    entry.resolved_at = datetime.now(UTC)
    entry.resolved_by_id = accepted_by_id
    entry.resolution_method = "risk_accepted"
    entry.resolution_note = note
    await db.flush()
    return entry


async def get_coverage_map(
    db: AsyncSession,
    building_id: UUID,
) -> dict:
    """Get spatial coverage map: which zones have evidence vs gaps.

    Returns: {covered: [...], gaps: [...], partial: [...]}
    """
    from sqlalchemy.orm import selectinload

    zone_result = await db.execute(
        select(Zone).options(selectinload(Zone.elements)).where(Zone.building_id == building_id)
    )
    zones = list(zone_result.scalars().all())

    # Check if there are open spatial gaps in the ledger for each zone
    gap_result = await db.execute(
        select(UnknownEntry).where(
            and_(
                UnknownEntry.building_id == building_id,
                UnknownEntry.unknown_type == "spatial_gap",
                UnknownEntry.status.in_(["open", "investigating"]),
            )
        )
    )
    gap_entries = list(gap_result.scalars().all())
    gap_zone_ids = {e.zone_id for e in gap_entries if e.zone_id}

    covered: list[dict] = []
    gaps: list[dict] = []
    partial: list[dict] = []

    for zone in zones:
        zone_info = {
            "zone_id": str(zone.id),
            "zone_name": zone.name or str(zone.id),
            "status": "gap",
        }
        if zone.id in gap_zone_ids or not zone.elements:
            zone_info["status"] = "gap"
            gaps.append(zone_info)
        else:
            zone_info["status"] = "covered"
            covered.append(zone_info)

    return {"covered": covered, "gaps": gaps, "partial": partial}


async def get_unknowns_impact(
    db: AsyncSession,
    building_id: UUID,
) -> dict:
    """Get impact summary: what safe-to-x are blocked, what packs are incomplete.

    Consumed by SafeToX and PassportEnvelope.
    """
    entries = await get_ledger(db, building_id, status=None)
    open_entries = [e for e in entries if e.status in ("open", "investigating")]

    blocked_safe_to_x: dict[str, int] = defaultdict(int)
    blocked_pack_types: dict[str, int] = defaultdict(int)
    critical_count = 0

    for e in open_entries:
        if e.severity == "critical":
            critical_count += 1
        for b in e.blocks_safe_to_x or []:
            blocked_safe_to_x[b] += 1
        for p in e.blocks_pack_types or []:
            blocked_pack_types[p] += 1

    # Most urgent: up to 5 critical/high entries
    most_urgent = [e for e in open_entries if e.severity in ("critical", "high")][:5]

    return {
        "total_open": len(open_entries),
        "critical_count": critical_count,
        "blocked_safe_to_x": dict(blocked_safe_to_x),
        "blocked_pack_types": dict(blocked_pack_types),
        "most_urgent": most_urgent,
    }
