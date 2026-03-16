"""Pydantic v2 schemas for Contractor Matching."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MatchReason(BaseModel):
    """A single reason contributing to a contractor match score."""

    factor: str
    score: float
    detail: str

    model_config = ConfigDict(from_attributes=True)


class ContractorMatch(BaseModel):
    """A ranked contractor organization with match score."""

    organization_id: UUID
    organization_name: str
    total_score: float
    suva_recognized: bool
    fach_approved: bool
    canton: str | None = None
    city: str | None = None
    match_reasons: list[MatchReason]

    model_config = ConfigDict(from_attributes=True)


class ContractorMatchResult(BaseModel):
    """Result of contractor matching for a building."""

    building_id: UUID
    pollutants_found: list[str]
    contractors: list[ContractorMatch]

    model_config = ConfigDict(from_attributes=True)


class CertificationRequirement(BaseModel):
    """A single certification requirement derived from building diagnostics."""

    certification: str
    reason: str
    pollutant: str | None = None
    legal_ref: str | None = None

    model_config = ConfigDict(from_attributes=True)


class RequiredCertificationsResult(BaseModel):
    """All certifications required for a building."""

    building_id: UUID
    cfst_work_category: str | None = None
    suva_certifications: list[CertificationRequirement]
    special_equipment: list[str]
    regulatory_notifications: list[str]

    model_config = ConfigDict(from_attributes=True)


class PollutantNeed(BaseModel):
    """Workforce needs for a single pollutant."""

    pollutant: str
    sample_count: int
    max_risk_level: str
    specialists_needed: int
    estimated_days: float
    requires_safety_crew: bool

    model_config = ConfigDict(from_attributes=True)


class ContractorNeedsResult(BaseModel):
    """Workforce sizing estimate for a building."""

    building_id: UUID
    pollutant_needs: list[PollutantNeed]
    total_specialists: int
    total_estimated_days: float
    safety_crew_required: bool
    parallel_possible: bool
    work_sequence_recommendation: str

    model_config = ConfigDict(from_attributes=True)


class BuildingDemand(BaseModel):
    """Contractor demand for a single building."""

    building_id: UUID
    address: str
    contractor_days: float
    certifications_needed: list[str]

    model_config = ConfigDict(from_attributes=True)


class CertificationDemandEntry(BaseModel):
    """Distribution of certification demand."""

    certification: str
    building_count: int

    model_config = ConfigDict(from_attributes=True)


class PortfolioContractorDemandResult(BaseModel):
    """Aggregate contractor demand across an organization's buildings."""

    organization_id: UUID
    total_buildings: int
    total_contractor_days: float
    certification_demand: list[CertificationDemandEntry]
    buildings: list[BuildingDemand]

    model_config = ConfigDict(from_attributes=True)
