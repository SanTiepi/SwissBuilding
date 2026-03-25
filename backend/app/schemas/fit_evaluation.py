"""BatiConnect — Fit evaluation schema."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class FitEvidence(BaseModel):
    check: str
    result: bool
    detail: str


class FitResult(BaseModel):
    organization_id: UUID
    verdict: str  # good_fit | pilot_slice | walk_away
    reasons: list[str]
    evidence: list[FitEvidence]
