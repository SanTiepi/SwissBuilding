"""Read-model schema for imported diagnostic summaries (BatiConnect surface)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ImportedDiagnosticSummary(BaseModel):
    """Projected read-model from DiagnosticReportPublication — no new DB table."""

    # Source origin
    source_system: str
    mission_ref: str
    published_at: datetime

    # Local ingestion state
    consumer_state: str | None

    # Building match state
    match_state: str
    match_key_type: str | None
    building_id: UUID | None

    # Report readiness (extracted from structured_summary, no recalculation)
    report_readiness_status: str | None  # ready|blocked|partial|unknown

    # Publication summary
    snapshot_version: int
    payload_hash: str
    contract_version: str | None

    # Sample summary (high-level, no recalculation)
    sample_count: int | None
    positive_count: int | None
    review_count: int | None
    not_analyzed_count: int | None

    # AI and remediation
    ai_summary_text: str | None
    has_ai: bool
    has_remediation: bool
    is_partial: bool

    # Flags
    flags: list[str]  # ["no_ai", "no_remediation", "partial_package", "rejected_source"]

    model_config = ConfigDict(from_attributes=True)
