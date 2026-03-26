"""Imported diagnostic service — pure projection from DiagnosticReportPublication.

NO new DB table, NO recalculation. Reads structured_summary and maps to a
clean read-model for the frontend.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.diagnostic_publication import DiagnosticReportPublication
from app.schemas.imported_diagnostic import ImportedDiagnosticSummary


def project_summary(publication: DiagnosticReportPublication) -> ImportedDiagnosticSummary:
    """Project a publication into a clean read-model for the UI."""
    summary = publication.structured_summary or {}

    # Extract sample counts (from structured_summary, no recalculation)
    sample_count = summary.get("sample_count")
    positive_count = summary.get("positive_sample_count")

    # Extract AI summary
    ai_data = summary.get("ai_structured_summary", {})
    ai_summary_text = ai_data.get("summary_text") if isinstance(ai_data, dict) else None

    # Detect flags
    has_ai = bool(ai_data and ai_summary_text)
    has_remediation = bool(summary.get("remediation_handoff"))
    flags: list[str] = []
    if not has_ai:
        flags.append("no_ai")
    if not has_remediation:
        flags.append("no_remediation")

    # Detect partial package
    is_partial = not summary.get("pollutants_found") or not sample_count
    if is_partial:
        flags.append("partial_package")

    # Report readiness
    report_readiness = summary.get("report_readiness", {})
    readiness_status = report_readiness.get("status") if isinstance(report_readiness, dict) else None

    # Consumer state mapping
    consumer_state = publication.consumer_state
    if consumer_state == "rejected_source":
        flags.append("rejected_source")

    return ImportedDiagnosticSummary(
        source_system=publication.source_system,
        mission_ref=publication.source_mission_id,
        published_at=publication.published_at,
        consumer_state=consumer_state,
        match_state=publication.match_state,
        match_key_type=publication.match_key_type,
        building_id=publication.building_id,
        report_readiness_status=readiness_status,
        snapshot_version=publication.current_version,
        payload_hash=publication.payload_hash,
        contract_version=getattr(publication, "contract_version", None),
        sample_count=sample_count,
        positive_count=positive_count,
        review_count=summary.get("review_sample_count"),
        not_analyzed_count=summary.get("not_analyzed_count"),
        ai_summary_text=ai_summary_text,
        has_ai=has_ai,
        has_remediation=has_remediation,
        is_partial=is_partial,
        flags=flags,
    )


async def get_building_diagnostic_summaries(db: AsyncSession, building_id: UUID) -> list[ImportedDiagnosticSummary]:
    """Get all imported diagnostic summaries for a building."""
    result = await db.execute(
        select(DiagnosticReportPublication).where(DiagnosticReportPublication.building_id == building_id)
    )
    publications = result.scalars().all()
    return [project_summary(pub) for pub in publications]
