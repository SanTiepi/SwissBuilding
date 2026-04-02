"""
BatiConnect - Meteo Alert Cron Job (Programme S)

Runs 2x/day (6h, 18h) to check forecast against building incident history.
For each building with weather-sensitive incidents, evaluates predictions
and flags alerts for the notification system.

Usage (standalone or via task scheduler):
    python -m app.tasks.meteo_alert_job
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.incident import IncidentEpisode
from app.services.incident_prediction_service import (
    get_building_forecast_stub,
    predict_incidents,
)
from app.services.meteo_incident_correlation_service import WEATHER_SENSITIVE_TYPES

logger = logging.getLogger(__name__)


async def run_meteo_alert_scan(db: AsyncSession) -> dict:
    """Scan all buildings with incident history for weather-based alerts.

    Returns summary: {buildings_scanned, alerts_generated, errors}.
    """
    # Find buildings that have weather-sensitive incidents
    stmt = (
        select(IncidentEpisode.building_id)
        .where(IncidentEpisode.incident_type.in_(WEATHER_SENSITIVE_TYPES))
        .group_by(IncidentEpisode.building_id)
        .having(func.count(IncidentEpisode.id) >= 2)
    )
    result = await db.execute(stmt)
    building_ids = [row[0] for row in result.all()]

    logger.info("Meteo alert scan: %d buildings with incident history", len(building_ids))

    alerts_generated = 0
    errors = 0

    for bid in building_ids:
        try:
            forecast = await get_building_forecast_stub(db, bid)
            prediction = await predict_incidents(db, bid, forecast=forecast)

            if prediction.get("building_risk_level") in ("high", "medium"):
                alerts_generated += 1
                logger.info(
                    "Alert for building %s: risk=%s, predictions=%d",
                    bid,
                    prediction["building_risk_level"],
                    len(prediction.get("predicted_incidents", [])),
                )
                # In production: create notification via notification service
                # await create_notification(db, building_id=bid, type="meteo_alert", ...)

        except Exception:
            logger.exception("Error processing building %s", bid)
            errors += 1

    summary = {
        "run_at": datetime.utcnow().isoformat(),
        "buildings_scanned": len(building_ids),
        "alerts_generated": alerts_generated,
        "errors": errors,
    }
    logger.info("Meteo alert scan complete: %s", summary)
    return summary


async def _main() -> None:
    """Entry point for standalone execution."""
    async with async_session_factory() as db:
        summary = await run_meteo_alert_scan(db)
        print(f"Meteo alert scan: {summary}")


if __name__ == "__main__":
    asyncio.run(_main())
