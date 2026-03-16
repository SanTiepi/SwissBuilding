from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.services.geospatial_service import get_buildings_in_bbox, get_heatmap_data

router = APIRouter()


def _parse_bbox(bbox: str) -> tuple[float, float, float, float]:
    """Parse a bounding box string 'minlon,minlat,maxlon,maxlat' into a tuple of floats."""
    try:
        parts = [float(x.strip()) for x in bbox.split(",")]
        if len(parts) != 4:
            raise ValueError
        return parts[0], parts[1], parts[2], parts[3]
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=400,
            detail="bbox must be in format 'minlon,minlat,maxlon,maxlat'",
        ) from None


@router.get("/buildings")
async def get_map_buildings(
    bbox: str = Query(..., description="Bounding box: minlon,minlat,maxlon,maxlat"),
    pollutant: str | None = Query(None, description="Filter by pollutant type (e.g. asbestos, lead, pcb)"),
    risk_level: str | None = Query(None, description="Filter by risk level (low, medium, high, critical)"),
    current_user: User = Depends(require_permission("pollutant_map", "read")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return buildings within a bounding box as a GeoJSON FeatureCollection."""
    minlon, minlat, maxlon, maxlat = _parse_bbox(bbox)

    features = await get_buildings_in_bbox(
        db, minlon, minlat, maxlon, maxlat, pollutant=pollutant, risk_level=risk_level
    )

    return {
        "type": "FeatureCollection",
        "features": features,
    }


@router.get("/heatmap")
async def get_heatmap(
    bbox: str = Query(..., description="Bounding box: minlon,minlat,maxlon,maxlat"),
    pollutant: str | None = Query(None, description="Filter by pollutant type"),
    current_user: User = Depends(require_permission("pollutant_map", "read")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return heatmap grid data for pollutant density within a bounding box."""
    minlon, minlat, maxlon, maxlat = _parse_bbox(bbox)

    grid_data = await get_heatmap_data(db, pollutant=pollutant)

    return {
        "bbox": [minlon, minlat, maxlon, maxlat],
        "grid": grid_data,
    }


@router.get("/clusters")
async def get_clusters(
    bbox: str = Query(..., description="Bounding box: minlon,minlat,maxlon,maxlat"),
    pollutant: str | None = Query(None, description="Filter by pollutant type"),
    risk_level: str | None = Query(None, description="Filter by risk level"),
    zoom: int = Query(10, ge=1, le=20, description="Map zoom level for cluster granularity"),
    current_user: User = Depends(require_permission("pollutant_map", "read")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return clustered building points for the given bounding box and zoom level."""
    minlon, minlat, maxlon, maxlat = _parse_bbox(bbox)

    # Reuse the bbox query but group by grid cell based on zoom level
    features = await get_buildings_in_bbox(
        db, minlon, minlat, maxlon, maxlat, pollutant=pollutant, risk_level=risk_level
    )

    # Cluster features by grid cell
    cell_size = 360.0 / (2**zoom)
    clusters: dict[tuple[int, int], list] = {}

    for feature in features:
        coords = feature.get("geometry", {}).get("coordinates", [0, 0])
        lon, lat = coords[0], coords[1]
        cell_x = int(lon / cell_size)
        cell_y = int(lat / cell_size)
        key = (cell_x, cell_y)
        if key not in clusters:
            clusters[key] = []
        clusters[key].append(feature)

    cluster_features = []
    for (cell_x, cell_y), group in clusters.items():
        center_lon = (cell_x + 0.5) * cell_size
        center_lat = (cell_y + 0.5) * cell_size
        cluster_features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [center_lon, center_lat],
                },
                "properties": {
                    "cluster": True,
                    "point_count": len(group),
                    "building_ids": [f.get("properties", {}).get("id") for f in group],
                },
            }
        )

    return {
        "type": "FeatureCollection",
        "features": cluster_features,
    }
