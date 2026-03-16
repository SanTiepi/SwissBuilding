"""Pydantic schemas for expert review governance."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

VALID_DECISIONS = {"agree", "disagree", "override", "escalate", "defer"}
VALID_TARGET_TYPES = {
    "contradiction",
    "trust_score",
    "readiness",
    "unknown_issue",
    "sample",
    "diagnostic",
}
VALID_CONFIDENCE_LEVELS = {"high", "medium", "low"}


class ExpertReviewCreate(BaseModel):
    target_type: str
    target_id: uuid.UUID
    building_id: uuid.UUID
    decision: str
    confidence_level: str | None = None
    justification: str
    override_value: dict[str, Any] | None = None
    original_value: dict[str, Any] | None = None
    organization_id: uuid.UUID | None = None

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v: str) -> str:
        if v not in VALID_DECISIONS:
            raise ValueError(f"decision must be one of {sorted(VALID_DECISIONS)}")
        return v

    @field_validator("target_type")
    @classmethod
    def validate_target_type(cls, v: str) -> str:
        if v not in VALID_TARGET_TYPES:
            raise ValueError(f"target_type must be one of {sorted(VALID_TARGET_TYPES)}")
        return v

    @field_validator("confidence_level")
    @classmethod
    def validate_confidence_level(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_CONFIDENCE_LEVELS:
            raise ValueError(f"confidence_level must be one of {sorted(VALID_CONFIDENCE_LEVELS)}")
        return v


class ExpertReviewRead(BaseModel):
    id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    building_id: uuid.UUID
    decision: str
    confidence_level: str | None
    justification: str
    override_value: dict[str, Any] | None
    original_value: dict[str, Any] | None
    reviewed_by: uuid.UUID
    reviewer_role: str | None
    organization_id: uuid.UUID | None
    status: str
    superseded_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ExpertReviewList(BaseModel):
    items: list[ExpertReviewRead]
    total: int
