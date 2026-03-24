"""SwissBuildingOS - Material Recommendation Schemas."""

from __future__ import annotations

from pydantic import BaseModel


class EvidenceRequirement(BaseModel):
    """A single evidence document required for a material recommendation."""

    document_type: str
    description: str
    mandatory: bool = True
    legal_ref: str | None = None


class MaterialRecommendation(BaseModel):
    """A recommended replacement material for a pollutant-containing material."""

    original_material_type: str
    original_pollutant: str
    recommended_material: str
    recommended_material_type: str
    reason: str
    risk_level: str
    evidence_requirements: list[EvidenceRequirement]
    risk_flags: list[str]


class MaterialRecommendationReport(BaseModel):
    """Full recommendation report for a building's material replacements."""

    building_id: str
    intervention_count: int
    pollutant_material_count: int
    recommendations: list[MaterialRecommendation]
    summary: str
