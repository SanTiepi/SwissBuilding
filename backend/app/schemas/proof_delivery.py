"""BatiConnect - Proof Delivery schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProofDeliveryCreate(BaseModel):
    building_id: UUID | None = None  # optional: path param takes precedence
    target_type: str  # document | pack | authority_pack | transfer_package | diagnostic_publication
    target_id: UUID
    audience: str  # owner | authority | insurer | lender | fiduciary | contractor | other
    recipient_org_id: UUID | None = None
    recipient_email: str | None = None
    delivery_method: str  # email | download | api | postal | handoff
    content_hash: str | None = None  # computed by service if not provided
    content_version: int | None = None
    notes: str | None = None
    source_type: str | None = None
    confidence: str | None = None
    source_ref: str | None = None


class ProofDeliveryRead(BaseModel):
    id: UUID
    building_id: UUID
    target_type: str
    target_id: UUID
    audience: str
    recipient_org_id: UUID | None
    recipient_email: str | None
    delivery_method: str
    status: str
    sent_at: datetime | None
    delivered_at: datetime | None
    viewed_at: datetime | None
    acknowledged_at: datetime | None
    content_hash: str | None
    content_version: int | None
    error_message: str | None
    notes: str | None
    source_type: str | None
    confidence: str | None
    source_ref: str | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProofDeliveryTransition(BaseModel):
    """Payload for status transition endpoints (sent/delivered/viewed/acknowledged/failed)."""

    notes: str | None = None
    error_message: str | None = None  # only used for failed transition
