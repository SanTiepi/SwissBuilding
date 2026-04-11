"""Permit workflow schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PermitCreate(BaseModel):
    """Create a new permit."""

    permit_type: str  # renovation | subsidy | declaration
    issued_date: datetime
    expiry_date: datetime
    subsidy_amount: float | None = None
    notes: str | None = None


class PermitUpdate(BaseModel):
    """Update permit status or dates."""

    status: str | None = None
    issued_date: datetime | None = None
    expiry_date: datetime | None = None
    subsidy_amount: float | None = None
    notes: str | None = None


class PermitRead(BaseModel):
    """Read permit details."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    building_id: UUID
    permit_type: str
    status: str
    issued_date: datetime
    expiry_date: datetime
    subsidy_amount: float | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class PermitAlert(BaseModel):
    """Alert for expiring permits."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    building_id: UUID
    permit_type: str
    status: str
    issued_date: datetime
    expiry_date: datetime
    days_until_expiry: int
    alert_level: str  # green | amber | red
