"""BatiConnect — RecurringService schemas."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RecurringServiceCreate(BaseModel):
    service_type: str  # maintenance | cleaning | security | elevator | heating | garden | pest_control | fire_inspection | chimney | energy_monitoring | waste | other
    provider_name: str
    provider_contact: str | None = None
    provider_org_id: UUID | None = None
    contract_reference: str | None = None
    start_date: date
    end_date: date | None = None
    renewal_type: str = "auto"  # auto | manual | fixed_term
    notice_period_days: int | None = None
    annual_cost_chf: float | None = None
    payment_frequency: str | None = None  # monthly | quarterly | annual
    frequency: str  # weekly | monthly | quarterly | semi_annual | annual | on_demand
    last_service_date: date | None = None
    next_service_date: date | None = None
    status: str = "active"
    notes: str | None = None


class RecurringServiceUpdate(BaseModel):
    service_type: str | None = None
    provider_name: str | None = None
    provider_contact: str | None = None
    provider_org_id: UUID | None = None
    contract_reference: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    renewal_type: str | None = None
    notice_period_days: int | None = None
    annual_cost_chf: float | None = None
    payment_frequency: str | None = None
    frequency: str | None = None
    last_service_date: date | None = None
    next_service_date: date | None = None
    status: str | None = None
    notes: str | None = None


class RecurringServiceRead(BaseModel):
    id: UUID
    building_id: UUID
    organization_id: UUID
    service_type: str
    provider_name: str
    provider_contact: str | None
    provider_org_id: UUID | None
    contract_reference: str | None
    start_date: date
    end_date: date | None
    renewal_type: str
    notice_period_days: int | None
    annual_cost_chf: float | None
    payment_frequency: str | None
    frequency: str
    last_service_date: date | None
    next_service_date: date | None
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ServicePerformedRequest(BaseModel):
    performed_date: date
    notes: str | None = None
