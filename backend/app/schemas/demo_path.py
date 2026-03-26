"""Schemas for guided demo path scenarios."""

from __future__ import annotations

from pydantic import BaseModel


class DemoStep(BaseModel):
    """A single step in a guided demo scenario."""

    order: int
    title: str
    description: str
    api_endpoint: str
    expected_insight: str
    page_path: str
    cta_label: str


class DemoScenarioResult(BaseModel):
    """A complete demo scenario with its steps."""

    scenario_type: str
    title: str
    description: str
    icon: str
    step_count: int
    steps: list[DemoStep] = []
