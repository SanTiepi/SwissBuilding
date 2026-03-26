"""Schemas for address preview and instant card."""

from __future__ import annotations

import uuid as _uuid
from typing import Any

from pydantic import BaseModel, Field


class AddressPreviewRequest(BaseModel):
    """Request body for address preview (no building creation)."""

    address: str
    postal_code: str | None = None
    city: str | None = None


# --- Sub-sections ---


class IdentitySection(BaseModel):
    egid: int | None = None
    egrid: str | None = None
    parcel: str | None = None
    address_normalized: str | None = None
    lat: float | None = None
    lon: float | None = None


class PhysicalSection(BaseModel):
    construction_year: int | None = None
    floors: int | None = None
    dwellings: int | None = None
    surface_m2: float | None = None
    heating_type: str | None = None


class EnvironmentSection(BaseModel):
    radon: dict[str, Any] | None = None
    noise: dict[str, Any] | None = None
    hazards: dict[str, Any] | None = None
    seismic: dict[str, Any] | None = None


class EnergySection(BaseModel):
    solar_potential: dict[str, Any] | None = None
    heating_type: str | None = None
    district_heating_available: bool | None = None


class TransportSection(BaseModel):
    quality_class: str | None = None
    nearest_stops: list[dict[str, Any]] = Field(default_factory=list)
    ev_charging: dict[str, Any] | None = None


class RiskSection(BaseModel):
    pollutant_prediction: dict[str, Any] | None = None
    environmental_score: float | None = None


class ScoresSection(BaseModel):
    neighborhood: float | None = None
    livability: float | None = None
    connectivity: float | None = None
    overall_grade: str | None = None


class LifecycleSection(BaseModel):
    components: list[dict[str, Any]] = Field(default_factory=list)
    critical_count: int = 0
    urgent_count: int = 0


class RenovationSection(BaseModel):
    plan_summary: str | None = None
    total_cost: float | None = None
    total_subsidy: float | None = None
    roi_years: float | None = None


class ComplianceSection(BaseModel):
    checks_count: int = 0
    non_compliant_count: int = 0
    summary: str | None = None


class FinancialSection(BaseModel):
    cost_of_inaction: float | None = None
    energy_savings: float | None = None
    value_increase: float | None = None


class NarrativeSection(BaseModel):
    summary_fr: str | None = None


class MetadataSection(BaseModel):
    sources_used: list[str] = Field(default_factory=list)
    freshness: str = "current"
    run_id: _uuid.UUID | None = None


# --- Main result ---


class AddressPreviewResult(BaseModel):
    """Complete structured result from address preview enrichment."""

    identity: IdentitySection = Field(default_factory=IdentitySection)
    physical: PhysicalSection = Field(default_factory=PhysicalSection)
    environment: EnvironmentSection = Field(default_factory=EnvironmentSection)
    energy: EnergySection = Field(default_factory=EnergySection)
    transport: TransportSection = Field(default_factory=TransportSection)
    risk: RiskSection = Field(default_factory=RiskSection)
    scores: ScoresSection = Field(default_factory=ScoresSection)
    lifecycle: LifecycleSection = Field(default_factory=LifecycleSection)
    renovation: RenovationSection = Field(default_factory=RenovationSection)
    compliance: ComplianceSection = Field(default_factory=ComplianceSection)
    financial: FinancialSection = Field(default_factory=FinancialSection)
    narrative: NarrativeSection = Field(default_factory=NarrativeSection)
    metadata: MetadataSection = Field(default_factory=MetadataSection)


# --- Instant card (for existing buildings) ---


class InstantCardResult(BaseModel):
    """Aggregated instant card for an existing building."""

    building_id: _uuid.UUID
    identity: IdentitySection = Field(default_factory=IdentitySection)
    physical: PhysicalSection = Field(default_factory=PhysicalSection)
    environment: EnvironmentSection = Field(default_factory=EnvironmentSection)
    energy: EnergySection = Field(default_factory=EnergySection)
    transport: TransportSection = Field(default_factory=TransportSection)
    risk: RiskSection = Field(default_factory=RiskSection)
    scores: ScoresSection = Field(default_factory=ScoresSection)
    lifecycle: LifecycleSection = Field(default_factory=LifecycleSection)
    renovation: RenovationSection = Field(default_factory=RenovationSection)
    compliance: ComplianceSection = Field(default_factory=ComplianceSection)
    financial: FinancialSection = Field(default_factory=FinancialSection)
    narrative: NarrativeSection = Field(default_factory=NarrativeSection)
    metadata: MetadataSection = Field(default_factory=MetadataSection)


# --- Source snapshot read schema ---


class SourceSnapshotRead(BaseModel):
    id: _uuid.UUID
    building_id: _uuid.UUID | None = None
    enrichment_run_id: _uuid.UUID | None = None
    source_name: str
    source_category: str
    normalized_data: dict[str, Any] | None = None
    fetched_at: str | None = None
    freshness_state: str = "current"
    confidence: str = "medium"

    model_config = {"from_attributes": True}


class EnrichmentRunRead(BaseModel):
    id: _uuid.UUID
    building_id: _uuid.UUID | None = None
    address_input: str
    status: str
    sources_attempted: int = 0
    sources_succeeded: int = 0
    sources_failed: int = 0
    duration_ms: int | None = None
    error_summary: str | None = None
    started_at: str | None = None
    completed_at: str | None = None

    model_config = {"from_attributes": True}
