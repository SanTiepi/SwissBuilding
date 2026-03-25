from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# ---- PublicOwnerOperatingMode ----


class PublicOwnerModeCreate(BaseModel):
    mode_type: str  # municipal | cantonal | federal | public_foundation | mixed
    is_active: bool = True
    governance_level: str = "standard"  # standard | enhanced | strict
    requires_committee_review: bool = False
    requires_review_pack: bool = True
    default_review_audience: list[str] | None = None
    notes: str | None = None
    activated_at: datetime | None = None


class PublicOwnerModeRead(BaseModel):
    id: UUID
    organization_id: UUID
    mode_type: str
    is_active: bool
    governance_level: str
    requires_committee_review: bool
    requires_review_pack: bool
    default_review_audience: list[str] | None
    notes: str | None
    activated_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---- MunicipalityReviewPack ----


class ReviewPackCreate(BaseModel):
    notes: str | None = None
    review_deadline: date | None = None


class ReviewPackRead(BaseModel):
    id: UUID
    building_id: UUID
    generated_by_user_id: UUID | None
    pack_version: int
    status: str
    sections: dict | list | None
    content_hash: str | None
    review_deadline: date | None
    circulated_to: list[dict] | None
    notes: str | None
    generated_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CirculateRequest(BaseModel):
    recipients: list[dict]  # [{org_name, role, sent_at}]


# ---- CommitteeDecisionPack ----


class CommitteePackCreate(BaseModel):
    committee_name: str
    committee_type: str  # municipal_council | building_committee | procurement_committee | technical_commission | other
    decision_deadline: date | None = None
    procurement_clauses: list[dict] | None = None


class CommitteePackRead(BaseModel):
    id: UUID
    building_id: UUID
    committee_name: str
    committee_type: str
    pack_version: int
    status: str
    sections: dict | list | None
    procurement_clauses: list[dict] | None
    content_hash: str | None
    decision_deadline: date | None
    submitted_at: datetime | None
    decided_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---- ReviewDecisionTrace ----


class DecisionTraceCreate(BaseModel):
    pack_type: str | None = None  # committee | municipal_review — set by endpoint
    pack_id: UUID | None = None  # set by endpoint from path param
    reviewer_name: str
    reviewer_role: str | None = None
    reviewer_org_id: UUID | None = None
    decision: str  # approved | rejected | deferred | modified | abstained
    conditions: str | None = None
    notes: str | None = None
    evidence_refs: list[dict] | None = None
    confidence_level: str | None = None
    decided_at: datetime


class DecisionTraceRead(BaseModel):
    id: UUID
    pack_type: str
    pack_id: UUID
    reviewer_name: str
    reviewer_role: str | None
    reviewer_org_id: UUID | None
    decision: str
    conditions: str | None
    notes: str | None
    evidence_refs: list[dict] | None
    confidence_level: str | None
    decided_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---- GovernanceSignal ----


class GovernanceSignalCreate(BaseModel):
    organization_id: UUID
    building_id: UUID | None = None
    signal_type: str
    severity: str = "info"
    title: str
    description: str | None = None
    source_entity_type: str | None = None
    source_entity_id: UUID | None = None


class GovernanceSignalRead(BaseModel):
    id: UUID
    organization_id: UUID
    building_id: UUID | None
    signal_type: str
    severity: str
    title: str
    description: str | None
    source_entity_type: str | None
    source_entity_id: UUID | None
    resolved: bool
    resolved_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
