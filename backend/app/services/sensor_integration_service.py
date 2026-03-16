"""Sensor Integration Service.

Manages IoT sensor data integration for continuous building monitoring.
Simulates sensor readings based on building diagnostic data — radon sensors,
air quality monitors, humidity/temperature sensors, particle counters, CO2 monitors.

Swiss regulatory thresholds:
- Radon: 300 Bq/m³ (ORaP Art. 110)
- Asbestos fibers: 0.01 f/cm³
- CO2: 1000 ppm
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.schemas.sensor_integration import (
    BuildingSensorAlerts,
    BuildingSensorOverview,
    BuildingSensorTrends,
    PortfolioSensorStatus,
    SensorAlert,
    SensorDevice,
    SensorReading,
    SensorTrend,
)
from app.services.building_data_loader import load_org_buildings

# Swiss regulatory thresholds
_THRESHOLDS: dict[str, tuple[float, str]] = {
    "radon_concentration": (300.0, "Bq/m³"),
    "fiber_concentration": (0.01, "f/cm³"),
    "co2_concentration": (1000.0, "ppm"),
    "humidity": (70.0, "%"),
    "temperature": (30.0, "°C"),
    "pm2_5": (25.0, "µg/m³"),
}

# Simulated baseline values per sensor type
_BASELINE_VALUES: dict[str, list[tuple[str, float, str]]] = {
    "radon_monitor": [("radon_concentration", 180.0, "Bq/m³")],
    "air_quality": [("pm2_5", 12.0, "µg/m³")],
    "humidity_temp": [("humidity", 55.0, "%"), ("temperature", 21.0, "°C")],
    "particle_counter": [("fiber_concentration", 0.005, "f/cm³")],
    "co2_monitor": [("co2_concentration", 650.0, "ppm")],
}


def _sensor_id(building_id: uuid.UUID, sensor_type: str, suffix: str = "") -> str:
    """Deterministic sensor id based on building + type + suffix."""
    raw = f"{building_id}:sensor:{sensor_type}:{suffix}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _alert_id(sensor_id: str, metric: str) -> str:
    """Deterministic alert id."""
    raw = f"{sensor_id}:alert:{metric}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


async def get_building_sensor_overview(
    building_id: uuid.UUID,
    db: AsyncSession,
) -> BuildingSensorOverview:
    """Generate sensor overview for a building based on diagnostic data."""
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return BuildingSensorOverview(
            building_id=building_id,
            sensors=[],
            total_sensors=0,
            active_sensors=0,
            sensors_with_alerts=0,
            latest_readings=[],
            generated_at=datetime.now(UTC),
        )

    # Determine sensor types from diagnostics
    sensor_types = await _determine_sensor_types(db, building_id)
    now = datetime.now(UTC)

    sensors: list[SensorDevice] = []
    readings: list[SensorReading] = []
    alert_count = 0

    for stype in sensor_types:
        sid = _sensor_id(building_id, stype)
        sensors.append(
            SensorDevice(
                sensor_id=sid,
                sensor_type=stype,
                location_description=f"Building {building.address}",
                zone_id=None,
                installed_date=None,
                status="active",
                last_reading_at=now,
            )
        )

        # Generate readings for this sensor
        baseline_metrics = _BASELINE_VALUES.get(stype, [])
        for metric, base_value, unit in baseline_metrics:
            threshold_info = _THRESHOLDS.get(metric)
            is_above = False
            if threshold_info:
                is_above = base_value > threshold_info[0]
            if is_above:
                alert_count += 1

            readings.append(
                SensorReading(
                    sensor_id=sid,
                    timestamp=now,
                    metric=metric,
                    value=base_value,
                    unit=unit,
                    is_above_threshold=is_above,
                )
            )

    # Adjust readings based on actual diagnostic data
    readings = await _adjust_readings_from_diagnostics(db, building_id, readings)

    # Recount alerts after adjustment
    alert_count = sum(1 for r in readings if r.is_above_threshold)
    sensors_alerting = len({r.sensor_id for r in readings if r.is_above_threshold})

    return BuildingSensorOverview(
        building_id=building_id,
        sensors=sensors,
        total_sensors=len(sensors),
        active_sensors=len(sensors),
        sensors_with_alerts=sensors_alerting,
        latest_readings=readings,
        generated_at=now,
    )


async def get_building_sensor_alerts(
    building_id: uuid.UUID,
    db: AsyncSession,
) -> BuildingSensorAlerts:
    """Generate alerts for sensors with readings exceeding thresholds."""
    overview = await get_building_sensor_overview(building_id, db)
    now = datetime.now(UTC)
    alerts: list[SensorAlert] = []

    for reading in overview.latest_readings:
        threshold_info = _THRESHOLDS.get(reading.metric)
        if not threshold_info:
            continue

        threshold_val, unit = threshold_info
        ratio = reading.value / threshold_val if threshold_val > 0 else 0.0

        if ratio > 2.0:
            severity = "critical"
        elif ratio > 1.0:
            severity = "warning"
        elif ratio > 0.8:
            severity = "info"
        else:
            continue

        # Find sensor type
        sensor_type = "unknown"
        for sensor in overview.sensors:
            if sensor.sensor_id == reading.sensor_id:
                sensor_type = sensor.sensor_type
                break

        alerts.append(
            SensorAlert(
                alert_id=_alert_id(reading.sensor_id, reading.metric),
                sensor_id=reading.sensor_id,
                sensor_type=sensor_type,
                metric=reading.metric,
                value=reading.value,
                threshold=threshold_val,
                unit=unit,
                severity=severity,
                triggered_at=now,
                acknowledged=False,
            )
        )

    critical_count = sum(1 for a in alerts if a.severity == "critical")
    unack_count = sum(1 for a in alerts if not a.acknowledged)

    return BuildingSensorAlerts(
        building_id=building_id,
        alerts=alerts,
        total_alerts=len(alerts),
        critical_count=critical_count,
        unacknowledged_count=unack_count,
        generated_at=now,
    )


async def get_building_sensor_trends(
    building_id: uuid.UUID,
    db: AsyncSession,
    period_days: int = 30,
) -> BuildingSensorTrends:
    """Generate trend data for building sensors over a period."""
    overview = await get_building_sensor_overview(building_id, db)
    now = datetime.now(UTC)
    trends: list[SensorTrend] = []

    # Look for diagnostic dates to determine trend direction
    diag_result = await db.execute(
        select(Diagnostic).where(Diagnostic.building_id == building_id).order_by(Diagnostic.created_at.desc())
    )
    diagnostics = diag_result.scalars().all()
    has_recent_diagnostics = any(
        d.created_at and d.created_at > (now - timedelta(days=period_days)).replace(tzinfo=None)
        for d in diagnostics
        if d.created_at is not None
    )

    for reading in overview.latest_readings:
        base = reading.value
        # Simulate variation
        variation = base * 0.15
        min_val = round(base - variation, 2)
        max_val = round(base + variation, 2)

        # Trend direction: if recent diagnostics found issues, trend rising; else stable/falling
        if reading.is_above_threshold:
            direction = "rising"
        elif has_recent_diagnostics:
            direction = "stable"
        else:
            direction = "falling"

        trends.append(
            SensorTrend(
                sensor_id=reading.sensor_id,
                metric=reading.metric,
                period=f"{period_days}d",
                min_value=min_val,
                max_value=max_val,
                avg_value=round(base, 2),
                readings_count=period_days * 24,  # hourly readings
                trend_direction=direction,
            )
        )

    return BuildingSensorTrends(
        building_id=building_id,
        trends=trends,
        monitoring_period_days=period_days,
        generated_at=now,
    )


async def get_portfolio_sensor_status(
    org_id: uuid.UUID,
    db: AsyncSession,
) -> PortfolioSensorStatus:
    """Aggregate sensor status across all buildings in an organization."""
    all_buildings = await load_org_buildings(db, org_id)
    buildings = [b for b in all_buildings if b.status == "active"]

    now = datetime.now(UTC)
    total_sensors = 0
    active_sensors = 0
    buildings_with_alerts = 0
    alert_summary: dict[str, int] = {"info": 0, "warning": 0, "critical": 0}

    for b in buildings:
        overview = await get_building_sensor_overview(b.id, db)
        total_sensors += overview.total_sensors
        active_sensors += overview.active_sensors

        if overview.sensors_with_alerts > 0:
            buildings_with_alerts += 1

        alerts = await get_building_sensor_alerts(b.id, db)
        for alert in alerts.alerts:
            alert_summary[alert.severity] = alert_summary.get(alert.severity, 0) + 1

    return PortfolioSensorStatus(
        organization_id=org_id,
        total_buildings_monitored=len(buildings),
        total_sensors=total_sensors,
        active_sensors=active_sensors,
        buildings_with_alerts=buildings_with_alerts,
        alert_summary=alert_summary,
        generated_at=now,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _determine_sensor_types(
    db: AsyncSession,
    building_id: uuid.UUID,
) -> list[str]:
    """Determine which sensor types a building should have based on diagnostics."""
    result = await db.execute(
        select(Diagnostic.diagnostic_type).where(Diagnostic.building_id == building_id).distinct()
    )
    diag_types = {row[0] for row in result.all()}

    sensor_types: list[str] = []
    if "radon" in diag_types:
        sensor_types.append("radon_monitor")
    if "asbestos" in diag_types:
        sensor_types.extend(["air_quality", "particle_counter"])

    # Default sensors for all buildings with diagnostics
    if diag_types:
        sensor_types.extend(["humidity_temp", "co2_monitor"])
    elif not sensor_types:
        # Even buildings without diagnostics get basic sensors
        sensor_types.extend(["humidity_temp", "co2_monitor"])

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for st in sensor_types:
        if st not in seen:
            seen.add(st)
            unique.append(st)
    return unique


async def _adjust_readings_from_diagnostics(
    db: AsyncSession,
    building_id: uuid.UUID,
    readings: list[SensorReading],
) -> list[SensorReading]:
    """Adjust simulated readings based on actual sample data."""
    # Check for radon samples with high concentration
    result = await db.execute(
        select(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(
            Diagnostic.building_id == building_id,
            Sample.pollutant_type == "radon",
            Sample.concentration.isnot(None),
        )
    )
    radon_samples = result.scalars().all()

    # Check for asbestos samples with threshold exceeded
    result2 = await db.execute(
        select(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(
            Diagnostic.building_id == building_id,
            Sample.pollutant_type == "asbestos",
            Sample.threshold_exceeded.is_(True),
        )
    )
    asbestos_samples = result2.scalars().all()

    adjusted: list[SensorReading] = []
    for reading in readings:
        new_value = reading.value
        new_above = reading.is_above_threshold

        if reading.metric == "radon_concentration" and radon_samples:
            # Use actual concentration from latest sample
            latest = max(radon_samples, key=lambda s: s.concentration or 0)
            if latest.concentration is not None:
                new_value = latest.concentration
                new_above = new_value > 300.0

        if reading.metric == "fiber_concentration" and asbestos_samples:
            # Elevate fiber reading if asbestos was found
            new_value = 0.015
            new_above = new_value > 0.01

        adjusted.append(
            SensorReading(
                sensor_id=reading.sensor_id,
                timestamp=reading.timestamp,
                metric=reading.metric,
                value=new_value,
                unit=reading.unit,
                is_above_threshold=new_above,
            )
        )

    return adjusted
