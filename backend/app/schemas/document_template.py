"""Pydantic v2 schemas for the Document Template system."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TemplateField(BaseModel):
    """A single field in a template section."""

    label: str
    value: str | None = None
    editable: bool = False
    field_type: str = "text"  # text, date, number, choice
    choices: list[str] | None = None

    model_config = ConfigDict(from_attributes=True)


class TemplateSection(BaseModel):
    """A named section containing multiple fields."""

    name: str
    title: str
    fields: list[TemplateField]

    model_config = ConfigDict(from_attributes=True)


class TemplateInfo(BaseModel):
    """Describes an available template and its requirements."""

    template_type: str
    title: str
    description: str
    is_available: bool
    required_data: list[str]
    legal_basis: str | None = None

    model_config = ConfigDict(from_attributes=True)


class GeneratedTemplate(BaseModel):
    """A fully generated template with pre-filled data."""

    template_type: str
    title: str
    sections: list[TemplateSection]
    metadata: dict
    warnings: list[str]
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GenerateTemplateRequest(BaseModel):
    """Request body for template generation."""

    template_type: str

    model_config = ConfigDict(from_attributes=True)
