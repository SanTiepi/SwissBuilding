"""Pack impact simulation schemas."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PackImpactType(StrEnum):
    invalidated = "invalidated"
    degraded = "degraded"
    unaffected = "unaffected"
    improved = "improved"


class AffectedPack(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pack_id: UUID | None = None
    pack_type: str
    impact_type: PackImpactType
    reason: str
    affected_sections: list[str] = []
    current_trust_score: float | None = None
    projected_trust_score: float | None = None
    remediation_actions: list[str] = []


class PackImpactSummary(BaseModel):
    invalidated_count: int = 0
    degraded_count: int = 0
    unaffected_count: int = 0
    improved_count: int = 0


class PackImpactSimulateRequest(BaseModel):
    intervention_ids: list[UUID]


class PackImpactSimulation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    simulation_date: datetime
    interventions_analyzed: int
    packs_analyzed: int
    affected_packs: list[AffectedPack] = []
    summary: PackImpactSummary
    risk_level: str  # low | medium | high | critical
    recommendations: list[str] = []
