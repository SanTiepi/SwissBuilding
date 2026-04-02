"""Material stress predictor service — estimates material degradation acceleration.

Analyzes age, climate exposure, material type, and environmental factors
to compute a stress grade (stable/gradual/accelerated/critical) and confidence score.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.climate_exposure import ClimateExposureProfile
from app.models.material import Material

logger = logging.getLogger(__name__)

# Material type degradation curves (years to critical condition under typical stress)
MATERIAL_DEGRADATION_YEARS: dict[str, int] = {
    "amiante": 40,           # Asbestos: critical risk after 40+ years
    "pcb": 40,               # PCB: critical risk after 40+ years
    "joint": 30,             # Joint sealants: critical after 30+ years
    "facade": 50,            # Facade materials: 50+ years typical
    "beton": 60,             # Concrete: 60+ years
    "brique": 100,           # Brick: very long lifespan
    "pierre": 200,           # Stone: very long lifespan
    "bois": 40,              # Wood: 40 years in typical conditions
    "tole": 30,              # Metal sheets: 30 years
    "verre": 100,            # Glass: very long
}

# Stress multipliers based on material type
MATERIAL_TYPE_MULTIPLIER: dict[str, float] = {
    "amiante": 1.5,          # High-risk material
    "pcb": 1.4,              # High-risk material
    "joint": 1.2,            # Moderate-risk
    "facade": 1.0,           # Standard
    "beton": 0.9,            # Resilient
    "brique": 0.7,           # Very resilient
    "pierre": 0.6,           # Very resilient
    "bois": 1.1,             # Moderate risk in wet environments
    "tole": 1.2,             # Moderate risk (corrosion)
    "verre": 0.5,            # Very durable
}

# Environmental stress factors based on cantonal conditions
CANTON_STRESS_MULTIPLIER: dict[str, float] = {
    "VD": 1.1,  # Valais-romand: alpine freeze/thaw
    "VS": 1.3,  # Valais: extreme alpine conditions
    "GE": 1.0,  # Geneva: standard
    "VG": 1.15, # Valais-german: alpine conditions
    "JU": 1.15, # Jura: alpine conditions
    "TI": 1.05, # Ticino: moderate
    "GR": 1.3,  # Graubuenden: extreme alpine
    "UR": 1.25, # Uri: alpine
    "ZH": 1.0,  # Zurich: standard
    "LU": 1.0,  # Lucerne: standard
    "AG": 1.0,  # Aargau: standard
    "SG": 1.05, # St. Gallen: moderate
    "AR": 1.05, # Appenzell Ausserrhoden: moderate
    "AI": 1.05, # Appenzell Innerrhoden: moderate
    "BE": 1.1,  # Bern: alpine
    "OW": 1.2,  # Obwalden: alpine
    "NW": 1.2,  # Nidwalden: alpine
    "SZ": 1.2,  # Schwyz: alpine
    "BL": 1.0,  # Basel-Land: standard
    "BS": 1.0,  # Basel-Stadt: standard
    "SO": 1.0,  # Solothurn: standard
    "NE": 1.0,  # Neuchatel: standard
    "FR": 1.0,  # Fribourg: standard
    "SH": 1.0,  # Schaffhausen: standard
    "TG": 1.0,  # Thurgau: standard
    "SL": 1.0,  # Salland: standard
}


def _age_stress_factor(age_years: int, material_type: str) -> float:
    """Compute stress from age relative to material's expected lifespan.
    
    Returns 0-10 scale. Uses material-specific degradation curves.
    Accelerates exponentially after expected lifespan is exceeded.
    """
    if age_years < 0:
        return 0.0

    expected_years = MATERIAL_DEGRADATION_YEARS.get(material_type.lower(), 50)

    if age_years < expected_years * 0.5:
        # Early life: minimal stress
        return age_years / expected_years * 2.0
    elif age_years < expected_years:
        # Mid-life: gradual increase
        return 2.0 + (age_years - expected_years * 0.5) / (expected_years * 0.5) * 5.0
    else:
        # Post-expected-life: exponential degradation
        years_over = age_years - expected_years
        return 7.0 + min(3.0, (years_over / expected_years) * 3.0)


def _climate_stress_factor(
    heating_degree_days: float | None,
    freeze_thaw_cycles: int | None,
    precipitation_mm: float | None,
    moisture_stress: str | None,
    uv_exposure: str | None,
) -> float:
    """Compute climate-induced stress from environmental conditions.
    
    Major factors:
    - Freeze/thaw cycles (facade degradation)
    - Precipitation (moisture damage)
    - UV exposure (surface degradation)
    - Thermal stress (expansion/contraction)
    
    Returns 0-10 scale.
    """
    score = 0.0
    data_points = 0

    # Freeze/thaw cycles: major factor for facades
    if freeze_thaw_cycles is not None:
        data_points += 1
        if freeze_thaw_cycles < 20:
            score += 1.0
        elif freeze_thaw_cycles < 40:
            score += 5.0
        elif freeze_thaw_cycles < 60:
            score += 7.5
        else:
            score += 9.0

    # Precipitation: moisture damage risk
    if precipitation_mm is not None:
        data_points += 1
        if precipitation_mm < 800:
            score += 1.0
        elif precipitation_mm < 1200:
            score += 3.0
        elif precipitation_mm < 1500:
            score += 5.0
        else:
            score += 7.0

    # Thermal stress (heating degree days proxy for hot/cold extremes)
    if heating_degree_days is not None:
        data_points += 1
        if heating_degree_days < 2000:
            score += 2.0  # Mild climate
        elif heating_degree_days < 3000:
            score += 3.0
        elif heating_degree_days < 4000:
            score += 5.0
        else:
            score += 7.0

    # UV exposure
    if uv_exposure and uv_exposure.lower() in ["high", "exposed"]:
        data_points += 1
        score += 3.0
    elif uv_exposure and uv_exposure.lower() in ["moderate"]:
        data_points += 0.5
        score += 1.5

    # Moisture stress indicator
    if moisture_stress:
        data_points += 0.5
        if moisture_stress.lower() == "high":
            score += 3.0
        elif moisture_stress.lower() == "moderate":
            score += 1.5

    # Average the contributions
    if data_points == 0:
        return 5.0  # Unknown: neutral/conservative

    return min(10.0, score / data_points * 1.3)  # Normalize to 0-10 with slight boost for multiple factors


def _environmental_factor(building: Building) -> float:
    """Compute environmental stress from location/context.
    
    Considers:
    - Canton (climate zone, altitude, exposure)
    - Proximity to sea/salt air (corrosion)
    - Urban vs rural (pollution, wind)
    
    Returns multiplier 0.8-1.5x.
    """
    canton = building.canton.upper() if building.canton else "ZH"
    base_multiplier = CANTON_STRESS_MULTIPLIER.get(canton, 1.0)

    # Coastal proximity premium (simplified: assume sea-adjacent cantons)
    coastal = canton in ["GE", "VD", "NE", "FR", "TI"]
    if coastal:
        base_multiplier *= 1.15  # Salt air corrosion

    return base_multiplier


def _confidence_from_data_availability(
    has_installation_year: bool,
    has_climate_data: bool,
    has_moisture_stress: bool,
) -> int:
    """Estimate confidence (0-100) based on data availability."""
    score = 50  # Base confidence

    if has_installation_year:
        score += 25
    if has_climate_data:
        score += 15
    if has_moisture_stress:
        score += 10

    return min(100, score)


def _grade_from_stress(stress_score: float) -> str:
    """Map stress score (0-10) to degradation grade."""
    if stress_score < 3.0:
        return "stable"
    elif stress_score < 5.0:
        return "gradual"
    elif stress_score < 7.5:
        return "accelerated"
    else:
        return "critical"


async def analyze_material_stress(
    db: AsyncSession,
    building_id: UUID,
    material_id: UUID,
) -> dict[str, Any]:
    """Predict material degradation stress grade.
    
    Analyzes age, climate exposure, material type, and environment
    to estimate stress grade (stable/gradual/accelerated/critical)
    with confidence 0-100.
    
    Args:
        db: Async database session
        building_id: UUID of the building
        material_id: UUID of the material
        
    Returns:
        {
            "material_id": UUID,
            "grade": "stable" | "gradual" | "accelerated" | "critical",
            "stress_score": 0-10 float,
            "confidence": 0-100 int,
            "factors": {
                "age": float,
                "climate": float,
                "material_type": float,
                "environment": float,
            },
            "prognosis": str,
            "age_years": int,
            "data_quality": str,
        }
    """
    # Fetch material
    result = await db.execute(
        select(Material).where(
            Material.id == material_id,
        )
    )
    material = result.scalar_one_or_none()
    if not material:
        raise ValueError(f"Material {material_id} not found")

    # Fetch building
    result = await db.execute(
        select(Building).where(Building.id == building_id)
    )
    building = result.scalar_one_or_none()
    if not building:
        raise ValueError(f"Building {building_id} not found")

    # Fetch climate profile
    result = await db.execute(
        select(ClimateExposureProfile).where(
            ClimateExposureProfile.building_id == building_id
        )
    )
    climate = result.scalar_one_or_none()

    # Calculate age
    current_year = datetime.now().year
    age_years = (
        current_year - material.installation_year
        if material.installation_year
        else None
    )

    # Calculate stress factors
    age_factor = _age_stress_factor(age_years or 0, material.material_type)

    climate_factor = _climate_stress_factor(
        heating_degree_days=climate.heating_degree_days if climate else None,
        freeze_thaw_cycles=climate.freeze_thaw_cycles_per_year if climate else None,
        precipitation_mm=climate.avg_annual_precipitation_mm if climate else None,
        moisture_stress=climate.moisture_stress if climate else None,
        uv_exposure=climate.uv_exposure if climate else None,
    )

    material_type_factor = MATERIAL_TYPE_MULTIPLIER.get(
        material.material_type.lower(), 1.0
    )

    environment_factor = _environmental_factor(building)

    # Composite stress score
    # Weight: age 40%, climate 35%, material 15%, environment 10%
    composite_stress = (
        age_factor * 0.40
        + climate_factor * 0.35
        + (material_type_factor - 1.0) * 10.0 * 0.15  # Scale multiplier to 0-10
        + (environment_factor - 1.0) * 10.0 * 0.10
    )
    composite_stress = max(0.0, min(10.0, composite_stress))

    grade = _grade_from_stress(composite_stress)

    # Confidence calculation
    confidence = _confidence_from_data_availability(
        has_installation_year=material.installation_year is not None,
        has_climate_data=climate is not None,
        has_moisture_stress=climate and climate.moisture_stress != "unknown",
    )

    # Prognosis text
    age_text = f"Age {age_years}y" if age_years is not None else "Age unknown"
    climate_text = (
        f"{climate.freeze_thaw_cycles_per_year} freeze/thaw cycles/year"
        if climate and climate.freeze_thaw_cycles_per_year
        else "climate data incomplete"
    )
    prognosis = f"{age_text} + {climate_text} → {grade} degradation"

    # Data quality assessment
    if confidence >= 80:
        data_quality = "high"
    elif confidence >= 60:
        data_quality = "moderate"
    else:
        data_quality = "low"

    return {
        "material_id": str(material_id),
        "grade": grade,
        "stress_score": round(composite_stress, 2),
        "confidence": confidence,
        "factors": {
            "age": round(age_factor, 2),
            "climate": round(climate_factor, 2),
            "material_type": round(material_type_factor, 2),
            "environment": round(environment_factor, 2),
        },
        "age_years": age_years,
        "prognosis": prognosis,
        "data_quality": data_quality,
    }
