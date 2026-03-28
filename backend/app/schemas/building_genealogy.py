"""Pydantic schemas for the Building Genealogy (TransformationEpisode, OwnershipEpisode, HistoricalClaim)."""

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# TransformationEpisode
# ---------------------------------------------------------------------------


class TransformationEpisodeCreate(BaseModel):
    episode_type: str = Field(
        ...,
        description=(
            "construction, renovation, extension, demolition_partial, "
            "change_of_use, merger, split, restoration, modernization, remediation, other"
        ),
    )
    title: str
    description: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    approximate: bool = False
    evidence_basis: str = Field(
        "unknown",
        description="documented, observed, inferred, declared, unknown",
    )
    evidence_ids: list[uuid.UUID] | None = None
    spatial_scope: dict[str, Any] | None = None
    state_before_summary: str | None = None
    state_after_summary: str | None = None


class TransformationEpisodeRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    episode_type: str
    title: str
    description: str | None
    period_start: date | None
    period_end: date | None
    approximate: bool
    evidence_basis: str
    evidence_ids: list[Any] | None
    spatial_scope: dict[str, Any] | None
    state_before_summary: str | None
    state_after_summary: str | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# OwnershipEpisode
# ---------------------------------------------------------------------------


class OwnershipEpisodeCreate(BaseModel):
    owner_name: str | None = None
    owner_type: str = Field(
        "unknown",
        description="individual, company, public, cooperative, foundation, unknown",
    )
    period_start: date | None = None
    period_end: date | None = None
    approximate: bool = False
    evidence_basis: str = Field(
        "declared",
        description="registry, document, declared, inferred",
    )
    source_document_id: uuid.UUID | None = None
    acquisition_type: str = Field(
        "unknown",
        description="purchase, inheritance, donation, exchange, other, unknown",
    )


class OwnershipEpisodeRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    owner_name: str | None
    owner_type: str
    period_start: date | None
    period_end: date | None
    approximate: bool
    evidence_basis: str
    source_document_id: uuid.UUID | None
    acquisition_type: str
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# HistoricalClaim
# ---------------------------------------------------------------------------


class HistoricalClaimCreate(BaseModel):
    claim_type: str = Field(
        ...,
        description=(
            "construction_date, material_presence, use_type, "
            "intervention_performed, condition_at_date, owner_at_date, other"
        ),
    )
    subject: str
    assertion: str
    reference_date: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    evidence_basis: str = Field(
        "inference",
        description="document, photograph, testimony, inference, registry",
    )
    confidence: float = Field(0.5, ge=0, le=1)
    source_description: str | None = None
    status: str = Field("recorded", description="recorded, verified, contested, superseded")


class HistoricalClaimRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    claim_type: str
    subject: str
    assertion: str
    reference_date: date | None
    period_start: date | None
    period_end: date | None
    evidence_basis: str
    confidence: float
    source_description: str | None
    status: str
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Genealogy composite responses
# ---------------------------------------------------------------------------


class BuildingGenealogyResponse(BaseModel):
    building_id: uuid.UUID
    transformations: list[TransformationEpisodeRead]
    ownership_episodes: list[OwnershipEpisodeRead]
    historical_claims: list[HistoricalClaimRead]


class GenealogyTimelineEntry(BaseModel):
    id: uuid.UUID
    entry_type: str  # transformation, ownership, claim, event
    occurred_at: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    title: str
    description: str | None = None
    evidence_basis: str | None = None
    metadata: dict[str, Any] | None = None


class GenealogyTimeline(BaseModel):
    building_id: uuid.UUID
    entries: list[GenealogyTimelineEntry]
    total_entries: int


class DeclaredVsObservedDiscrepancy(BaseModel):
    claim_id: uuid.UUID
    claim_subject: str
    claim_assertion: str
    claim_basis: str
    observed_value: str | None = None
    observed_source: str | None = None
    discrepancy_type: str  # contradiction, unverified, partial_match, missing_observation
    explanation: str


class DeclaredVsObservedResponse(BaseModel):
    building_id: uuid.UUID
    total_claims: int
    verified_count: int
    contested_count: int
    unverified_count: int
    discrepancies: list[DeclaredVsObservedDiscrepancy]
