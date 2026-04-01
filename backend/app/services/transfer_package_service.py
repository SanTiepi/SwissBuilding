"""
SwissBuildingOS - Building Memory Transfer Package Service

Bundles a building's complete intelligence state into a portable, auditable
transfer package for handoff, interoperability, and building sale/transfer
scenarios.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import TRANSFER_PACKAGE_SECTIONS, TRANSFER_PACKAGE_VERSION
from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_snapshot import BuildingSnapshot
from app.models.diagnostic import Diagnostic
from app.models.diagnostic_publication import DiagnosticReportPublication
from app.models.document import Document
from app.models.evidence_link import EvidenceLink
from app.models.intervention import Intervention
from app.models.unknown_issue import UnknownIssue
from app.schemas.transfer_package import TransferPackageResponse

logger = logging.getLogger(__name__)


def _should_include(section: str, include_sections: list[str] | None) -> bool:
    """Check whether a section should be included in the package."""
    if include_sections is None:
        return True
    return section in include_sections


_REDACTED_PLACEHOLDER = "[confidentiel]"
_REDACTED_COST_MESSAGE = "[Montants masques a la demande du proprietaire]"

_FINANCIAL_KEYS = frozenset(
    {
        "total_amount_chf",
        "cost",
        "amount",
        "price",
        "amount_chf",
        "total_expenses_chf",
        "total_income_chf",
        "claimed_amount_chf",
        "approved_amount_chf",
        "paid_amount_chf",
        "insured_value_chf",
        "premium_annual_chf",
    }
)


def _redact_dict(data: dict) -> dict:
    """Recursively redact financial fields in a dict."""
    redacted = {}
    for key, value in data.items():
        if key in _FINANCIAL_KEYS:
            redacted[key] = _REDACTED_PLACEHOLDER
        elif isinstance(value, dict):
            redacted[key] = _redact_dict(value)
        elif isinstance(value, list):
            redacted[key] = [_redact_dict(v) if isinstance(v, dict) else v for v in value]
        else:
            redacted[key] = value
    return redacted


async def generate_transfer_package(
    db: AsyncSession,
    building_id: UUID,
    include_sections: list[str] | None = None,
    redact_financials: bool = False,
) -> TransferPackageResponse | None:
    """Generate a transfer package for a building.

    Returns None if the building does not exist.
    If *include_sections* is provided, only those sections are populated.
    """
    # ── 0. Fetch building ─────────────────────────────────────────
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        return None

    generated_at = datetime.now(UTC)
    package_id = uuid4()

    # ── Building summary (always included) ────────────────────────
    building_summary = {
        "address": building.address,
        "postal_code": building.postal_code,
        "city": building.city,
        "canton": building.canton,
        "egid": building.egid,
        "egrid": building.egrid,
        "construction_year": building.construction_year,
        "building_type": building.building_type,
        "source_dataset": building.source_dataset,
        "latitude": building.latitude,
        "longitude": building.longitude,
    }

    # ── Passport ──────────────────────────────────────────────────
    passport: dict | None = None
    if _should_include("passport", include_sections):
        try:
            from app.services.passport_service import get_passport_summary

            passport = await get_passport_summary(db, building_id)
        except Exception as e:
            logger.warning(f"Failed to get passport summary for building {building_id}: {e}")

    # ── Diagnostics summary ───────────────────────────────────────
    diagnostics_summary: dict | None = None
    if _should_include("diagnostics", include_sections):
        diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
        diagnostics = list(diag_result.scalars().all())

        status_counts: dict[str, int] = defaultdict(int)
        pollutants_found: set[str] = set()
        risk_levels: set[str] = set()
        for d in diagnostics:
            status_counts[d.status or "unknown"] += 1
            if d.diagnostic_type:
                pollutants_found.add(d.diagnostic_type)

        diagnostics_summary = {
            "count": len(diagnostics),
            "statuses": dict(status_counts),
            "pollutants_found": sorted(pollutants_found),
            "risk_levels": sorted(risk_levels),
        }

    # ── Documents summary ─────────────────────────────────────────
    documents_summary: dict | None = None
    if _should_include("documents", include_sections):
        doc_result = await db.execute(select(Document).where(Document.building_id == building_id))
        documents = list(doc_result.scalars().all())

        by_type: dict[str, int] = defaultdict(int)
        total_size = 0
        for doc in documents:
            by_type[doc.document_type or "other"] += 1
            total_size += doc.file_size_bytes or 0

        documents_summary = {
            "count": len(documents),
            "by_type": dict(by_type),
            "total_size_bytes": total_size,
        }

    # ── Interventions summary ─────────────────────────────────────
    interventions_summary: dict | None = None
    if _should_include("interventions", include_sections):
        interv_result = await db.execute(select(Intervention).where(Intervention.building_id == building_id))
        interventions = list(interv_result.scalars().all())

        by_status: dict[str, int] = defaultdict(int)
        types_set: set[str] = set()
        for iv in interventions:
            by_status[iv.status or "unknown"] += 1
            if iv.intervention_type:
                types_set.add(iv.intervention_type)

        interventions_summary = {
            "count": len(interventions),
            "by_status": dict(by_status),
            "types": sorted(types_set),
        }

    # ── Actions summary ───────────────────────────────────────────
    actions_summary: dict | None = None
    if _should_include("actions", include_sections):
        action_result = await db.execute(select(ActionItem).where(ActionItem.building_id == building_id))
        actions = list(action_result.scalars().all())

        by_priority: dict[str, int] = defaultdict(int)
        open_count = 0
        done_count = 0
        for a in actions:
            by_priority[a.priority or "medium"] += 1
            if a.status == "open":
                open_count += 1
            elif a.status == "done":
                done_count += 1

        actions_summary = {
            "total": len(actions),
            "open": open_count,
            "done": done_count,
            "by_priority": dict(by_priority),
        }

    # ── Evidence coverage ─────────────────────────────────────────
    evidence_coverage: dict | None = None
    if _should_include("evidence", include_sections):
        # Count evidence links related to this building's diagnostic entities
        diag_ids_result = await db.execute(select(Diagnostic.id).where(Diagnostic.building_id == building_id))
        diag_ids = [r[0] for r in diag_ids_result.fetchall()]

        total_evidence = 0
        if diag_ids:
            ev_result = await db.execute(
                select(func.count()).select_from(EvidenceLink).where(EvidenceLink.source_id.in_(diag_ids))
            )
            total_evidence = ev_result.scalar() or 0

        # Coverage ratio: evidence links / diagnostics
        diag_count = len(diag_ids)
        coverage_ratio = round(total_evidence / max(diag_count, 1), 2)

        evidence_coverage = {
            "linked_evidence_count": total_evidence,
            "coverage_ratio": coverage_ratio,
        }

    # ── Contradictions ────────────────────────────────────────────
    contradictions: dict | None = None
    if _should_include("contradictions", include_sections):
        try:
            from app.services.contradiction_detector import get_contradiction_summary

            contradictions = await get_contradiction_summary(db, building_id)
        except Exception as e:
            logger.warning(f"Failed to get contradiction summary for building {building_id}: {e}")

    # ── Unknowns ──────────────────────────────────────────────────
    unknowns: dict | None = None
    if _should_include("unknowns", include_sections):
        unknown_result = await db.execute(
            select(UnknownIssue).where(
                and_(
                    UnknownIssue.building_id == building_id,
                    UnknownIssue.status == "open",
                )
            )
        )
        open_unknowns = list(unknown_result.scalars().all())

        by_category: dict[str, int] = defaultdict(int)
        for u in open_unknowns:
            by_category[u.unknown_type] += 1

        unknowns = {
            "total": len(open_unknowns),
            "by_category": dict(by_category),
        }

    # ── Snapshots ─────────────────────────────────────────────────
    snapshots: list[dict] | None = None
    if _should_include("snapshots", include_sections):
        snap_result = await db.execute(
            select(BuildingSnapshot)
            .where(BuildingSnapshot.building_id == building_id)
            .order_by(BuildingSnapshot.captured_at.desc())
            .limit(5)
        )
        snapshot_records = list(snap_result.scalars().all())
        snapshots = [
            {
                "id": str(s.id),
                "captured_at": s.captured_at.isoformat() if s.captured_at else None,
                "passport_grade": s.passport_grade,
                "overall_trust": s.overall_trust,
                "completeness_score": s.completeness_score,
                "snapshot_type": s.snapshot_type,
            }
            for s in snapshot_records
        ]

    # ── Completeness ──────────────────────────────────────────────
    completeness: dict | None = None
    if _should_include("completeness", include_sections):
        try:
            from app.services.completeness_engine import evaluate_completeness

            comp_result = await evaluate_completeness(db, building_id)
            completeness = {
                "overall_score": comp_result.overall_score,
                "checks_passed": sum(1 for c in comp_result.checks if c.status == "complete"),
                "checks_failed": sum(1 for c in comp_result.checks if c.status == "missing"),
                "missing_items": comp_result.missing_items,
                "ready_to_proceed": comp_result.ready_to_proceed,
            }
        except Exception as e:
            logger.warning(f"Failed to evaluate completeness for building {building_id}: {e}")

    # ── Readiness ─────────────────────────────────────────────────
    readiness: dict | None = None
    if _should_include("readiness", include_sections):
        # Extract readiness from passport if already fetched, otherwise query
        if passport and "readiness" in passport:
            readiness = passport["readiness"]
        else:
            try:
                from app.services.passport_service import get_passport_summary

                passport_data = await get_passport_summary(db, building_id)
                if passport_data:
                    readiness = passport_data.get("readiness")
            except Exception as e:
                logger.warning(f"Failed to get readiness data for building {building_id}: {e}")

    # ── Eco clauses ────────────────────────────────────────────────
    eco_clauses: dict | None = None
    if _should_include("eco_clauses", include_sections):
        try:
            from app.services.eco_clause_template_service import generate_eco_clauses

            eco_payload = await generate_eco_clauses(building_id, "renovation", db)
            if eco_payload.detected_pollutants:
                eco_clauses = {
                    "context": eco_payload.context,
                    "total_clauses": eco_payload.total_clauses,
                    "detected_pollutants": eco_payload.detected_pollutants,
                    "sections": [
                        {
                            "section_id": s.section_id,
                            "title": s.title,
                            "clause_count": len(s.clauses),
                        }
                        for s in eco_payload.sections
                    ],
                }
        except Exception as e:
            logger.warning("Failed to generate eco clauses for building %s: %s", building_id, e)

    # ── Diagnostic publications (external reports) ─────────────────
    diagnostic_publications: list[dict] | None = None
    if _should_include("diagnostic_publications", include_sections):
        from app.services.imported_diagnostic_dossier import project_dossier_summary

        pub_result = await db.execute(
            select(DiagnosticReportPublication).where(
                and_(
                    DiagnosticReportPublication.building_id == building_id,
                    DiagnosticReportPublication.match_state.in_(["auto_matched", "manual_matched"]),
                )
            )
        )
        pubs = list(pub_result.scalars().all())
        diagnostic_publications = [
            {
                **project_dossier_summary(p),
                "id": str(p.id),
                "mission_type": p.mission_type,
                "report_pdf_url": p.report_pdf_url,
            }
            for p in pubs
        ]

    # ── Metadata ──────────────────────────────────────────────────
    included = include_sections if include_sections else list(TRANSFER_PACKAGE_SECTIONS)
    metadata = {
        "generator": "SwissBuildingOS",
        "generator_version": TRANSFER_PACKAGE_VERSION,
        "generation_time_utc": generated_at.isoformat(),
        "sections_included": included,
        "financials_redacted": redact_financials,
    }

    # ── Apply financial redaction if requested ────────────────────
    if redact_financials:
        if interventions_summary and isinstance(interventions_summary, dict):
            interventions_summary = _redact_dict(interventions_summary)
        if actions_summary and isinstance(actions_summary, dict):
            actions_summary = _redact_dict(actions_summary)
        if eco_clauses and isinstance(eco_clauses, dict):
            eco_clauses = _redact_dict(eco_clauses)
        if snapshots:
            snapshots = [_redact_dict(s) if isinstance(s, dict) else s for s in snapshots]
        if diagnostic_publications:
            diagnostic_publications = [_redact_dict(p) if isinstance(p, dict) else p for p in diagnostic_publications]

    return TransferPackageResponse(
        package_id=package_id,
        building_id=building_id,
        generated_at=generated_at,
        schema_version=TRANSFER_PACKAGE_VERSION,
        building_summary=building_summary,
        passport=passport,
        diagnostics_summary=diagnostics_summary,
        documents_summary=documents_summary,
        interventions_summary=interventions_summary,
        actions_summary=actions_summary,
        evidence_coverage=evidence_coverage,
        contradictions=contradictions,
        unknowns=unknowns,
        snapshots=snapshots,
        completeness=completeness,
        readiness=readiness,
        eco_clauses=eco_clauses,
        diagnostic_publications=diagnostic_publications,
        financials_redacted=redact_financials,
        metadata=metadata,
    )
