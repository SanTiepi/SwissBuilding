"""
SwissBuildingOS - Geospatial Service

PostGIS-powered spatial queries for buildings: bounding box, proximity,
GeoJSON conversion, and heatmap data aggregation.
"""

import json

from geoalchemy2 import Geography
from geoalchemy2.functions import (
    ST_AsGeoJSON,
    ST_DWithin,
    ST_MakeEnvelope,
    ST_MakePoint,
    ST_SetSRID,
)
from sqlalchemy import Float, and_, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore


def _building_geom_or_fallback(building_table=Building):
    """
    Return a SQL expression that uses the PostGIS geom column if available,
    falling back to constructing a point from lat/lon columns.
    """
    return case(
        (
            building_table.geom.isnot(None),
            building_table.geom,
        ),
        else_=ST_SetSRID(
            ST_MakePoint(building_table.longitude, building_table.latitude),
            4326,
        ),
    )


async def get_buildings_in_bbox(
    db: AsyncSession,
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
    pollutant: str | None = None,
    risk_level: str | None = None,
) -> list[dict]:
    """
    Query buildings within a bounding box using PostGIS ST_MakeEnvelope.
    Optionally filter by pollutant probability or risk level.
    Returns a list of GeoJSON Feature dicts.
    """
    envelope = ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
    geom_expr = _building_geom_or_fallback()

    stmt = (
        select(
            Building.id,
            Building.address,
            Building.city,
            Building.canton,
            Building.postal_code,
            Building.construction_year,
            Building.building_type,
            Building.latitude,
            Building.longitude,
            Building.status,
            BuildingRiskScore.overall_risk_level,
            BuildingRiskScore.asbestos_probability,
            BuildingRiskScore.pcb_probability,
            BuildingRiskScore.lead_probability,
            BuildingRiskScore.hap_probability,
            BuildingRiskScore.radon_probability,
            ST_AsGeoJSON(geom_expr).label("geojson"),
        )
        .outerjoin(BuildingRiskScore, Building.id == BuildingRiskScore.building_id)
        .where(
            Building.status != "archived",
            # Only include buildings that have coordinates
            and_(
                Building.latitude.isnot(None),
                Building.longitude.isnot(None),
            ),
        )
    )

    # Spatial filter using envelope
    stmt = stmt.where(func.ST_Intersects(geom_expr, envelope))

    # Optional pollutant filter (probability > 0.3 threshold)
    if pollutant:
        pollutant_col_map = {
            "asbestos": BuildingRiskScore.asbestos_probability,
            "pcb": BuildingRiskScore.pcb_probability,
            "lead": BuildingRiskScore.lead_probability,
            "hap": BuildingRiskScore.hap_probability,
            "radon": BuildingRiskScore.radon_probability,
        }
        col = pollutant_col_map.get(pollutant.lower())
        if col is not None:
            stmt = stmt.where(col > 0.3)

    # Optional risk level filter
    if risk_level:
        stmt = stmt.where(BuildingRiskScore.overall_risk_level == risk_level)

    result = await db.execute(stmt)
    rows = result.all()

    features = []
    for row in rows:
        geometry = (
            json.loads(row.geojson)
            if row.geojson
            else {
                "type": "Point",
                "coordinates": [row.longitude, row.latitude],
            }
        )

        feature = {
            "type": "Feature",
            "geometry": geometry,
            "properties": {
                "id": str(row.id),
                "address": row.address,
                "city": row.city,
                "canton": row.canton,
                "postal_code": row.postal_code,
                "construction_year": row.construction_year,
                "building_type": row.building_type,
                "status": row.status,
                "overall_risk_level": row.overall_risk_level or "unknown",
                "asbestos_probability": row.asbestos_probability,
                "pcb_probability": row.pcb_probability,
                "lead_probability": row.lead_probability,
                "hap_probability": row.hap_probability,
                "radon_probability": row.radon_probability,
            },
        }
        features.append(feature)

    return features


async def get_buildings_geojson(db: AsyncSession, buildings: list[Building]) -> dict:
    """
    Convert a list of Building model instances to a GeoJSON FeatureCollection.
    """
    features = []

    for b in buildings:
        if b.latitude is not None and b.longitude is not None:
            geometry = {
                "type": "Point",
                "coordinates": [b.longitude, b.latitude],
            }
        else:
            geometry = None

        feature = {
            "type": "Feature",
            "geometry": geometry,
            "properties": {
                "id": str(b.id),
                "address": b.address,
                "city": b.city,
                "canton": b.canton,
                "postal_code": b.postal_code,
                "construction_year": b.construction_year,
                "building_type": b.building_type,
                "status": b.status,
            },
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features,
    }


async def get_nearby_buildings(
    db: AsyncSession,
    lat: float,
    lon: float,
    radius_m: float = 500,
) -> list[Building]:
    """
    Find buildings within a given radius (in meters) of a point,
    using PostGIS ST_DWithin on geography type for accurate meter-based distance.
    """
    point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)
    geom_expr = _building_geom_or_fallback()

    # Cast geometry to geography for meter-based ST_DWithin
    geog_type = Geography(geometry_type="POINT", srid=4326)
    stmt = (
        select(Building)
        .where(
            Building.status != "archived",
            Building.latitude.isnot(None),
            Building.longitude.isnot(None),
        )
        .where(
            ST_DWithin(
                cast(geom_expr, geog_type),
                cast(point, geog_type),
                radius_m,
            )
        )
    )

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_heatmap_data(
    db: AsyncSession,
    pollutant: str | None = None,
    canton: str | None = None,
) -> list[dict]:
    """
    Aggregate risk data for generating heatmap visualizations.
    Returns a list of dicts with lat, lon, and risk intensity value.
    """
    # Choose which probability column to aggregate
    pollutant_col_map = {
        "asbestos": BuildingRiskScore.asbestos_probability,
        "pcb": BuildingRiskScore.pcb_probability,
        "lead": BuildingRiskScore.lead_probability,
        "hap": BuildingRiskScore.hap_probability,
        "radon": BuildingRiskScore.radon_probability,
    }

    if pollutant and pollutant.lower() in pollutant_col_map:
        risk_col = pollutant_col_map[pollutant.lower()]
    else:
        # Default: use the max of all pollutants as intensity
        risk_col = func.greatest(
            BuildingRiskScore.asbestos_probability,
            BuildingRiskScore.pcb_probability,
            BuildingRiskScore.lead_probability,
            BuildingRiskScore.hap_probability,
            BuildingRiskScore.radon_probability,
        )

    stmt = (
        select(
            Building.latitude,
            Building.longitude,
            cast(risk_col, Float).label("intensity"),
            BuildingRiskScore.overall_risk_level,
        )
        .join(BuildingRiskScore, Building.id == BuildingRiskScore.building_id)
        .where(
            Building.status != "archived",
            Building.latitude.isnot(None),
            Building.longitude.isnot(None),
        )
    )

    if canton:
        stmt = stmt.where(Building.canton == canton.upper())

    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "lat": row.latitude,
            "lon": row.longitude,
            "intensity": round(row.intensity, 3) if row.intensity else 0.0,
            "risk_level": row.overall_risk_level or "unknown",
        }
        for row in rows
    ]
