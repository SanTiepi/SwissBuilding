"""Pydantic v2 schemas for the Sensor Integration service."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SensorDevice(BaseModel):
    """An IoT sensor device installed in a building."""

    sensor_id: str
    sensor_type: str  # radon_monitor | air_quality | humidity_temp | particle_counter | co2_monitor
    location_description: str | None = None
    zone_id: UUID | None = None
    installed_date: date | None = None
    status: str  # active | inactive | maintenance | decommissioned
    last_reading_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SensorReading(BaseModel):
    """A single reading from a sensor."""

    sensor_id: str
    timestamp: datetime
    metric: str
    value: float
    unit: str
    is_above_threshold: bool

    model_config = ConfigDict(from_attributes=True)


class BuildingSensorOverview(BaseModel):
    """Overview of all sensors and latest readings for a building."""

    building_id: UUID
    sensors: list[SensorDevice]
    total_sensors: int
    active_sensors: int
    sensors_with_alerts: int
    latest_readings: list[SensorReading]
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SensorAlert(BaseModel):
    """An alert triggered when a sensor reading exceeds a threshold."""

    alert_id: str
    sensor_id: str
    sensor_type: str
    metric: str
    value: float
    threshold: float
    unit: str
    severity: str  # info | warning | critical
    triggered_at: datetime
    acknowledged: bool

    model_config = ConfigDict(from_attributes=True)


class BuildingSensorAlerts(BaseModel):
    """All sensor alerts for a building."""

    building_id: UUID
    alerts: list[SensorAlert]
    total_alerts: int
    critical_count: int
    unacknowledged_count: int
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SensorTrend(BaseModel):
    """Trend analysis for a single sensor metric over a period."""

    sensor_id: str
    metric: str
    period: str
    min_value: float
    max_value: float
    avg_value: float
    readings_count: int
    trend_direction: str  # rising | stable | falling

    model_config = ConfigDict(from_attributes=True)


class BuildingSensorTrends(BaseModel):
    """Trend data for all sensors in a building."""

    building_id: UUID
    trends: list[SensorTrend]
    monitoring_period_days: int
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PortfolioSensorStatus(BaseModel):
    """Org-level sensor status across all monitored buildings."""

    organization_id: UUID
    total_buildings_monitored: int
    total_sensors: int
    active_sensors: int
    buildings_with_alerts: int
    alert_summary: dict[str, int]
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)
