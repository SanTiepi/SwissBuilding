import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# RegulatoryPack schemas
# ---------------------------------------------------------------------------


class RegulatoryPackCreate(BaseModel):
    pollutant_type: str
    version: str = "1.0"
    is_active: bool = True
    threshold_value: float | None = None
    threshold_unit: str | None = None
    threshold_action: str | None = None
    risk_year_start: int | None = None
    risk_year_end: int | None = None
    base_probability: float | None = None
    work_categories_json: dict | list | None = None
    waste_classification_json: dict | list | None = None
    legal_reference: str | None = None
    legal_url: str | None = None
    description_fr: str | None = None
    description_de: str | None = None
    description_it: str | None = None
    description_en: str | None = None
    notification_required: bool = False
    notification_authority: str | None = None
    notification_delay_days: int | None = None


class RegulatoryPackUpdate(BaseModel):
    pollutant_type: str | None = None
    version: str | None = None
    is_active: bool | None = None
    threshold_value: float | None = None
    threshold_unit: str | None = None
    threshold_action: str | None = None
    risk_year_start: int | None = None
    risk_year_end: int | None = None
    base_probability: float | None = None
    work_categories_json: dict | list | None = None
    waste_classification_json: dict | list | None = None
    legal_reference: str | None = None
    legal_url: str | None = None
    description_fr: str | None = None
    description_de: str | None = None
    description_it: str | None = None
    description_en: str | None = None
    notification_required: bool | None = None
    notification_authority: str | None = None
    notification_delay_days: int | None = None


class RegulatoryPackRead(BaseModel):
    id: uuid.UUID
    jurisdiction_id: uuid.UUID
    pollutant_type: str
    version: str | None
    is_active: bool
    threshold_value: float | None
    threshold_unit: str | None
    threshold_action: str | None
    risk_year_start: int | None
    risk_year_end: int | None
    base_probability: float | None
    work_categories_json: dict | list | None
    waste_classification_json: dict | list | None
    legal_reference: str | None
    legal_url: str | None
    description_fr: str | None
    description_de: str | None
    description_it: str | None
    description_en: str | None
    notification_required: bool
    notification_authority: str | None
    notification_delay_days: int | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Jurisdiction schemas
# ---------------------------------------------------------------------------


class JurisdictionCreate(BaseModel):
    code: str
    name: str
    parent_id: uuid.UUID | None = None
    level: str
    country_code: str | None = None
    is_active: bool = True
    metadata_json: dict | None = None


class JurisdictionUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    parent_id: uuid.UUID | None = None
    level: str | None = None
    country_code: str | None = None
    is_active: bool | None = None
    metadata_json: dict | None = None


class JurisdictionRead(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    parent_id: uuid.UUID | None
    level: str
    country_code: str | None
    is_active: bool
    metadata_json: dict | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JurisdictionReadWithPacks(JurisdictionRead):
    regulatory_packs: list[RegulatoryPackRead] = []
