"""Pydantic v2 schemas for Bulk Operations."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class BulkOperationType(StrEnum):
    """Supported bulk operation types."""

    generate_actions = "generate_actions"
    generate_unknowns = "generate_unknowns"
    evaluate_readiness = "evaluate_readiness"
    calculate_trust = "calculate_trust"
    run_dossier_agent = "run_dossier_agent"


class BulkOperationRequest(BaseModel):
    """Request body for bulk operations."""

    building_ids: list[str] = Field(..., min_length=1, max_length=50)
    operation_type: BulkOperationType

    model_config = ConfigDict(from_attributes=True)


class BulkBuildingResult(BaseModel):
    """Result for a single building within a bulk operation."""

    building_id: str
    status: str  # success / failed / skipped
    message: str = ""
    items_created: int | None = None

    model_config = ConfigDict(from_attributes=True)


class BulkOperationResult(BaseModel):
    """Aggregate result of a bulk operation."""

    operation_type: str
    total_buildings: int
    succeeded: int
    failed: int
    skipped: int
    results: list[BulkBuildingResult] = Field(default_factory=list)
    started_at: datetime
    completed_at: datetime

    model_config = ConfigDict(from_attributes=True)
