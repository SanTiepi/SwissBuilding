"""BatiConnect -- RegBL Intelligence Service.

Deep analysis of RegBL/GWR (Registre federal des batiments) data stored
in building.source_metadata_json["regbl_data"]. Extracts construction
intelligence, physical characteristics, energy profile, renovation
status, and data quality metrics.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# GWR code lookups (subset of official codes)
# ---------------------------------------------------------------------------
_HEATING_TYPE_LABELS: dict[str, str] = {
    "7400": "Pas de chauffage",
    "7410": "Poele individuel",
    "7420": "Chauffage central",
    "7430": "Chauffage a distance",
    "7436": "Pompe a chaleur",
    "7440": "Chauffage electrique",
    "7450": "Autre chauffage",
    "7499": "Inconnu",
}

_ENERGY_SOURCE_LABELS: dict[str, str] = {
    "7500": "Pas de source",
    "7510": "Air",
    "7511": "Geothermie (sonde)",
    "7512": "Geothermie (eau)",
    "7513": "Eau (lac/riviere)",
    "7520": "Mazout",
    "7530": "Gaz",
    "7540": "Bois",
    "7541": "Bois (buches)",
    "7542": "Bois (copeaux)",
    "7543": "Bois (pellets)",
    "7550": "Dechets",
    "7560": "Electricite",
    "7570": "Soleil (thermique)",
    "7580": "Chauffage a distance",
    "7598": "Autre",
    "7599": "Inconnu",
}

_BUILDING_CATEGORY_LABELS: dict[str, str] = {
    "1010": "Habitation provisoire",
    "1020": "Maison individuelle",
    "1030": "Maison a 2 logements",
    "1040": "Maison a 3+ logements",
    "1060": "Habitation avec usage annexe",
    "1080": "Batiment partiellement habite",
}

_BUILDING_CLASS_LABELS: dict[str, str] = {
    "1110": "Batiment d'habitation",
    "1121": "Batiment avec usage commercial partiel",
    "1122": "Batiment avec usage agricole partiel",
    "1130": "Batiment d'habitation collectif",
    "1211": "Hotel",
    "1212": "Autre hebergement",
    "1220": "Batiment administratif",
    "1230": "Batiment commercial",
    "1241": "Batiment de transport",
    "1242": "Garage",
    "1251": "Batiment industriel",
    "1252": "Reservoir",
    "1261": "Batiment culturel",
    "1262": "Batiment religieux",
    "1263": "Batiment sanitaire",
    "1264": "Batiment d'enseignement",
    "1271": "Batiment agricole",
    "1272": "Batiment forestier",
    "1275": "Jardin d'hiver",
    "1276": "Batiment de sport",
    "1278": "Batiment de pompiers",
}

_ERA_LABELS: dict[str, str] = {
    "pre_1900": "Avant 1900 — batiment historique",
    "1900_1945": "1900-1945 — entre-deux-guerres",
    "1946_1960": "1946-1960 — reconstruction",
    "1961_1980": "1961-1980 — boom immobilier",
    "1981_2000": "1981-2000 — premieres normes energetiques",
    "2001_2010": "2001-2010 — normes SIA modernisees",
    "post_2010": "Apres 2010 — normes energetiques strictes",
}

# Total number of RegBL fields we track
_REGBL_TOTAL_FIELDS = 39

# Critical fields for building intelligence
_CRITICAL_FIELDS = [
    "construction_year",
    "floors",
    "dwellings",
    "heating_type_code",
    "energy_source_code",
    "building_category_code",
    "living_area_m2",
]


# ---------------------------------------------------------------------------
# Era classification
# ---------------------------------------------------------------------------


def _classify_era(year: int | None) -> str | None:
    """Classify construction year into architectural era."""
    if year is None:
        return None
    if year < 1900:
        return "pre_1900"
    if year <= 1945:
        return "1900_1945"
    if year <= 1960:
        return "1946_1960"
    if year <= 1980:
        return "1961_1980"
    if year <= 2000:
        return "1981_2000"
    if year <= 2010:
        return "2001_2010"
    return "post_2010"


def _decade_label(year: int | None) -> str | None:
    """Return decade label like '1960s'."""
    if year is None:
        return None
    decade = (year // 10) * 10
    return f"{decade}s"


# ---------------------------------------------------------------------------
# Renovation need score
# ---------------------------------------------------------------------------

_OIL_GAS_CODES = {"7520", "7530"}  # mazout, gaz


def _compute_renovation_need_score(
    construction_year: int | None,
    renovation_year: int | None,
    heating_type_code: str | None,
    energy_source_code: str | None,
) -> int:
    """Compute a 0-100 renovation need score.

    Higher = more likely to need renovation.
    """
    score = 0
    current_year = date.today().year

    # Age factor (0-40 points)
    if construction_year:
        age = current_year - construction_year
        if age > 80:
            score += 40
        elif age > 50:
            score += 30
        elif age > 30:
            score += 20
        elif age > 15:
            score += 10

    # No known renovation (0-25 points)
    if construction_year and not renovation_year:
        age = current_year - construction_year
        if age > 30:
            score += 25
        elif age > 20:
            score += 15
    elif renovation_year:
        years_since = current_year - renovation_year
        if years_since > 30:
            score += 20
        elif years_since > 20:
            score += 10

    # Fossil heating (0-20 points)
    source = str(energy_source_code or "")
    if source in _OIL_GAS_CODES:
        score += 20

    # Old heating system type (0-15 points)
    heating = str(heating_type_code or "")
    if heating in ("7410", "7440"):  # individual stove or electric
        score += 15
    elif heating == "7420" and source in _OIL_GAS_CODES:  # central + fossil
        score += 10

    return min(score, 100)


# ---------------------------------------------------------------------------
# Insight generation
# ---------------------------------------------------------------------------


def _generate_insights(
    construction_year: int | None,
    renovation_year: int | None,
    energy_source_code: str | None,
    heating_type_code: str | None,
    dwellings: int | None,
    living_area_m2: float | None,
    floors: int | None,
) -> list[str]:
    """Generate human-readable intelligence insights."""
    insights: list[str] = []
    current_year = date.today().year
    source = str(energy_source_code or "")
    heating = str(heating_type_code or "")

    # Fossil fuel warning
    if source in _OIL_GAS_CODES:
        label = _ENERGY_SOURCE_LABELS.get(source, "combustible fossile")
        insights.append(f"Chauffage au {label.lower()} — obligation de remplacement probable avant 2030")

    # No renovation since construction
    if construction_year and not renovation_year:
        age = current_year - construction_year
        if age > 30:
            insights.append(f"Aucune renovation connue depuis la construction ({construction_year})")

    # Old renovation
    if renovation_year and (current_year - renovation_year) > 25:
        insights.append(f"Derniere renovation en {renovation_year} — {current_year - renovation_year} ans")

    # Electric heating (inefficient)
    if heating == "7440":
        insights.append("Chauffage electrique direct — mauvaise performance energetique")

    # Living area vs dwellings
    if living_area_m2 and dwellings and dwellings > 0:
        avg = living_area_m2 / dwellings
        if construction_year:
            era = _classify_era(construction_year)
            era_label = _ERA_LABELS.get(era or "", "")
            if era_label:
                insights.append(
                    f"Surface habitable {living_area_m2:.0f}m2 pour {dwellings} logement(s) — "
                    f"standard pour l'epoque ({era_label.split(' — ')[0]})"
                )
            else:
                insights.append(f"Surface habitable {living_area_m2:.0f}m2 pour {dwellings} logement(s)")
        if avg < 40:
            insights.append(f"Surface moyenne par logement faible ({avg:.0f}m2)")

    # Multi-story without elevator indication
    if floors and floors >= 5:
        insights.append(f"Batiment de {floors} etages — verifier conformite accessibilite")

    return insights


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------


async def analyze_regbl_data(db: AsyncSession, building_id: UUID) -> dict[str, Any]:
    """Deep analysis of RegBL/GWR data stored in enrichment_meta.

    Returns:
        {
            construction: {year, decade, era_label, building_class, building_category},
            physical: {floors, dwellings, living_area_m2, rooms_estimate},
            energy: {heating_type, energy_source, energy_label, heating_age_estimate},
            renovation: {
                last_renovation_year,
                renovation_status,
                renovation_need_score
            },
            data_quality: {
                fields_available, fields_total,
                completeness_pct,
                missing_critical
            },
            insights: [str]
        }
    """
    # Load building
    stmt = select(Building).where(Building.id == building_id)
    row = await db.execute(stmt)
    building = row.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    meta: dict[str, Any] = building.source_metadata_json or {}
    regbl: dict[str, Any] = meta.get("regbl_data", {})

    # --- Construction ---
    year = regbl.get("construction_year") or building.construction_year
    era = _classify_era(year)
    construction = {
        "year": year,
        "decade": _decade_label(year),
        "era_label": _ERA_LABELS.get(era) if era else None,
        "building_class": _BUILDING_CLASS_LABELS.get(str(regbl.get("building_class_code", ""))),
        "building_category": _BUILDING_CATEGORY_LABELS.get(str(regbl.get("building_category_code", ""))),
    }

    # --- Physical ---
    floors = regbl.get("floors") or building.floors_above
    dwellings = regbl.get("dwellings")
    living_area = regbl.get("living_area_m2") or (building.surface_area_m2 if building.surface_area_m2 else None)
    # Rough rooms estimate: GWR dwelling_rooms if available
    rooms_estimate = None
    if regbl.get("dwelling_rooms"):
        rooms_list = regbl["dwelling_rooms"]
        if isinstance(rooms_list, list):
            rooms_estimate = sum(r for r in rooms_list if isinstance(r, (int, float)))

    physical = {
        "floors": floors,
        "dwellings": dwellings,
        "living_area_m2": living_area,
        "rooms_estimate": rooms_estimate,
    }

    # --- Energy ---
    heating_code = regbl.get("heating_type_code")
    energy_code = regbl.get("energy_source_code")
    energy = {
        "heating_type": _HEATING_TYPE_LABELS.get(str(heating_code or "")),
        "energy_source": _ENERGY_SOURCE_LABELS.get(str(energy_code or "")),
        "heating_type_code": str(heating_code) if heating_code else None,
        "energy_source_code": str(energy_code) if energy_code else None,
    }

    # --- Renovation ---
    renovation_year = regbl.get("renovation_period_code") or building.renovation_year
    # Determine status
    if renovation_year:
        reno_status = "complete"
    elif year and (date.today().year - (year or 2000)) > 30:
        reno_status = "unknown"
    else:
        reno_status = "unknown"

    if year and not renovation_year:
        reno_status = "never" if (date.today().year - year) > 20 else "unknown"

    renovation_need = _compute_renovation_need_score(
        year, renovation_year if isinstance(renovation_year, int) else None, heating_code, energy_code
    )

    renovation = {
        "last_renovation_year": renovation_year if isinstance(renovation_year, int) else None,
        "renovation_status": reno_status,
        "renovation_need_score": renovation_need,
    }

    # --- Data quality ---
    # Count non-internal fields available in regbl_data
    available_fields = [k for k in regbl if not k.startswith("_") and k != "egid_confidence"]
    missing_critical = [f for f in _CRITICAL_FIELDS if f not in regbl]
    completeness = round(len(available_fields) / _REGBL_TOTAL_FIELDS * 100, 1) if _REGBL_TOTAL_FIELDS > 0 else 0.0

    data_quality = {
        "fields_available": len(available_fields),
        "fields_total": _REGBL_TOTAL_FIELDS,
        "completeness_pct": completeness,
        "missing_critical": missing_critical,
    }

    # --- Insights ---
    insights = _generate_insights(
        year,
        renovation_year if isinstance(renovation_year, int) else None,
        energy_code,
        heating_code,
        dwellings,
        living_area,
        floors,
    )

    return {
        "construction": construction,
        "physical": physical,
        "energy": energy,
        "renovation": renovation,
        "data_quality": data_quality,
        "insights": insights,
    }
