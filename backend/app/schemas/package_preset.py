"""Adoption Loops — Package preset and embed token schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PresetRead(BaseModel):
    id: UUID
    preset_code: str
    title: str
    description: str | None
    audience_type: str
    included_sections: list[str] | None
    excluded_sections: list[str] | None
    unknown_sections: list[str] | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PresetPreview(BaseModel):
    preset_code: str
    building_id: UUID
    title: str
    audience_type: str
    included: list[str]
    excluded: list[str]
    unknown: list[str]


class EmbedTokenCreate(BaseModel):
    viewer_profile_id: UUID | None = None
    scope: dict | None = None  # {sections: [str], max_views: int|null, expires_at: str|null}


class EmbedTokenRead(BaseModel):
    id: UUID
    building_id: UUID
    token: str
    viewer_profile_id: UUID | None
    scope: dict | None
    created_by_user_id: UUID
    view_count: int
    last_viewed_at: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmbedPublicView(BaseModel):
    """Public view returned when accessing an embed token (no auth)."""

    building_id: UUID
    sections: list[str]
    viewer_type: str | None = None
    requires_acknowledgement: bool = False


class ExternalViewerProfileRead(BaseModel):
    id: UUID
    name: str
    viewer_type: str
    allowed_sections: list[str] | None
    requires_acknowledgement: bool
    notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
