import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.constants import PLAN_ANNOTATION_TYPES


class PlanAnnotationCreate(BaseModel):
    annotation_type: str
    label: str
    x: float
    y: float
    description: str | None = None
    zone_id: uuid.UUID | None = None
    sample_id: uuid.UUID | None = None
    element_id: uuid.UUID | None = None
    color: str | None = None
    icon: str | None = None
    metadata_json: dict | None = None

    @field_validator("annotation_type")
    @classmethod
    def validate_annotation_type(cls, v: str) -> str:
        if v not in PLAN_ANNOTATION_TYPES:
            raise ValueError(f"annotation_type must be one of {PLAN_ANNOTATION_TYPES}")
        return v

    @field_validator("x", "y")
    @classmethod
    def validate_coordinates(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("Coordinate must be between 0.0 and 1.0")
        return v


class PlanAnnotationUpdate(BaseModel):
    annotation_type: str | None = None
    label: str | None = None
    x: float | None = None
    y: float | None = None
    description: str | None = None
    zone_id: uuid.UUID | None = None
    sample_id: uuid.UUID | None = None
    element_id: uuid.UUID | None = None
    color: str | None = None
    icon: str | None = None
    metadata_json: dict | None = None

    @field_validator("annotation_type")
    @classmethod
    def validate_annotation_type(cls, v: str | None) -> str | None:
        if v is not None and v not in PLAN_ANNOTATION_TYPES:
            raise ValueError(f"annotation_type must be one of {PLAN_ANNOTATION_TYPES}")
        return v

    @field_validator("x", "y")
    @classmethod
    def validate_coordinates(cls, v: float | None) -> float | None:
        if v is not None and not 0.0 <= v <= 1.0:
            raise ValueError("Coordinate must be between 0.0 and 1.0")
        return v


class PlanAnnotationRead(BaseModel):
    id: uuid.UUID
    plan_id: uuid.UUID
    building_id: uuid.UUID
    annotation_type: str
    label: str
    x: float
    y: float
    description: str | None
    zone_id: uuid.UUID | None
    sample_id: uuid.UUID | None
    element_id: uuid.UUID | None
    color: str | None
    icon: str | None
    metadata_json: dict | None
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
