"""Schemas for permit tracking."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RequiredDocument(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    description: str | None = None
    available: bool = False


class RequiredPermit(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    permit_type: str
    authority: str
    estimated_processing_days: int
    required_documents: list[RequiredDocument] = Field(default_factory=list)
    reason: str


class RequiredPermitsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    permits: list[RequiredPermit] = Field(default_factory=list)
    total_permits: int = 0
    generated_at: datetime


class PermitTimeline(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event: str
    date: str | None = None


class PermitStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    permit_type: str
    status: str  # not_started, application_submitted, under_review, approved, rejected, expired
    authority: str
    timeline: list[PermitTimeline] = Field(default_factory=list)
    days_since_submission: int | None = None
    estimated_remaining_days: int | None = None


class PermitStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    permits: list[PermitStatus] = Field(default_factory=list)
    overall_readiness: str  # blocked, partial, ready
    generated_at: datetime


class PermitDependency(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    permit_type: str
    blocks: list[str] = Field(default_factory=list)
    blocked_by: list[str] = Field(default_factory=list)
    status: str


class PermitDependencyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    dependencies: list[PermitDependency] = Field(default_factory=list)
    blocking_permits: list[str] = Field(default_factory=list)
    generated_at: datetime


class BuildingPermitSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    address: str
    total_permits: int = 0
    approved_count: int = 0
    pending_count: int = 0
    blocked: bool = False


class PortfolioPermitOverview(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: UUID
    buildings: list[BuildingPermitSummary] = Field(default_factory=list)
    total_permits_needed: int = 0
    total_approved: int = 0
    total_pending: int = 0
    approval_rate: float = 0.0
    avg_processing_days: int = 0
    buildings_blocked_count: int = 0
    generated_at: datetime
