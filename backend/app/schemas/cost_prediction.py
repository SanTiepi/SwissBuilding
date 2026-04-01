"""
Schemas for the RénoPredict cost prediction module.

Handles request validation and response formatting for pollutant remediation
cost estimation based on Swiss market averages.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CostPredictionRequest(BaseModel):
    """Input parameters for a remediation cost estimation."""

    model_config = ConfigDict(str_strip_whitespace=True)

    pollutant_type: str = Field(..., description="Pollutant: asbestos, pcb, lead, hap, radon, pfas")
    material_type: str = Field(
        ..., description="Material: flocage, dalle_vinyle, joint, peinture, enduit, isolation, colle, revetement, other"
    )
    condition: str = Field("degrade", description="Condition: bon, degrade, friable")
    surface_m2: float = Field(0.0, ge=0, description="Surface in m² (0 for forfait items like radon)")
    canton: str = Field("VD", description="Canton code: VD, GE, ZH, VS, BE, FR")
    accessibility: str = Field("normal", description="Access difficulty: facile, normal, difficile, tres_difficile")


class CostBreakdownItem(BaseModel):
    """One line of the cost breakdown."""

    label: str
    percentage: float
    amount_min: float
    amount_median: float
    amount_max: float


class CostPredictionResponse(BaseModel):
    """Full cost estimation result with fourchette and breakdown."""

    pollutant_type: str
    material_type: str
    surface_m2: float
    cost_min: float
    cost_median: float
    cost_max: float
    duration_days: int
    complexity: str
    method: str
    canton_coefficient: float
    accessibility_coefficient: float
    breakdown: list[CostBreakdownItem]
    disclaimer: str = "Estimation indicative basée sur les moyennes du marché suisse. Le devis final peut varier."
