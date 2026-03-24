from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UnitCreate(BaseModel):
    building_id: UUID
    unit_type: str  # residential | commercial | parking | storage | office | common_area
    reference_code: str
    name: str | None = None
    floor: int | None = None
    surface_m2: float | None = None
    rooms: float | None = None
    status: str = "active"  # active | vacant | renovating | decommissioned
    notes: str | None = None


class UnitUpdate(BaseModel):
    unit_type: str | None = None
    reference_code: str | None = None
    name: str | None = None
    floor: int | None = None
    surface_m2: float | None = None
    rooms: float | None = None
    status: str | None = None
    notes: str | None = None


class UnitRead(BaseModel):
    id: UUID
    building_id: UUID
    unit_type: str
    reference_code: str
    name: str | None
    floor: int | None
    surface_m2: float | None
    rooms: float | None
    status: str
    notes: str | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UnitListRead(BaseModel):
    id: UUID
    building_id: UUID
    unit_type: str
    reference_code: str
    name: str | None
    floor: int | None
    surface_m2: float | None
    rooms: float | None
    status: str

    model_config = ConfigDict(from_attributes=True)


class UnitZoneCreate(BaseModel):
    unit_id: UUID
    zone_id: UUID


class UnitZoneRead(BaseModel):
    id: UUID
    unit_id: UUID
    zone_id: UUID

    model_config = ConfigDict(from_attributes=True)
