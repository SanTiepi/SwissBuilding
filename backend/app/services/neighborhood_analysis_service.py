"""
SwissBuildingOS - Neighborhood Analysis Service (Programme W)

Analyze the built neighborhood context using PostGIS spatial queries.
Provides:
  - Neighbor discovery within radius (ST_DWithin)
  - Construction era distribution and homogeneity
  - Nearby construction activity detection
  - Risk propagation assessment between buildings
"""

from __future__ import annotations

import math
from collections import Counter
from uuid import UUID

from geoalchemy2 import Geography
from geoalchemy2.functions import ST_DWithin, ST_MakePoint, ST_SetSRID
from sqlalchemy import cast, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ERA_BUCKETS = [
    (1940, 1950, "1940-1950"),
    (1950, 1960, "1950-1960"),
    (1960, 1970, "1960-1970"),
    (1970, 1980, "1970-1980"),
    (1980, 1990, "1980-1990"),
    (1990, 2000, "1990-2000"),
    (2000, 2010, "2000-2010"),
    (2010, 2030, "2010+"),
]


def _era_bucket(year: int | None) -> str:
    if year is None:
        return "unknown"
    for lo, hi, label in _ERA_BUCKETS:
        if lo <= year < hi:
            return label
    if year < 1940:
        return "pre-1940"
    return "2010+"


def _compute_homogeneity(years: list[int]) -> float:
    """Compute homogeneity score 0-100.

    100 = all buildings same decade, 0 = spread across centuries.
    Based on standard deviation of construction years.
    """
    if len(years) < 2:
        return 100.0
    mean = sum(years) / len(years)
    variance = sum((y - mean) ** 2 for y in years) / len(years)
    std_dev = math.sqrt(variance)
    # Normalize: std_dev of 0 = 100, std_dev of 50+ = 0
    score = max(0.0, 100.0 - std_dev * 2)
    return round(score, 1)


def _estimate_height(building: Building) -> float | None:
    """Estimate building height from floors or enrichment data."""
    meta = building.source_metadata_json or {}
    # Check OSM data for explicit height
    osm = meta.get("osm_building", {})
    if osm.get("height"):
        return float(osm["height"])
    # Estimate from floors (3m per floor is Swiss average)
    if building.floors_above:
        return building.floors_above * 3.0
    return None


def _bearing_label(lat1: float, lon1: float, lat2: float, lon2: float) -> str:
    """Compute cardinal direction from point 1 to point 2."""
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    angle = math.degrees(math.atan2(dlon, dlat)) % 360
    if angle < 45 or angle >= 315:
        return "north"
    if 45 <= angle < 135:
        return "east"
    if 135 <= angle < 225:
        return "south"
    return "west"


# ---------------------------------------------------------------------------
# Internal: get nearby buildings (pure Python fallback for SQLite tests)
# ---------------------------------------------------------------------------


async def _get_nearby_buildings_postgis(
    db: AsyncSession,
    building: Building,
    radius_m: float,
) -> list[Building]:
    """Use PostGIS ST_DWithin for meter-accurate radius search."""
    from app.services.geospatial_service import _building_geom_or_fallback

    point = ST_SetSRID(ST_MakePoint(building.longitude, building.latitude), 4326)
    geom_expr = _building_geom_or_fallback()
    geog_type = Geography(geometry_type="POINT", srid=4326)

    stmt = (
        select(Building)
        .where(
            Building.id != building.id,
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


async def _get_nearby_buildings_fallback(
    db: AsyncSession,
    building: Building,
    radius_m: float,
) -> list[Building]:
    """Haversine-based fallback when PostGIS is not available (e.g. SQLite tests)."""
    # Approximate degree distance: 1 degree lat ≈ 111km
    degree_radius = radius_m / 111_000
    stmt = select(Building).where(
        Building.id != building.id,
        Building.status != "archived",
        Building.latitude.isnot(None),
        Building.longitude.isnot(None),
        Building.latitude.between(
            building.latitude - degree_radius,
            building.latitude + degree_radius,
        ),
        Building.longitude.between(
            building.longitude - degree_radius,
            building.longitude + degree_radius,
        ),
    )
    result = await db.execute(stmt)
    candidates = list(result.scalars().all())

    # Precise haversine filter
    nearby = []
    for c in candidates:
        dist = _haversine_m(building.latitude, building.longitude, c.latitude, c.longitude)
        if dist <= radius_m:
            nearby.append(c)
    return nearby


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in meters."""
    R = 6_371_000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def _get_nearby(db: AsyncSession, building: Building, radius_m: float) -> list[Building]:
    """Get nearby buildings, trying PostGIS first, falling back to Haversine."""
    try:
        return await _get_nearby_buildings_postgis(db, building, radius_m)
    except Exception:
        return await _get_nearby_buildings_fallback(db, building, radius_m)


# ---------------------------------------------------------------------------
# FN1: analyze_neighborhood
# ---------------------------------------------------------------------------


async def analyze_neighborhood(db: AsyncSession, building_id: UUID, radius_m: float = 100) -> dict:
    """Analyze buildings within radius: era distribution, homogeneity, density.

    Uses PostGIS ST_DWithin when available, haversine fallback for SQLite.
    """
    stmt = select(Building).where(Building.id == building_id)
    result = await db.execute(stmt)
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    if building.latitude is None or building.longitude is None:
        return {
            "buildings_in_radius": 0,
            "avg_construction_year": None,
            "construction_era_distribution": {},
            "avg_floors": None,
            "homogeneity_score": None,
            "dominant_type": None,
            "has_diagnosed_neighbors": 0,
            "neighbor_findings": [],
            "shadow_risk": "unknown",
            "density_score": 0.0,
            "recommendation": "Coordonnées GPS non disponibles — enrichissement nécessaire",
            "coordinates_available": False,
        }

    neighbors = await _get_nearby(db, building, radius_m)

    if not neighbors:
        return {
            "buildings_in_radius": 0,
            "avg_construction_year": None,
            "construction_era_distribution": {},
            "avg_floors": None,
            "homogeneity_score": None,
            "dominant_type": None,
            "has_diagnosed_neighbors": 0,
            "neighbor_findings": [],
            "shadow_risk": "none",
            "density_score": 0.0,
            "recommendation": "Aucun bâtiment voisin dans le rayon — bâtiment isolé",
            "coordinates_available": True,
        }

    # Construction years
    years = [n.construction_year for n in neighbors if n.construction_year]
    avg_year = round(sum(years) / len(years)) if years else None

    # Era distribution
    era_dist = dict(Counter(_era_bucket(n.construction_year) for n in neighbors))

    # Average floors
    floors = [n.floors_above for n in neighbors if n.floors_above]
    avg_floors = round(sum(floors) / len(floors), 1) if floors else None

    # Homogeneity
    homogeneity = _compute_homogeneity(years) if years else None

    # Dominant building type
    types = Counter(n.building_type for n in neighbors if n.building_type)
    dominant_type = types.most_common(1)[0][0] if types else None

    # Diagnosed neighbors: load diagnostics for neighbor IDs
    neighbor_ids = [n.id for n in neighbors]
    diag_stmt = select(Diagnostic).where(Diagnostic.building_id.in_(neighbor_ids))
    diag_result = await db.execute(diag_stmt)
    diagnostics = diag_result.scalars().all()
    diagnosed_building_ids = {d.building_id for d in diagnostics}

    # Neighbor findings: load samples from diagnosed neighbors
    neighbor_findings = []
    if diagnostics:
        diag_ids = [d.id for d in diagnostics]
        sample_stmt = select(Sample).where(
            Sample.diagnostic_id.in_(diag_ids),
            Sample.threshold_exceeded.is_(True),
        )
        sample_result = await db.execute(sample_stmt)
        samples = sample_result.scalars().all()
        # Map diagnostic_id -> building_id
        diag_to_building = {d.id: d.building_id for d in diagnostics}
        for s in samples:
            neighbor_findings.append(
                {
                    "building_id": str(diag_to_building.get(s.diagnostic_id)),
                    "pollutant": s.pollutant_type,
                    "material": s.material_category,
                    "year_found": str(s.created_at.year) if s.created_at else None,
                }
            )

    # Shadow risk: check for tall buildings to the south
    shadow_risk = "none"
    building_height = _estimate_height(building) or 9.0  # default 3 floors
    for n in neighbors:
        n_height = _estimate_height(n)
        if n_height and n_height > building_height + 3:
            direction = _bearing_label(building.latitude, building.longitude, n.latitude, n.longitude)
            if direction == "south":
                shadow_risk = "high"
                break
            elif direction in ("east", "west"):
                shadow_risk = max(shadow_risk, "medium", key=lambda x: ["none", "low", "medium", "high"].index(x))

    # Density: buildings per hectare (1 hectare = 10000 m2)
    area_m2 = math.pi * radius_m**2
    density = round(len(neighbors) / (area_m2 / 10_000), 2)

    # Recommendation
    if homogeneity and homogeneity > 70 and avg_year and 1950 <= avg_year <= 1980:
        recommendation = (
            f"Quartier homogène {int(avg_year - 10)}-{int(avg_year + 10)} — risques polluants similaires probables"
        )
    elif len(neighbor_findings) > 3:
        recommendation = "Plusieurs voisins avec polluants détectés — diagnostic recommandé par similitude de quartier"
    elif not years:
        recommendation = "Années de construction voisines inconnues — données insuffisantes"
    else:
        recommendation = f"{len(neighbors)} bâtiment(s) dans un rayon de {radius_m}m"

    return {
        "buildings_in_radius": len(neighbors),
        "avg_construction_year": avg_year,
        "construction_era_distribution": era_dist,
        "avg_floors": avg_floors,
        "homogeneity_score": homogeneity,
        "dominant_type": dominant_type,
        "has_diagnosed_neighbors": len(diagnosed_building_ids),
        "neighbor_findings": neighbor_findings,
        "shadow_risk": shadow_risk,
        "density_score": density,
        "recommendation": recommendation,
        "coordinates_available": True,
    }


# ---------------------------------------------------------------------------
# FN2: detect_construction_activity
# ---------------------------------------------------------------------------


async def detect_construction_activity(db: AsyncSession, building_id: UUID, radius_m: float = 200) -> list[dict]:
    """Find nearby buildings with active interventions or recent work."""
    stmt = select(Building).where(Building.id == building_id)
    result = await db.execute(stmt)
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    if building.latitude is None or building.longitude is None:
        return []

    neighbors = await _get_nearby(db, building, radius_m)
    if not neighbors:
        return []

    neighbor_ids = [n.id for n in neighbors]
    neighbor_map = {n.id: n for n in neighbors}

    # Find active or recent interventions
    intervention_stmt = select(Intervention).where(
        Intervention.building_id.in_(neighbor_ids),
        Intervention.status.in_(["planned", "in_progress", "scheduled"]),
    )
    intervention_result = await db.execute(intervention_stmt)
    interventions = intervention_result.scalars().all()

    activities = []
    for intv in interventions:
        neighbor = neighbor_map.get(intv.building_id)
        if not neighbor:
            continue

        dist = (
            _haversine_m(
                building.latitude,
                building.longitude,
                neighbor.latitude,
                neighbor.longitude,
            )
            if neighbor.latitude and neighbor.longitude
            else 0
        )

        # Determine potential impact based on intervention type
        impact = "bruit"
        if intv.intervention_type in ("demolition", "structural"):
            impact = "bruit/vibrations"
        elif intv.intervention_type in ("asbestos_removal", "pollutant_removal"):
            impact = "poussière/contamination"
        elif intv.intervention_type in ("excavation", "foundation"):
            impact = "vibrations/subsidence"

        activities.append(
            {
                "building_id": str(intv.building_id),
                "address": neighbor.address if neighbor else None,
                "intervention_type": intv.intervention_type,
                "status": intv.status,
                "distance_m": round(dist, 1),
                "potential_impact": impact,
            }
        )

    # Sort by distance
    activities.sort(key=lambda a: a["distance_m"])
    return activities


# ---------------------------------------------------------------------------
# FN3: compute_neighborhood_risk_propagation
# ---------------------------------------------------------------------------


async def compute_neighborhood_risk_propagation(db: AsyncSession, building_id: UUID, radius_m: float = 50) -> dict:
    """Assess risks that propagate between buildings.

    - Fire propagation: distance to neighbors < 5m + material type
    - Structural: potential subsidence affecting multiple buildings
    - Environmental: contamination spreading from neighbor
    """
    stmt = select(Building).where(Building.id == building_id)
    result = await db.execute(stmt)
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    if building.latitude is None or building.longitude is None:
        return {
            "propagation_risks": [],
            "risk_count": 0,
            "highest_severity": None,
        }

    neighbors = await _get_nearby(db, building, radius_m)
    if not neighbors:
        return {
            "propagation_risks": [],
            "risk_count": 0,
            "highest_severity": None,
        }

    propagation_risks = []
    neighbor_ids = [n.id for n in neighbors]

    # Check for contaminated neighbors (diagnostics with threshold_exceeded samples)
    diag_stmt = select(Diagnostic).where(Diagnostic.building_id.in_(neighbor_ids))
    diag_result = await db.execute(diag_stmt)
    diagnostics = diag_result.scalars().all()
    diag_ids = [d.id for d in diagnostics]
    contaminated_neighbors = set()

    if diag_ids:
        sample_stmt = select(Sample).where(
            Sample.diagnostic_id.in_(diag_ids),
            Sample.threshold_exceeded.is_(True),
        )
        sample_result = await db.execute(sample_stmt)
        samples = sample_result.scalars().all()
        diag_to_building = {d.id: d.building_id for d in diagnostics}
        for s in samples:
            contaminated_neighbors.add(diag_to_building.get(s.diagnostic_id))

    for n in neighbors:
        dist = (
            _haversine_m(
                building.latitude,
                building.longitude,
                n.latitude,
                n.longitude,
            )
            if n.latitude and n.longitude
            else 999
        )

        # Fire propagation risk: close buildings
        if dist < 5:
            propagation_risks.append(
                {
                    "type": "fire_propagation",
                    "neighbor_id": str(n.id),
                    "neighbor_address": n.address,
                    "distance_m": round(dist, 1),
                    "severity": "high",
                    "description": "Distance < 5m — risque de propagation d'incendie",
                }
            )
        elif dist < 10:
            propagation_risks.append(
                {
                    "type": "fire_propagation",
                    "neighbor_id": str(n.id),
                    "neighbor_address": n.address,
                    "distance_m": round(dist, 1),
                    "severity": "medium",
                    "description": "Distance < 10m — propagation possible",
                }
            )

        # Environmental contamination risk
        if n.id in contaminated_neighbors and dist < 30:
            severity = "high" if dist < 10 else "medium"
            propagation_risks.append(
                {
                    "type": "environmental_contamination",
                    "neighbor_id": str(n.id),
                    "neighbor_address": n.address,
                    "distance_m": round(dist, 1),
                    "severity": severity,
                    "description": "Polluants détectés chez le voisin — contamination croisée possible",
                }
            )

        # Structural risk: very close buildings with deep foundations
        if dist < 15 and n.floors_above and n.floors_above > 5:
            propagation_risks.append(
                {
                    "type": "structural_subsidence",
                    "neighbor_id": str(n.id),
                    "neighbor_address": n.address,
                    "distance_m": round(dist, 1),
                    "severity": "low",
                    "description": "Bâtiment voisin élevé proche — surveiller tassement différentiel",
                }
            )

    # Sort by severity
    severity_order = {"high": 0, "medium": 1, "low": 2}
    propagation_risks.sort(key=lambda r: severity_order.get(r["severity"], 3))

    highest = propagation_risks[0]["severity"] if propagation_risks else None

    return {
        "propagation_risks": propagation_risks,
        "risk_count": len(propagation_risks),
        "highest_severity": highest,
    }
