import math
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class RiskScoreRead(BaseModel):
    id: UUID
    building_id: UUID
    asbestos_probability: float
    pcb_probability: float
    lead_probability: float
    hap_probability: float
    radon_probability: float
    overall_risk_level: str
    confidence: float
    factors_json: dict[str, Any] | None
    data_source: str
    last_updated: datetime

    model_config = ConfigDict(from_attributes=True)


class RenovationSimulationRequest(BaseModel):
    building_id: UUID
    renovation_type: str  # full_renovation, partial_interior, roof, facade, bathroom, kitchen, flooring, windows


class RenovationSimulationResponse(BaseModel):
    building_id: UUID
    renovation_type: str
    pollutant_risks: list["PollutantRiskDetail"]
    total_estimated_cost_chf: float
    required_diagnostics: list[str]
    compliance_requirements: list["ComplianceRequirementDetail"]
    timeline_weeks: int


class PollutantRiskDetail(BaseModel):
    pollutant: str
    probability: float
    risk_level: str
    exposure_factor: float
    materials_at_risk: list[str]
    estimated_cost_chf: float

    @field_validator("probability", "exposure_factor", "estimated_cost_chf", mode="before")
    @classmethod
    def validate_finite_float(cls, v):
        if v is not None and isinstance(v, (int, float)) and (math.isinf(v) or math.isnan(v)):
            raise ValueError("value must be a finite number")
        return v


class ComplianceRequirementDetail(BaseModel):
    requirement: str
    legal_reference: str
    mandatory: bool
    deadline_days: int | None


RenovationSimulationResponse.model_rebuild()


class SinistraliteScoreRead(BaseModel):
    """Read schema for sinistralite (claims/loss) score."""

    building_id: UUID
    score: float
    risk_level: str
    incident_count: int
    weighted_severity: float
    computed_at: datetime

    model_config = ConfigDict(from_attributes=True)
