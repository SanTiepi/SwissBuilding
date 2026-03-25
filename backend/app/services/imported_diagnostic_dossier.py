"""Imported diagnostic dossier projection helper.

Provides a compact, dossier-safe dict projection from DiagnosticReportPublication,
suitable for embedding in passport, timeline, and transfer package outputs.

Reuses the same extraction logic as imported_diagnostic_service.project_summary
but returns a plain dict (no Pydantic model) for direct embedding.
"""

from __future__ import annotations

from app.models.diagnostic_publication import DiagnosticReportPublication


def project_dossier_summary(publication: DiagnosticReportPublication) -> dict:
    """Compact dossier-safe projection from DiagnosticReportPublication.

    Reuses the same logic as imported_diagnostic_service.project_summary
    but returns a plain dict suitable for embedding in passport/timeline/transfer.
    """
    summary = publication.structured_summary or {}
    ai_data = summary.get("ai_structured_summary", {})
    ai_text = ai_data.get("summary_text") if isinstance(ai_data, dict) else None
    has_ai = bool(ai_data and ai_text)
    has_remediation = bool(summary.get("remediation_handoff"))
    sample_count = summary.get("sample_count")
    is_partial = not summary.get("pollutants_found") or not sample_count

    flags: list[str] = []
    if not has_ai:
        flags.append("no_ai")
    if not has_remediation:
        flags.append("no_remediation")
    if is_partial:
        flags.append("partial_package")

    readiness = summary.get("report_readiness", {})
    readiness_status = readiness.get("status") if isinstance(readiness, dict) else None

    return {
        "source_system": publication.source_system,
        "mission_ref": publication.source_mission_id,
        "published_at": publication.published_at.isoformat() if publication.published_at else None,
        "local_ingestion_status": publication.consumer_state or "imported",
        "building_match_status": publication.match_state,
        "report_readiness_status": readiness_status,
        "snapshot_version": publication.current_version,
        "snapshot_ref": None,  # Explicitly unavailable until bridge v2
        "payload_hash": publication.payload_hash,
        "sample_count": sample_count,
        "positive_sample_count": summary.get("positive_sample_count"),
        "ai_summary_text": ai_text,
        "flags": flags,
    }
