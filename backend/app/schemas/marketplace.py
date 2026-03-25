"""BatiConnect — Marketplace schemas (CompanyProfile, Verification, Subscription)."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# ---- CompanyProfile ----


class CompanyProfileCreate(BaseModel):
    organization_id: UUID
    company_name: str
    legal_form: str | None = None
    uid_number: str | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    canton: str | None = None
    contact_email: str
    contact_phone: str | None = None
    website: str | None = None
    description: str | None = None
    work_categories: list[str] = []
    certifications: list[dict] | None = None
    regions_served: list[str] | None = None
    employee_count: int | None = None
    years_experience: int | None = None
    insurance_info: dict | None = None


class CompanyProfileUpdate(BaseModel):
    company_name: str | None = None
    legal_form: str | None = None
    uid_number: str | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    canton: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    website: str | None = None
    description: str | None = None
    work_categories: list[str] | None = None
    certifications: list[dict] | None = None
    regions_served: list[str] | None = None
    employee_count: int | None = None
    years_experience: int | None = None
    insurance_info: dict | None = None
    is_active: bool | None = None


class CompanyProfileRead(BaseModel):
    id: UUID
    organization_id: UUID
    company_name: str
    legal_form: str | None
    uid_number: str | None
    address: str | None
    city: str | None
    postal_code: str | None
    canton: str | None
    contact_email: str
    contact_phone: str | None
    website: str | None
    description: str | None
    work_categories: list[str]
    certifications: list[dict] | None
    regions_served: list[str] | None
    employee_count: int | None
    years_experience: int | None
    insurance_info: dict | None
    is_active: bool
    profile_completeness: float | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---- CompanyVerification ----


class CompanyVerificationCreate(BaseModel):
    company_profile_id: UUID
    verification_type: str = "initial"  # initial | renewal | spot_check


class VerificationDecision(BaseModel):
    status: str  # approved | rejected
    checks_performed: list[dict] | None = None
    rejection_reason: str | None = None
    valid_until: date | None = None
    notes: str | None = None


class CompanyVerificationRead(BaseModel):
    id: UUID
    company_profile_id: UUID
    status: str
    verified_by_user_id: UUID | None
    verified_at: datetime | None
    verification_type: str
    checks_performed: list[dict] | None
    rejection_reason: str | None
    valid_until: date | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---- CompanySubscription ----


class CompanySubscriptionCreate(BaseModel):
    plan_type: str  # free_trial | basic | professional | premium
    started_at: datetime
    expires_at: datetime | None = None
    billing_reference: str | None = None
    notes: str | None = None


class CompanySubscriptionUpdate(BaseModel):
    status: str | None = None  # active | expired | suspended | cancelled
    plan_type: str | None = None
    expires_at: datetime | None = None
    billing_reference: str | None = None
    notes: str | None = None


class CompanySubscriptionRead(BaseModel):
    id: UUID
    company_profile_id: UUID
    plan_type: str
    status: str
    started_at: datetime
    expires_at: datetime | None
    is_network_eligible: bool
    billing_reference: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---- Network Eligibility ----


class NetworkEligibilityCheck(BaseModel):
    company_profile_id: UUID
    is_eligible: bool
    is_verified: bool
    has_active_subscription: bool
    verification_status: str | None = None
    subscription_status: str | None = None
