"""BatiConnect — Expansion signal and customer success schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# --- Account Expansion Trigger ---


class AccountExpansionTriggerRead(BaseModel):
    id: UUID
    organization_id: UUID
    trigger_type: str
    source_entity_type: str | None
    source_entity_id: UUID | None
    evidence_summary: str
    detected_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Distribution Loop Signal ---


class DistributionLoopSignalRead(BaseModel):
    id: UUID
    building_id: UUID
    organization_id: UUID | None
    signal_type: str
    audience_type: str | None
    source_entity_type: str | None
    source_entity_id: UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Expansion Opportunity ---


class ExpansionOpportunityRead(BaseModel):
    id: UUID
    organization_id: UUID
    opportunity_type: str
    status: str
    recommended_action: str
    evidence: Any | None
    priority: str
    detected_at: datetime
    acted_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExpansionOpportunityAction(BaseModel):
    notes: str | None = None


# --- Customer Success Milestone ---


class CustomerSuccessMilestoneRead(BaseModel):
    id: UUID
    organization_id: UUID
    milestone_type: str
    status: str
    achieved_at: datetime | None
    evidence_entity_type: str | None
    evidence_entity_id: UUID | None
    evidence_summary: str | None
    blocker_description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerSuccessReport(BaseModel):
    organization_id: UUID
    milestones: list[CustomerSuccessMilestoneRead]
    next_step: NextStepInfo | None


class NextStepInfo(BaseModel):
    milestone_type: str
    recommendation: str


# Rebuild forward refs
CustomerSuccessReport.model_rebuild()
