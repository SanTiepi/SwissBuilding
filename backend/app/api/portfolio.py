from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.models.user import User
from app.schemas.portfolio import MapBuildingsGeoJSON, PortfolioMetrics

router = APIRouter()


@router.get("/metrics", response_model=PortfolioMetrics)
async def get_portfolio_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return aggregated portfolio metrics across all buildings."""

    # Total buildings
    total_result = await db.execute(select(func.count()).select_from(Building).where(Building.status == "active"))
    total_buildings = total_result.scalar() or 0

    # Risk distribution
    risk_result = await db.execute(
        select(BuildingRiskScore.overall_risk_level, func.count())
        .join(Building, Building.id == BuildingRiskScore.building_id)
        .where(Building.status == "active")
        .group_by(BuildingRiskScore.overall_risk_level)
    )
    risk_rows = risk_result.all()
    risk_distribution = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for level, count in risk_rows:
        if level in risk_distribution:
            risk_distribution[level] = count

    # Completeness average (based on confidence as a proxy for data completeness)
    completeness_result = await db.execute(
        select(func.avg(BuildingRiskScore.confidence))
        .join(Building, Building.id == BuildingRiskScore.building_id)
        .where(Building.status == "active")
    )
    completeness_avg = completeness_result.scalar() or 0.0
    completeness_avg = round(float(completeness_avg), 2)

    # Buildings ready (high confidence >= 0.7) vs not ready
    ready_result = await db.execute(
        select(func.count())
        .select_from(BuildingRiskScore)
        .join(Building, Building.id == BuildingRiskScore.building_id)
        .where(Building.status == "active", BuildingRiskScore.confidence >= 0.7)
    )
    buildings_ready = ready_result.scalar() or 0
    buildings_not_ready = total_buildings - buildings_ready

    # Pollutant prevalence: count buildings with diagnostic samples per pollutant type
    pollutant_result = await db.execute(
        select(Sample.pollutant_type, func.count(func.distinct(Diagnostic.building_id)))
        .join(Diagnostic, Diagnostic.id == Sample.diagnostic_id)
        .join(Building, Building.id == Diagnostic.building_id)
        .where(Building.status == "active", Sample.threshold_exceeded.is_(True))
        .group_by(Sample.pollutant_type)
    )
    pollutant_rows = pollutant_result.all()
    pollutant_prevalence = {"asbestos": 0, "pcb": 0, "lead": 0, "hap": 0, "radon": 0}
    for pollutant, count in pollutant_rows:
        if pollutant in pollutant_prevalence:
            pollutant_prevalence[pollutant] = count

    # Actions pending (open or in_progress)
    actions_pending_result = await db.execute(
        select(func.count()).select_from(ActionItem).where(ActionItem.status.in_(["open", "in_progress"]))
    )
    actions_pending = actions_pending_result.scalar() or 0

    # Actions critical
    actions_critical_result = await db.execute(
        select(func.count())
        .select_from(ActionItem)
        .where(ActionItem.priority == "critical", ActionItem.status.in_(["open", "in_progress"]))
    )
    actions_critical = actions_critical_result.scalar() or 0

    # Recent diagnostics (in_progress or draft)
    recent_diag_result = await db.execute(
        select(func.count()).select_from(Diagnostic).where(Diagnostic.status.in_(["in_progress", "draft"]))
    )
    recent_diagnostics = recent_diag_result.scalar() or 0

    # Interventions in progress
    interventions_result = await db.execute(
        select(func.count()).select_from(Intervention).where(Intervention.status == "in_progress")
    )
    interventions_in_progress = interventions_result.scalar() or 0

    return PortfolioMetrics(
        total_buildings=total_buildings,
        risk_distribution=risk_distribution,
        completeness_avg=completeness_avg,
        buildings_ready=buildings_ready,
        buildings_not_ready=buildings_not_ready,
        pollutant_prevalence=pollutant_prevalence,
        actions_pending=actions_pending,
        actions_critical=actions_critical,
        recent_diagnostics=recent_diagnostics,
        interventions_in_progress=interventions_in_progress,
    )


@router.get("/map-buildings", response_model=MapBuildingsGeoJSON)
async def get_map_buildings(
    risk_level: str | None = Query(None, description="Comma-separated risk levels (low,medium,high,critical)"),
    canton: str | None = Query(None, description="Filter by canton code (e.g. VD, GE)"),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return all active buildings with coordinates as a GeoJSON FeatureCollection."""

    query = (
        select(Building, BuildingRiskScore)
        .outerjoin(BuildingRiskScore, Building.id == BuildingRiskScore.building_id)
        .where(
            Building.status == "active",
            Building.latitude.isnot(None),
            Building.longitude.isnot(None),
        )
    )

    if risk_level:
        levels = [lvl.strip() for lvl in risk_level.split(",") if lvl.strip()]
        if levels:
            query = query.where(BuildingRiskScore.overall_risk_level.in_(levels))

    if canton:
        query = query.where(Building.canton == canton.strip().upper())

    result = await db.execute(query)
    rows = result.all()

    features = []
    for building, risk_score in rows:
        properties: dict[str, Any] = {
            "id": str(building.id),
            "address": building.address,
            "city": building.city,
            "canton": building.canton,
            "construction_year": building.construction_year,
            "overall_risk_level": risk_score.overall_risk_level if risk_score else "unknown",
            "risk_score": round(float(risk_score.confidence), 2) if risk_score and risk_score.confidence else 0.0,
            "completeness_score": round(float(risk_score.confidence), 2)
            if risk_score and risk_score.confidence
            else 0.0,
        }
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [building.longitude, building.latitude],
                },
                "properties": properties,
            }
        )

    return {
        "type": "FeatureCollection",
        "features": features,
    }
