import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class SavedSimulationCreate(BaseModel):
    title: str
    description: str | None = None
    simulation_type: str = "renovation"
    parameters_json: dict[str, Any]
    results_json: dict[str, Any]
    total_cost_chf: float | None = None
    total_duration_weeks: int | None = None
    risk_level_before: str | None = None
    risk_level_after: str | None = None


class SavedSimulationUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    simulation_type: str | None = None
    parameters_json: dict[str, Any] | None = None
    results_json: dict[str, Any] | None = None
    total_cost_chf: float | None = None
    total_duration_weeks: int | None = None
    risk_level_before: str | None = None
    risk_level_after: str | None = None


class SavedSimulationRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    title: str
    description: str | None
    simulation_type: str
    parameters_json: dict[str, Any]
    results_json: dict[str, Any]
    total_cost_chf: float | None
    total_duration_weeks: int | None
    risk_level_before: str | None
    risk_level_after: str | None
    created_by: uuid.UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
