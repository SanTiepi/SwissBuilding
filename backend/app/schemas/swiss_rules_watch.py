"""SwissRules Watch + Commune Adapter schemas."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# ---- RuleSource ----


class RuleSourceCreate(BaseModel):
    source_code: str
    source_name: str
    source_url: str | None = None
    watch_tier: str  # daily|weekly|monthly|quarterly
    is_active: bool = True
    notes: str | None = None


class RuleSourceRead(BaseModel):
    id: UUID
    source_code: str
    source_name: str
    source_url: str | None
    watch_tier: str
    last_checked_at: datetime | None
    last_changed_at: datetime | None
    freshness_state: str
    change_types_detected: list[str] | None
    is_active: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---- RuleChangeEvent ----


class RuleChangeEventCreate(BaseModel):
    event_type: str  # new_rule|amended_rule|repealed_rule|portal_change|form_change|procedure_change
    title: str
    description: str | None = None
    impact_summary: str | None = None
    affects_buildings: bool = False


class RuleChangeEventRead(BaseModel):
    id: UUID
    source_id: UUID
    event_type: str
    title: str
    description: str | None
    impact_summary: str | None
    detected_at: datetime
    reviewed: bool
    reviewed_by_user_id: UUID | None
    reviewed_at: datetime | None
    review_notes: str | None
    affects_buildings: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReviewPayload(BaseModel):
    notes: str | None = None


# ---- CommunalAdapterProfile ----


class CommunalAdapterCreate(BaseModel):
    commune_code: str
    commune_name: str
    canton_code: str
    adapter_status: str = "draft"
    supports_procedure_projection: bool = False
    supports_rule_projection: bool = False
    fallback_mode: str = "canton_default"
    source_ids: list[str] | None = None
    notes: str | None = None


class CommunalAdapterRead(BaseModel):
    id: UUID
    commune_code: str
    commune_name: str
    canton_code: str
    adapter_status: str
    supports_procedure_projection: bool
    supports_rule_projection: bool
    fallback_mode: str
    source_ids: list[str] | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---- CommunalRuleOverride ----


class CommunalOverrideCreate(BaseModel):
    commune_code: str
    canton_code: str
    override_type: str
    rule_reference: str | None = None
    impact_summary: str
    review_required: bool = True
    confidence_level: str = "review_required"
    source_id: UUID | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    is_active: bool = True


class CommunalOverrideRead(BaseModel):
    id: UUID
    commune_code: str
    canton_code: str
    override_type: str
    rule_reference: str | None
    impact_summary: str
    review_required: bool
    confidence_level: str
    source_id: UUID | None
    effective_from: date | None
    effective_to: date | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---- Building commune context (read-only projection) ----


class BuildingCommuneContext(BaseModel):
    building_id: UUID
    city: str
    canton: str
    adapter: CommunalAdapterRead | None
    overrides: list[CommunalOverrideRead]
