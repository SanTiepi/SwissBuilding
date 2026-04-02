"""Pydantic schemas for Building Passport."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PassportGradeBreakdown(BaseModel):
    """Breakdown of metrics contributing to a grade."""

    category: str
    grade: str
    score: float = Field(..., ge=0, le=100)
    components: dict = Field(default_factory=dict)


class BuildingPassportBase(BaseModel):
    """Base schema for building passport."""

    structural_grade: str = Field(..., pattern="^[A-F]$")
    energy_grade: str = Field(..., pattern="^[A-F]$")
    safety_grade: str = Field(..., pattern="^[A-F]$")
    environmental_grade: str = Field(..., pattern="^[A-F]$")
    compliance_grade: str = Field(..., pattern="^[A-F]$")
    readiness_grade: str = Field(..., pattern="^[A-F]$")
    overall_grade: str = Field(..., pattern="^[A-F]$")


class BuildingPassportCreate(BuildingPassportBase):
    """Create building passport."""

    metadata: dict | None = None


class BuildingPassportUpdate(BaseModel):
    """Update building passport."""

    structural_grade: str | None = Field(None, pattern="^[A-F]$")
    energy_grade: str | None = Field(None, pattern="^[A-F]$")
    safety_grade: str | None = Field(None, pattern="^[A-F]$")
    environmental_grade: str | None = Field(None, pattern="^[A-F]$")
    compliance_grade: str | None = Field(None, pattern="^[A-F]$")
    readiness_grade: str | None = Field(None, pattern="^[A-F]$")
    overall_grade: str | None = Field(None, pattern="^[A-F]$")
    metadata: dict | None = None


class BuildingPassportRead(BuildingPassportBase):
    """Read building passport."""

    id: UUID
    building_id: UUID
    version: int
    metadata: dict | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BuildingPassportHistoryItem(BuildingPassportRead):
    """Single passport version in history."""
    pass


class BuildingPassportHistory(BaseModel):
    """Historical passport versions."""

    building_id: UUID
    current: BuildingPassportRead
    history: list[BuildingPassportHistoryItem] = Field(default_factory=list)
    total_versions: int = 0
