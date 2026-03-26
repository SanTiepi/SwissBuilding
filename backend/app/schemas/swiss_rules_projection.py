"""Projection schemas that turn SwissRules research into implementation candidates."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ProcedureCandidate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    procedure_code: str
    title: str
    summary: str
    procedure_type: str
    authority_code: str
    jurisdiction_code: str
    source_rule_code: str
    blocking: bool = True
    rationale: list[str] = Field(default_factory=list)


class ObligationCandidate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    requirement_code: str
    source_rule_code: str
    title: str
    description: str
    obligation_type: str
    priority: str
    responsible_role: str
    due_hint: str | None = None
    integration_target: str
    legal_basis_source_ids: list[str] = Field(default_factory=list)


class ControlTowerActionCandidate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    action_key: str
    source_rule_code: str
    title: str
    description: str
    priority_bucket: str
    action_type: str
    responsible_role: str
    integration_target: str
    legal_basis_source_ids: list[str] = Field(default_factory=list)
    manual_review: bool = False
    rationale: list[str] = Field(default_factory=list)


class ProjectionBundle(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    procedures: list[ProcedureCandidate] = Field(default_factory=list)
    obligations: list[ObligationCandidate] = Field(default_factory=list)
    actions: list[ControlTowerActionCandidate] = Field(default_factory=list)
