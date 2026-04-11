"""Schemas for material recognition via Claude Vision API."""

from pydantic import BaseModel, ConfigDict, Field


class PollutantDetail(BaseModel):
    probability: float = Field(ge=0.0, le=1.0)
    reason: str = ""


class MaterialRecognitionResult(BaseModel):
    """Result from Claude Vision material recognition."""

    material_type: str
    material_name: str
    estimated_year_range: str = ""
    identified_materials: list[str] = []
    likely_pollutants: dict[str, PollutantDetail] = {}
    confidence_overall: float = Field(ge=0.0, le=1.0)
    recommendations: list[str] = []
    description: str = ""
    has_high_risk: bool = False

    model_config = ConfigDict(from_attributes=True)


class MaterialRecognitionRequest(BaseModel):
    """Optional metadata sent alongside the image upload."""

    building_id: str | None = None
    zone_id: str | None = None
    element_id: str | None = None
    notes: str | None = None
