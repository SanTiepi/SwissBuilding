"""BatiConnect - Trust Semantics Mixin for confidence/freshness/identity columns.

Provides reusable trust-related columns for entities that need
confidence level, freshness state, and identity match tracking.

Apply via multiple inheritance on SQLAlchemy models:
    class MyModel(TrustSemanticsMixin, Base):
        ...
"""

from sqlalchemy import Boolean, Column, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID


class TrustSemanticsMixin:
    """Declarative mixin providing trust semantics columns.

    confidence_level: auto_safe | auto_with_notice | review_required | blocked
    freshness_state: current | aging | stale | superseded | review_dependent
    identity_match_type: egid_exact | egrid_exact | address_fuzzy | manual | unverified
    identity_match_confidence: high | medium | low | unverified
    """

    confidence_level = Column(Text, nullable=True)
    confidence_reason = Column(Text, nullable=True)
    freshness_state = Column(Text, nullable=True)
    freshness_checked_at = Column(DateTime, nullable=True)
    identity_match_type = Column(Text, nullable=True)
    identity_match_confidence = Column(Text, nullable=True)
    review_required = Column(Boolean, default=False)
    review_reason = Column(Text, nullable=True)
    reviewed_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
