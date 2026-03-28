"""BatiConnect — Partner Exchange Contract schemas."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PartnerExchangeContractCreate(BaseModel):
    """Create a new partner exchange contract."""

    partner_org_id: UUID
    our_org_id: UUID
    contract_type: str = Field(
        ...,
        pattern=r"^(data_provider|data_consumer|bidirectional|submission_partner|exchange_partner)$",
    )
    allowed_operations: list[str] = Field(default_factory=list)
    api_access_level: str = Field(
        default="none",
        pattern=r"^(none|read_only|submit|full_partner)$",
    )
    allowed_endpoints: list[str] | None = None
    data_sharing_scope: str = Field(
        default="none",
        pattern=r"^(building_specific|case_specific|portfolio|none)$",
    )
    redaction_profile: str = Field(
        default="none",
        pattern=r"^(none|financial|personal|full)$",
    )
    minimum_trust_level: str = Field(
        default="unknown",
        pattern=r"^(unknown|weak|adequate|strong)$",
    )
    conformance_profile_id: UUID | None = None
    status: str = Field(
        default="draft",
        pattern=r"^(draft|active|suspended|terminated)$",
    )
    start_date: date
    end_date: date | None = None
    terms_summary: str | None = None


class PartnerExchangeContractUpdate(BaseModel):
    """Update an existing partner exchange contract."""

    contract_type: str | None = None
    allowed_operations: list[str] | None = None
    api_access_level: str | None = None
    allowed_endpoints: list[str] | None = None
    data_sharing_scope: str | None = None
    redaction_profile: str | None = None
    minimum_trust_level: str | None = None
    conformance_profile_id: UUID | None = None
    status: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    terms_summary: str | None = None


class PartnerExchangeContractRead(BaseModel):
    """Read representation of a partner exchange contract."""

    id: UUID
    partner_org_id: UUID
    our_org_id: UUID
    contract_type: str
    allowed_operations: list[str]
    api_access_level: str
    allowed_endpoints: list[str] | None
    data_sharing_scope: str
    redaction_profile: str
    minimum_trust_level: str
    conformance_profile_id: UUID | None
    status: str
    start_date: date
    end_date: date | None
    terms_summary: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PartnerExchangeEventRead(BaseModel):
    """Read representation of a partner exchange event."""

    id: UUID
    contract_id: UUID
    event_type: str
    detail: dict | None
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PartnerAccessValidation(BaseModel):
    """Result of validating partner access."""

    allowed: bool
    reason: str
    contract_id: UUID | None = None


class PartnerSubmissionValidation(BaseModel):
    """Result of validating a partner submission."""

    valid: bool
    issues: list[dict] = Field(default_factory=list)
    conformance_result: dict | None = None
    contract_id: UUID | None = None
