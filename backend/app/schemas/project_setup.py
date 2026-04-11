"""Pydantic schemas for project setup wizard."""

from pydantic import BaseModel


class ProjectDraftRequest(BaseModel):
    intervention_type: str


class ProjectCreateRequest(BaseModel):
    intervention_type: str
    title: str
    description: str | None = None
    zones_affected: list[str] | None = None
    materials_used: list[str] | None = None
    gaps: list[dict] | None = None
