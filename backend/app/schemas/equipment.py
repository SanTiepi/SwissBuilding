"""Equipment lifecycle schemas."""

from pydantic import BaseModel, Field


class EquipmentTimelineItem(BaseModel):
    item_id: str
    name: str
    type: str
    installation_year: int | None = None
    replacement_year: int
    years_until_replacement: int
    condition: str | None = None
    cost_chf: float | None = None
    critical: bool = False


class EquipmentTimelineResponse(BaseModel):
    building_id: str
    timeline: list[EquipmentTimelineItem] = Field(default_factory=list)
    total_forecast_cost_chf: float = 0.0
    critical_items_count: int = 0
    forecast_period_years: int = 10
    item_count: int = 0
