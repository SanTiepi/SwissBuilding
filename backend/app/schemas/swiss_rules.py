"""Typed schemas for the SwissRules regulatory spine bootstrap."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class JurisdictionLevel(StrEnum):
    FEDERAL = "federal"
    INTERCANTONAL = "intercantonal"
    CANTONAL = "cantonal"
    COMMUNAL = "communal"
    UTILITY = "utility"
    PRIVATE_STANDARD = "private_standard"


class NormativeForce(StrEnum):
    BINDING_LAW = "binding_law"
    BINDING_REGULATION = "binding_regulation"
    OFFICIAL_EXECUTION_GUIDELINE = "official_execution_guideline"
    INTERCANTONAL_STANDARD = "intercantonal_standard"
    PRIVATE_STANDARD = "private_standard"
    LABEL = "label"


class SourceKind(StrEnum):
    LEGAL_TEXT = "legal_text"
    PORTAL = "portal"
    GUIDELINE = "guideline"
    DIRECTIVE = "directive"
    STANDARD = "standard"
    LABEL = "label"
    DATASET = "dataset"


class WatchCadence(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    EVENT_DRIVEN = "event_driven"


class ReviewStatus(StrEnum):
    DRAFT = "draft"
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PUBLISHED = "published"


class ApplicabilityStatus(StrEnum):
    APPLICABLE = "applicable"
    NOT_APPLICABLE = "not_applicable"
    MANUAL_REVIEW = "manual_review"


class ChangeType(StrEnum):
    NEW_RULE = "new_rule"
    AMENDED_RULE = "amended_rule"
    REPEALED_RULE = "repealed_rule"
    PORTAL_CHANGE = "portal_change"
    FORM_CHANGE = "form_change"
    PROCEDURE_CHANGE = "procedure_change"


class ChangeSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Jurisdiction(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    level: JurisdictionLevel
    parent_code: str | None = None
    country_code: str = "CH"
    notes: str | None = None
    is_operational: bool = True


class AuthorityRegistry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    jurisdiction_code: str
    authority_type: str
    portal_url: str
    contact_url: str | None = None
    filing_modes: list[str] = Field(default_factory=list)
    notes: str | None = None


class RuleSource(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_id: str
    title: str
    url: str
    jurisdiction_code: str
    publisher: str
    normative_force: NormativeForce
    source_kind: SourceKind
    language: str = "fr"
    cadence: WatchCadence = WatchCadence.WEEKLY
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None


class RuleSnapshot(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    snapshot_id: UUID = Field(default_factory=uuid4)
    source_id: str
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    content_hash: str
    review_status: ReviewStatus = ReviewStatus.DRAFT
    excerpt: str | None = None
    effective_from: datetime | None = None
    effective_to: datetime | None = None


class RuleTemplate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    title: str
    summary: str
    jurisdiction_levels: list[JurisdictionLevel]
    source_ids: list[str]
    normative_force: NormativeForce
    domain_tags: list[str] = Field(default_factory=list)
    required_project_kinds: list[str] = Field(default_factory=list)
    required_pollutants: list[str] = Field(default_factory=list)
    required_waste_categories: list[str] = Field(default_factory=list)
    required_building_flags: list[str] = Field(default_factory=list)
    manual_review_flags: list[str] = Field(default_factory=list)
    output_requirement_codes: list[str] = Field(default_factory=list)
    default_procedure_codes: list[str] = Field(default_factory=list)
    default_authority_codes: list[str] = Field(default_factory=list)
    integration_targets: list[str] = Field(default_factory=list)
    review_status: ReviewStatus = ReviewStatus.DRAFT


class RequirementTemplate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    title: str
    summary: str
    source_rule_codes: list[str]
    evidence_type: str
    responsible_role: str
    due_hint: str | None = None
    legal_basis_source_ids: list[str] = Field(default_factory=list)
    integration_target: str
    notes: str | None = None


class ProcedureStepTemplate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    step_key: str
    title: str
    summary: str
    blocking: bool = False


class ProcedureTemplate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    title: str
    summary: str
    jurisdiction_code: str
    authority_code: str
    procedure_type: str
    source_rule_codes: list[str]
    steps: list[ProcedureStepTemplate]
    integration_target: str
    review_status: ReviewStatus = ReviewStatus.DRAFT


class BuildingContext(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    canton: str
    commune: str | None = None
    outside_building_zone: bool = False
    protected_building: bool = False
    radon_risk: bool = False
    building_category: str = "standard"
    usage: str = "residential"
    special_case_tags: list[str] = Field(default_factory=list)


class ProjectContext(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_kind: str
    pollutants_detected: list[str] = Field(default_factory=list)
    waste_categories: list[str] = Field(default_factory=list)
    requires_permit: bool = False
    touches_structure: bool = False
    involves_demolition: bool = False
    public_facing: bool = False
    special_case_tags: list[str] = Field(default_factory=list)


class ApplicabilityEvaluation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rule_code: str
    status: ApplicabilityStatus
    reasons: list[str] = Field(default_factory=list)
    matched_conditions: list[str] = Field(default_factory=list)
    required_requirement_codes: list[str] = Field(default_factory=list)
    required_procedure_codes: list[str] = Field(default_factory=list)
    authority_codes: list[str] = Field(default_factory=list)
    integration_targets: list[str] = Field(default_factory=list)
    manual_review_reasons: list[str] = Field(default_factory=list)


class LegalChangeEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: UUID = Field(default_factory=uuid4)
    source_id: str
    change_type: ChangeType
    severity: ChangeSeverity
    previous_hash: str
    current_hash: str
    detected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    impacted_rule_codes: list[str] = Field(default_factory=list)
    notes: str | None = None


class ImpactReview(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    review_id: UUID = Field(default_factory=uuid4)
    change_event_id: UUID
    status: ReviewStatus
    reviewer_id: UUID | None = None
    decision_summary: str | None = None
    republish_required: bool = False
    impacted_subsystems: list[str] = Field(default_factory=list)


class IntegrationTarget(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    subsystem: str
    anchored_path: str
    integration_mode: str
    notes: str


class AntiDuplicationGuardrail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    title: str
    rule: str
    reuse_target: str
    prohibited_patterns: list[str] = Field(default_factory=list)


class WatchPlan(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_id: str
    cadence: WatchCadence
    parser_kind: str
    manual_review_required: bool = True
    rationale: str


class SwissRulesEnablementPack(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    jurisdictions: list[Jurisdiction]
    authorities: list[AuthorityRegistry]
    sources: list[RuleSource]
    rule_templates: list[RuleTemplate]
    requirement_templates: list[RequirementTemplate]
    procedure_templates: list[ProcedureTemplate]
    integration_targets: list[IntegrationTarget]
    guardrails: list[AntiDuplicationGuardrail]
    watch_plan: list[WatchPlan]
