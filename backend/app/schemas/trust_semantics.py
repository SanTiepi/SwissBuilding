"""BatiConnect - Trust Semantics schema (reusable nested model)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class TrustState(BaseModel):
    """Reusable trust state — embed in any Read schema that uses TrustSemanticsMixin."""

    confidence_level: str | None = None
    confidence_reason: str | None = None
    freshness_state: str | None = None
    freshness_checked_at: datetime | None = None
    identity_match_type: str | None = None
    identity_match_confidence: str | None = None
    review_required: bool = False
    review_reason: str | None = None
    reviewed_by_user_id: UUID | None = None
    reviewed_at: datetime | None = None
