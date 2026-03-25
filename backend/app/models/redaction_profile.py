"""Finance Surfaces — Redaction Profile + Decision Caveat Profile models.

ExternalAudienceRedactionProfile: controls which sections/fields are visible per audience.
DecisionCaveatProfile: templated warnings attached to packs based on data conditions.
"""

import uuid

from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.sql import func

from app.database import Base


class ExternalAudienceRedactionProfile(Base):
    __tablename__ = "external_audience_redaction_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_code = Column(String(50), unique=True, nullable=False)
    audience_type = Column(String(30), nullable=False)  # insurer | fiduciary | transaction | lender | authority | other
    allowed_sections = Column(JSON, nullable=False)  # ["building_identity", "diagnostics_summary", ...]
    blocked_sections = Column(JSON, nullable=False)  # ["financial", "internal_notes", ...]
    redacted_fields = Column(JSON, nullable=True)  # [{section, field, reason}]
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class DecisionCaveatProfile(Base):
    __tablename__ = "decision_caveat_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audience_type = Column(String(30), nullable=False)  # insurer | fiduciary | transaction | lender | authority | other
    caveat_type = Column(
        String(30), nullable=False
    )  # freshness_warning | confidence_caveat | unknown_disclosure | contradiction_notice | residual_risk_notice | regulatory_caveat
    template_text = Column(Text, nullable=False)
    severity = Column(String(10), nullable=False)  # info | warning | critical
    applies_when = Column(JSON, nullable=False)  # {freshness_state: "stale", confidence_level: "review_required"}
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
