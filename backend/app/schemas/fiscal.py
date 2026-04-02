"""Fiscal deduction and tax simulation schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RenovationItem(BaseModel):
    """A single renovation item in a simulation."""

    type: str = Field(
        ...,
        description="Renovation type: energy, amiante, seismic, facade, sanitary, roof",
    )
    cost: float = Field(..., gt=0, description="Total cost in CHF")


class FiscalSimulationRequest(BaseModel):
    """Request to simulate fiscal deductions for renovations."""

    renovations: list[RenovationItem] = Field(
        ..., min_items=1, description="List of renovation items"
    )
    fiscal_years: int = Field(
        5, ge=1, le=20, description="Number of fiscal years to project"
    )


class DeductionBreakdown(BaseModel):
    """Deduction calculation result for a single renovation."""

    canton: str
    renovation_type: str
    total_cost: float
    deduction_rate: float
    deduction_amount: float
    max_deduction: float
    tax_savings_estimate: float
    fiscal_year: int
    notes: str


class YearlyBreakdown(BaseModel):
    """Yearly deduction projection."""

    fiscal_year: int
    year_deduction: float
    year_tax_savings: float


class FiscalSimulationResponse(BaseModel):
    """Response from fiscal deduction simulation."""

    canton: str
    total_renovation_cost: float
    total_deduction: float
    total_tax_savings_estimate: float
    yearly_breakdown: list[YearlyBreakdown]
    fiscal_years_projected: int
    notes: str
