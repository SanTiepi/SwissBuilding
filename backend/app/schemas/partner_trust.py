"""BatiConnect — Partner trust schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PartnerTrustProfileRead(BaseModel):
    id: UUID
    partner_org_id: UUID
    delivery_reliability_score: float | None
    evidence_quality_score: float | None
    responsiveness_score: float | None
    overall_trust_level: str
    signal_count: int
    last_evaluated_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PartnerTrustSignalRead(BaseModel):
    id: UUID
    partner_org_id: UUID
    signal_type: str
    source_entity_type: str | None
    source_entity_id: UUID | None
    value: float | None
    notes: str | None
    recorded_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrustSignalCreate(BaseModel):
    partner_org_id: UUID
    signal_type: str
    source_entity_type: str | None = None
    source_entity_id: UUID | None = None
    value: float | None = None
    notes: str | None = None


class RoutingHintRead(BaseModel):
    partner_org_id: UUID
    workflow_type: str
    recommendation: str  # preferred | review | avoid
    overall_trust_level: str
    signal_count: int


class CasePartnerTrustRead(BaseModel):
    """Trust profile of a partner in the context of a specific case."""

    partner_org_id: UUID
    case_id: UUID
    overall_trust_level: str
    delivery_reliability_score: float | None
    evidence_quality_score: float | None
    responsiveness_score: float | None
    total_signal_count: int
    case_signal_count: int


class TrustedPartnerRead(BaseModel):
    """A partner qualified for panel selection (adequate+ trust)."""

    partner_org_id: UUID
    overall_trust_level: str
    delivery_reliability_score: float | None
    evidence_quality_score: float | None
    responsiveness_score: float | None
    signal_count: int
    work_family: str
    guidance: str  # qualified
