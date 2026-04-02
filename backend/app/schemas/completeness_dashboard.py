"""Pydantic v2 schemas for the 16-dimension Completeness Dashboard."""

from pydantic import BaseModel, ConfigDict, Field


class MissingItem(BaseModel):
    """A single missing item in a completeness dimension."""

    field: str
    importance: str  # critical, important, nice_to_have

    model_config = ConfigDict(from_attributes=True)


class RecommendedAction(BaseModel):
    """A recommended action to improve completeness."""

    dimension: str
    dimension_label: str
    action: str
    priority: str  # critical, important, nice_to_have
    effort: str  # low, medium, high

    model_config = ConfigDict(from_attributes=True)


class DimensionScore(BaseModel):
    """Score for a single completeness dimension."""

    key: str
    label: str
    score: float = Field(..., ge=0, le=100)
    max_weight: int
    color: str  # green, yellow, orange, red
    missing_items: list[MissingItem] = Field(default_factory=list)
    required_actions: list[dict] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class CompletenessDashboardRead(BaseModel):
    """Full completeness dashboard response for a building."""

    building_id: str
    overall_score: float = Field(..., ge=0, le=100)
    overall_color: str
    dimensions: list[DimensionScore]
    missing_items_count: int
    urgent_actions: int
    recommended_actions: int
    trend: str  # improving, stable, declining
    evaluated_at: str

    model_config = ConfigDict(from_attributes=True)


class MissingItemDetail(BaseModel):
    """Detailed missing item with dimension context."""

    dimension: str
    dimension_label: str
    field: str
    importance: str
    status: str = "missing"

    model_config = ConfigDict(from_attributes=True)


class MissingItemsResponse(BaseModel):
    """List of all missing items across dimensions."""

    building_id: str
    items: list[MissingItemDetail]
    total: int

    model_config = ConfigDict(from_attributes=True)


class RecommendedActionsResponse(BaseModel):
    """Prioritized recommended actions."""

    building_id: str
    actions: list[RecommendedAction]
    total: int

    model_config = ConfigDict(from_attributes=True)
