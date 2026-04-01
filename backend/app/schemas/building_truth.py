import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# ── BuildingClaim schemas ──


class BuildingClaimCreate(BaseModel):
    claim_type: str
    subject: str
    assertion: str
    basis_type: str
    basis_ids: list[str] | None = None
    confidence: float | None = Field(None, ge=0, le=1)
    case_id: uuid.UUID | None = None
    zone_id: uuid.UUID | None = None
    element_id: uuid.UUID | None = None


class BuildingClaimRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    case_id: uuid.UUID | None
    organization_id: uuid.UUID
    claimed_by_id: uuid.UUID
    claim_type: str
    subject: str
    assertion: str
    basis_type: str
    basis_ids: list | None
    confidence: float | None
    status: str
    verified_by_id: uuid.UUID | None
    verified_at: datetime | None
    contested_by_id: uuid.UUID | None
    contestation_reason: str | None
    superseded_by_id: uuid.UUID | None
    superseded_at: datetime | None
    zone_id: uuid.UUID | None
    element_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ClaimContestRequest(BaseModel):
    reason: str


class ClaimVerifyRequest(BaseModel):
    """Optional body for verify — currently empty but extensible."""


# ── BuildingDecision schemas ──


class BuildingDecisionCreate(BaseModel):
    decision_type: str
    title: str
    description: str | None = None
    basis_claims: list[str] | None = None
    basis_evidence: list[str] | None = None
    outcome: str
    rationale: str
    authority_level: str = "operator"
    reversible: bool = True
    case_id: uuid.UUID | None = None


class BuildingDecisionRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    case_id: uuid.UUID | None
    organization_id: uuid.UUID
    decision_maker_id: uuid.UUID
    decision_type: str
    title: str
    description: str | None
    basis_claims: list | None
    basis_evidence: list | None
    outcome: str
    rationale: str
    authority_level: str
    reversible: bool
    status: str
    enacted_at: datetime | None
    reversed_at: datetime | None
    reversed_by_id: uuid.UUID | None
    reversal_reason: str | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class DecisionReverseRequest(BaseModel):
    reason: str


# ── Truth state ──


class TruthStateRead(BaseModel):
    active_claims: list[BuildingClaimRead]
    contested_claims: list[BuildingClaimRead]
    recent_decisions: list[BuildingDecisionRead]
    summary: dict
