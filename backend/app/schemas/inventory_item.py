from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class InventoryItemCreate(BaseModel):
    building_id: UUID
    zone_id: UUID | None = None
    item_type: str  # hvac | boiler | elevator | fire_system | electrical_panel | solar_panel | heat_pump | ventilation | water_heater | garage_door | intercom | appliance | furniture | other
    name: str
    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = None
    installation_date: date | None = None
    warranty_end_date: date | None = None
    condition: str | None = None  # good | fair | poor | critical | unknown
    purchase_cost_chf: float | None = None
    replacement_cost_chf: float | None = None
    maintenance_contract_id: UUID | None = None
    notes: str | None = None
    source_type: str | None = None
    confidence: str | None = None
    source_ref: str | None = None


class InventoryItemUpdate(BaseModel):
    zone_id: UUID | None = None
    item_type: str | None = None
    name: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = None
    installation_date: date | None = None
    warranty_end_date: date | None = None
    condition: str | None = None
    purchase_cost_chf: float | None = None
    replacement_cost_chf: float | None = None
    maintenance_contract_id: UUID | None = None
    notes: str | None = None
    source_type: str | None = None
    confidence: str | None = None
    source_ref: str | None = None


class InventoryItemRead(BaseModel):
    id: UUID
    building_id: UUID
    zone_id: UUID | None
    item_type: str
    name: str
    manufacturer: str | None
    model: str | None
    serial_number: str | None
    installation_date: date | None
    warranty_end_date: date | None
    condition: str | None
    purchase_cost_chf: float | None
    replacement_cost_chf: float | None
    maintenance_contract_id: UUID | None
    notes: str | None
    source_type: str | None
    confidence: str | None
    source_ref: str | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InventoryItemListRead(BaseModel):
    id: UUID
    building_id: UUID
    item_type: str
    name: str
    manufacturer: str | None
    model: str | None
    condition: str | None
    serial_number: str | None

    model_config = ConfigDict(from_attributes=True)
