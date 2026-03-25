"""Finance Surfaces — Audience Pack schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# --- Create / Update ---


class AudiencePackCreate(BaseModel):
    building_id: UUID | None = None  # overridden by path param
    pack_type: str  # insurer | fiduciary | transaction | lender


# --- Read ---


class AudiencePackRead(BaseModel):
    id: UUID
    building_id: UUID
    pack_type: str
    pack_version: int
    status: str
    generated_by_user_id: UUID | None
    sections: dict[str, Any]
    unknowns_summary: list[dict[str, Any]] | None
    contradictions_summary: list[dict[str, Any]] | None
    residual_risk_summary: list[dict[str, Any]] | None
    trust_refs: list[dict[str, Any]] | None
    proof_refs: list[dict[str, Any]] | None
    content_hash: str
    generated_at: datetime
    superseded_by_id: UUID | None
    created_at: datetime
    updated_at: datetime
    caveats: list[CaveatEvaluation] | None = None

    model_config = ConfigDict(from_attributes=True)


class AudiencePackListRead(BaseModel):
    id: UUID
    building_id: UUID
    pack_type: str
    pack_version: int
    status: str
    generated_at: datetime
    content_hash: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Redaction Profile ---


class RedactionProfileRead(BaseModel):
    id: UUID
    profile_code: str
    audience_type: str
    allowed_sections: list[str]
    blocked_sections: list[str]
    redacted_fields: list[dict[str, Any]] | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Caveat Profile ---


class CaveatProfileRead(BaseModel):
    id: UUID
    audience_type: str
    caveat_type: str
    template_text: str
    severity: str
    applies_when: dict[str, Any]
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CaveatEvaluation(BaseModel):
    caveat_type: str
    severity: str
    message: str
    applies_when: dict[str, Any]


# --- Pack Comparison ---


class PackComparisonView(BaseModel):
    pack_1: AudiencePackRead
    pack_2: AudiencePackRead
    section_diff: dict[str, Any]  # {section_name: {only_in_1: [...], only_in_2: [...], changed: [...]}}
    caveat_diff: dict[str, Any]  # {only_in_1: [...], only_in_2: [...]}
