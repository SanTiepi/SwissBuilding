from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BuildingCreate(BaseModel):
    egrid: str | None = None
    egid: int | None = None
    official_id: str | None = None
    address: str
    postal_code: str = Field(pattern=r"^\d{4}$")
    city: str
    canton: str = Field(min_length=2, max_length=2)
    municipality_ofs: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    parcel_number: str | None = None
    construction_year: int | None = None
    renovation_year: int | None = None
    building_type: str
    floors_above: int | None = None
    floors_below: int | None = None
    surface_area_m2: float | None = None
    volume_m3: float | None = None
    owner_id: UUID | None = None
    source_dataset: str | None = None
    source_imported_at: datetime | None = None
    source_metadata_json: dict[str, Any] | None = None


class BuildingUpdate(BaseModel):
    address: str | None = None
    postal_code: str | None = None
    city: str | None = None
    canton: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    construction_year: int | None = None
    renovation_year: int | None = None
    building_type: str | None = None
    floors_above: int | None = None
    floors_below: int | None = None
    surface_area_m2: float | None = None
    volume_m3: float | None = None
    owner_id: UUID | None = None
    status: str | None = None


class BuildingRead(BaseModel):
    id: UUID
    egrid: str | None
    egid: int | None
    official_id: str | None
    address: str
    postal_code: str
    city: str
    canton: str
    municipality_ofs: int | None
    latitude: float | None
    longitude: float | None
    parcel_number: str | None
    construction_year: int | None
    renovation_year: int | None
    building_type: str
    floors_above: int | None
    floors_below: int | None
    surface_area_m2: float | None
    volume_m3: float | None
    owner_id: UUID | None
    created_by: UUID
    status: str
    source_dataset: str | None
    source_imported_at: datetime | None
    source_metadata_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime
    risk_scores: RiskScoreRead | None = None

    model_config = ConfigDict(from_attributes=True)


class BuildingListRead(BaseModel):
    id: UUID
    address: str
    postal_code: str
    city: str
    canton: str
    construction_year: int | None
    building_type: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Resolve forward reference
from app.schemas.risk import RiskScoreRead  # noqa: E402

BuildingRead.model_rebuild()
