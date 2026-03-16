"""Pydantic v2 schemas for the Access Control service."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AccessLevel(StrEnum):
    unrestricted = "unrestricted"
    restricted_ppe = "restricted_ppe"
    restricted_authorized = "restricted_authorized"
    prohibited = "prohibited"


class MaskType(StrEnum):
    ffp2 = "ffp2"
    ffp3 = "ffp3"
    full_face_p3 = "full_face_p3"
    supplied_air = "supplied_air"


class SuitType(StrEnum):
    disposable = "disposable"
    type_5_6 = "type_5_6"
    type_3_4 = "type_3_4"


class SUVACertLevel(StrEnum):
    none = "none"
    basic = "basic"
    advanced = "advanced"
    specialist = "specialist"


class PPERequirement(BaseModel):
    """PPE requirements for a zone."""

    mask_type: MaskType | None = None
    suit_type: SuitType | None = None
    gloves_required: bool = False
    safety_goggles: bool = False
    description: str = ""

    model_config = ConfigDict(from_attributes=True)


class SignageRequirement(BaseModel):
    """Signage to display at a zone entrance."""

    sign_type: str
    text_fr: str
    mandatory: bool = True

    model_config = ConfigDict(from_attributes=True)


class ZoneAccessRestriction(BaseModel):
    """Access restriction for a single zone."""

    zone_id: UUID
    zone_name: str
    zone_type: str
    floor_number: int | None = None
    access_level: AccessLevel
    reason: str
    pollutant_types: list[str] = []
    ppe: PPERequirement | None = None
    signage: list[SignageRequirement] = []

    model_config = ConfigDict(from_attributes=True)


class BuildingAccessRestrictions(BaseModel):
    """Per-zone access rules for a building."""

    building_id: UUID
    zones: list[ZoneAccessRestriction]
    total_zones: int = 0
    restricted_zones: int = 0
    prohibited_zones: int = 0
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SafeZone(BaseModel):
    """A zone confirmed safe for unrestricted access."""

    zone_id: UUID
    zone_name: str
    zone_type: str
    floor_number: int | None = None
    reason: str

    model_config = ConfigDict(from_attributes=True)


class BuildingSafeZones(BaseModel):
    """Zones confirmed safe for unrestricted access in a building."""

    building_id: UUID
    safe_zones: list[SafeZone]
    restricted_zones_count: int = 0
    total_zones: int = 0
    safe_ratio: float = Field(ge=0.0, le=1.0, default=1.0)
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ZonePermitRequirement(BaseModel):
    """Permit/authorization requirements for a restricted zone."""

    zone_id: UUID
    zone_name: str
    zone_type: str
    access_level: AccessLevel
    suva_cert_level: SUVACertLevel = SUVACertLevel.none
    medical_clearance_required: bool = False
    training_requirements: list[str] = []
    escort_required: bool = False
    escort_description: str | None = None
    pollutant_types: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class BuildingPermitRequirements(BaseModel):
    """All permit/authorization requirements for entering restricted zones."""

    building_id: UUID
    zones: list[ZonePermitRequirement]
    zones_requiring_permits: int = 0
    max_suva_cert_level: SUVACertLevel = SUVACertLevel.none
    any_medical_clearance: bool = False
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BuildingAccessSummary(BaseModel):
    """Access summary for a single building in portfolio view."""

    building_id: UUID
    address: str
    city: str
    total_zones: int = 0
    restricted_zones: int = 0
    prohibited_zones: int = 0
    fully_accessible: bool = True

    model_config = ConfigDict(from_attributes=True)


class PortfolioAccessStatus(BaseModel):
    """Org-level access compliance overview."""

    organization_id: UUID
    total_buildings: int = 0
    buildings_with_restrictions: int = 0
    buildings_fully_accessible: int = 0
    total_restricted_zones: int = 0
    access_compliance_rate: float = Field(ge=0.0, le=1.0, default=1.0)
    buildings: list[BuildingAccessSummary] = []
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)
