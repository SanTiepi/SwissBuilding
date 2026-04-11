"""Schemas for Programme N — Auto Compliance Scan output."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ComplianceFinding(BaseModel):
    """Single compliance finding from the scan."""

    model_config = ConfigDict(from_attributes=True)

    type: str  # non_conformity | warning | unknown
    rule: str  # e.g. "OTConst Art. 82"
    description: str
    severity: str  # critical | high | medium | low
    deadline: str | None = None
    references: list[str] = Field(default_factory=list)


class FindingsCount(BaseModel):
    non_conformities: int = 0
    warnings: int = 0
    unknowns: int = 0


class ComplianceScanResult(BaseModel):
    """Full compliance scan output for a building."""

    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    canton: str
    total_checks_executed: int
    findings_count: FindingsCount
    findings: list[ComplianceFinding] = Field(default_factory=list)
    compliance_score: float  # 0.0 - 1.0 = % rules passed
    scanned_at: datetime
