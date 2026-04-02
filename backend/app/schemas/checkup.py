"""Schemas for Check-up Bâtiment API"""

from uuid import UUID

from pydantic import BaseModel, Field


class CheckupCreateRequest(BaseModel):
    """Request to start a check-up session."""
    
    address: str | None = Field(None, description="Building address")
    egid: str | None = Field(None, description="Swiss building registration number (EGID)")


class CheckupSessionResponse(BaseModel):
    """Response from starting a check-up session."""
    
    id: UUID = Field(..., description="Unique session ID")
    address: str = Field(..., description="Enriched or provided address")
    egid: str | None = Field(None, description="Building EGID if identified")


class ObligationItem(BaseModel):
    """A regulatory obligation applicable to the building."""
    
    name: str = Field(..., description="Obligation name in French")
    description: str = Field(..., description="Detailed description")
    priority: str = Field(default="info", description="Priority level: info, warning, critical")
    regulation: str | None = Field(None, description="Source regulation (e.g., 'OTConst', 'CFST')")


class FindingItem(BaseModel):
    """A key issue identified during the check-up."""
    
    title: str = Field(..., description="Finding title in French")
    description: str = Field(..., description="Detailed description")
    severity: str = Field(default="medium", description="Severity level")


class CheckupScoreResponse(BaseModel):
    """Risk score and obligations for a building check-up."""
    
    score_letter: str = Field(..., description="Risk rating A-F (A=best, F=worst)")
    raw_score: float = Field(..., ge=0, le=1, description="Numeric risk score 0-1")
    completeness_score: float = Field(..., ge=0, le=1, description="Data completeness 0-1")
    document_count: int = Field(..., ge=0, description="Number of documents analyzed")
    construction_year: int | None = Field(None, description="Building construction year")
    
    obligations: list[ObligationItem] = Field(default_factory=list)
    findings: list[FindingItem] = Field(default_factory=list)
    
    explanation: str | None = Field(None, description="Textual explanation of the score")
