"""Schemas for regulatory filing service (SUVA, cantonal declarations, OLED waste manifests)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# --- SUVA Notification ---


class PollutantLocation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sample_id: UUID
    pollutant_type: str
    location: str | None = None
    material_description: str | None = None
    material_state: str | None = None
    concentration: float | None = None
    unit: str | None = None
    cfst_work_category: str | None = None
    risk_level: str | None = None


class ContractorInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    contractor_name: str | None = None
    contractor_id: UUID | None = None
    intervention_type: str | None = None
    date_start: str | None = None
    date_end: str | None = None


class SafetyMeasure(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: str
    description: str
    cfst_reference: str | None = None


class SuvaNotification(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    address: str
    postal_code: str
    city: str
    canton: str
    construction_year: int | None = None
    pollutant_locations: list[PollutantLocation] = Field(default_factory=list)
    max_work_category: str | None = None
    estimated_duration_days: int | None = None
    contractor: ContractorInfo | None = None
    safety_measures: list[SafetyMeasure] = Field(default_factory=list)
    suva_notification_required: bool = False
    diagnostic_references: list[str] = Field(default_factory=list)
    generated_at: datetime


# --- Cantonal Declaration ---


class DiagnosticReference(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    diagnostic_id: UUID
    diagnostic_type: str
    status: str
    date_report: str | None = None
    laboratory: str | None = None
    laboratory_report_number: str | None = None


class CantonalDeclaration(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    canton: str
    format_variant: str  # "VD" or "GE" or "standard"
    address: str
    postal_code: str
    city: str
    construction_year: int | None = None
    pollutant_summary: dict[str, int] = Field(default_factory=dict)
    required_fields: list[str] = Field(default_factory=list)
    diagnostic_references: list[DiagnosticReference] = Field(default_factory=list)
    compliance_commitments: list[str] = Field(default_factory=list)
    canton_specific_notes: list[str] = Field(default_factory=list)
    generated_at: datetime


# --- Waste Manifest ---


class WasteEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    waste_category: str  # type_b, type_e, special
    description: str
    estimated_volume_m3: float = 0.0
    estimated_weight_tons: float = 0.0
    source_location: str | None = None


class DisposalFacility(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    facility_type: str
    waste_categories_accepted: list[str] = Field(default_factory=list)


class TransportChainStep(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    step_number: int
    description: str
    requirements: list[str] = Field(default_factory=list)


class ResponsibleParty(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: str
    name: str | None = None
    contact_id: UUID | None = None


class WasteManifest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    tracking_number: str
    waste_entries: list[WasteEntry] = Field(default_factory=list)
    disposal_facilities: list[DisposalFacility] = Field(default_factory=list)
    transport_chain: list[TransportChainStep] = Field(default_factory=list)
    responsible_parties: list[ResponsibleParty] = Field(default_factory=list)
    regulatory_references: list[str] = Field(default_factory=list)
    generated_at: datetime


# --- Filing Status ---


class FilingTypeStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    filing_type: str  # suva_notification, cantonal_declaration, waste_manifest
    required: bool = False
    reason: str | None = None
    completed: bool = False
    completed_date: str | None = None
    overdue: bool = False
    next_action: str | None = None


class FilingStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    filings: list[FilingTypeStatus] = Field(default_factory=list)
    total_required: int = 0
    total_completed: int = 0
    total_overdue: int = 0
    generated_at: datetime
