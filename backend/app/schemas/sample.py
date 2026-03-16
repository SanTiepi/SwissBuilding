from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.constants import normalize_sample_unit


class SampleCreate(BaseModel):
    sample_number: str
    location_floor: str | None = None
    location_room: str | None = None
    location_detail: str | None = None
    material_category: str
    material_description: str | None = None
    material_state: str | None = None  # bon, moyen, mauvais, degrade
    pollutant_type: str  # asbestos, pcb, lead, hap, radon
    pollutant_subtype: str | None = None
    concentration: float | None = Field(None, allow_inf_nan=False)
    unit: str  # percent_weight, mg_per_kg, ug_per_l, bq_per_m3, fibers_per_m3, ng_per_m3
    notes: str | None = None

    @field_validator("unit", mode="before")
    @classmethod
    def normalize_unit(cls, value: str) -> str:
        normalized = normalize_sample_unit(value, strict=True)
        if normalized is None:
            raise ValueError("Unit is required")
        return normalized


class SampleUpdate(BaseModel):
    location_floor: str | None = None
    location_room: str | None = None
    location_detail: str | None = None
    material_description: str | None = None
    material_state: str | None = None
    pollutant_subtype: str | None = None
    concentration: float | None = Field(None, allow_inf_nan=False)
    unit: str | None = None
    notes: str | None = None

    @field_validator("unit", mode="before")
    @classmethod
    def normalize_unit(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_sample_unit(value, strict=True)


class SampleRead(BaseModel):
    id: UUID
    diagnostic_id: UUID
    sample_number: str
    location_floor: str | None
    location_room: str | None
    location_detail: str | None
    material_category: str
    material_description: str | None
    material_state: str | None
    pollutant_type: str
    pollutant_subtype: str | None
    concentration: float | None
    unit: str
    threshold_exceeded: bool
    risk_level: str | None
    cfst_work_category: str | None
    action_required: str | None
    waste_disposal_type: str | None
    notes: str | None
    created_at: datetime

    @field_validator("unit", mode="before")
    @classmethod
    def normalize_unit(cls, value: str) -> str:
        normalized = normalize_sample_unit(value)
        return normalized or value

    model_config = ConfigDict(from_attributes=True)
