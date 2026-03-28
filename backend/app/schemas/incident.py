"""BatiConnect - Incident & Damage Memory Schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Incident Episode
# ---------------------------------------------------------------------------


class IncidentEpisodeCreate(BaseModel):
    incident_type: str  # leak | mold | flooding | fire | subsidence | movement | breakage | equipment_failure | vandalism | storm_damage | pest | contamination | structural | other
    title: str
    description: str | None = None
    discovered_at: datetime | None = None
    zone_id: UUID | None = None
    element_id: UUID | None = None
    location_description: str | None = None
    severity: str = "minor"  # minor | moderate | major | critical
    affected_units: list | None = None
    occupant_impact: bool = False
    service_disruption: bool = False
    cause_description: str | None = None
    cause_category: str = "unknown"  # wear | defect | external | accident | negligence | unknown
    recurring: bool = False
    previous_incident_id: UUID | None = None
    response_description: str | None = None
    repair_cost_chf: float | None = None
    insurance_claim_filed: bool = False
    insurance_claim_id: UUID | None = None
    evidence_document_ids: list | None = None
    case_id: UUID | None = None


class IncidentEpisodeUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    incident_type: str | None = None
    discovered_at: datetime | None = None
    resolved_at: datetime | None = None
    zone_id: UUID | None = None
    element_id: UUID | None = None
    location_description: str | None = None
    severity: str | None = None
    affected_units: list | None = None
    occupant_impact: bool | None = None
    service_disruption: bool | None = None
    cause_description: str | None = None
    cause_category: str | None = None
    recurring: bool | None = None
    previous_incident_id: UUID | None = None
    response_description: str | None = None
    repair_cost_chf: float | None = None
    insurance_claim_filed: bool | None = None
    insurance_claim_id: UUID | None = None
    evidence_document_ids: list | None = None
    status: str | None = None


class IncidentResolveRequest(BaseModel):
    resolution_description: str
    repair_cost_chf: float | None = None


class IncidentEpisodeRead(BaseModel):
    id: UUID
    building_id: UUID
    case_id: UUID | None
    organization_id: UUID
    incident_type: str
    title: str
    description: str | None
    discovered_at: datetime
    resolved_at: datetime | None
    zone_id: UUID | None
    element_id: UUID | None
    location_description: str | None
    severity: str
    affected_units: list | None
    occupant_impact: bool
    service_disruption: bool
    cause_description: str | None
    cause_category: str
    recurring: bool
    previous_incident_id: UUID | None
    response_description: str | None
    repair_cost_chf: float | None
    insurance_claim_filed: bool
    insurance_claim_id: UUID | None
    evidence_document_ids: list | None
    status: str
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IncidentEpisodeListRead(BaseModel):
    id: UUID
    building_id: UUID
    incident_type: str
    title: str
    severity: str
    status: str
    discovered_at: datetime
    resolved_at: datetime | None
    recurring: bool
    occupant_impact: bool

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Damage Observation
# ---------------------------------------------------------------------------


class DamageObservationCreate(BaseModel):
    damage_type: (
        str  # crack | stain | corrosion | deformation | efflorescence | peeling | rot | erosion | displacement | other
    )
    location_description: str
    zone_id: UUID | None = None
    element_id: UUID | None = None
    severity: str = "cosmetic"  # cosmetic | functional | structural | safety
    progression: str = "unknown"  # stable | slow | rapid | unknown
    observed_at: datetime | None = None
    photo_document_ids: list | None = None
    notes: str | None = None
    incident_id: UUID | None = None


class DamageObservationRead(BaseModel):
    id: UUID
    building_id: UUID
    incident_id: UUID | None
    damage_type: str
    location_description: str
    zone_id: UUID | None
    element_id: UUID | None
    severity: str
    progression: str
    observed_at: datetime
    observed_by_id: UUID | None
    photo_document_ids: list | None
    notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Risk Profile & Insurer Summary
# ---------------------------------------------------------------------------


class IncidentTypeCount(BaseModel):
    incident_type: str
    count: int


class SeverityCount(BaseModel):
    severity: str
    count: int


class IncidentRiskProfile(BaseModel):
    building_id: UUID
    total_incidents: int
    unresolved_count: int
    recurring_count: int
    by_type: list[IncidentTypeCount]
    by_severity: list[SeverityCount]
    total_repair_cost_chf: float
    avg_resolution_days: float | None
    most_common_type: str | None
    most_common_cause: str | None


class InsurerIncidentSummary(BaseModel):
    building_id: UUID
    total_incidents: int
    claims_filed: int
    unresolved_incidents: int
    recurring_risks: int
    total_damage_cost_chf: float
    occupant_impact_incidents: int
    critical_incidents: int
    last_incident_at: datetime | None
    risk_rating: str  # low | moderate | elevated | high
