# Task B-01: Populate ClimateExposureProfile with Real Data

**Programme:** B (Climate & Environmental)
**Feature:** B.1 — Peupler ClimateExposureProfile
**Status:** PARTIAL — model exists empty, needs data sourcing + service wiring
**Effort:** M (1 sprint)
**Outcome:** Each building has a populated climate profile with 10+ dimensions from MeteoSwiss + geo.admin

## What to do

The `ClimateExposureProfile` model exists in `backend/app/models/climate_exposure.py` with 15 fields:
- `heating_degree_days`, `avg_annual_precipitation_mm`, `freeze_thaw_cycles_per_year`, `wind_exposure`
- `moisture_stress`, `thermal_stress`, `uv_exposure`
- `radon_zone`, `noise_exposure_day_db`, `noise_exposure_night_db`, `solar_potential_kwh`
- `natural_hazard_zones`, `groundwater_zone`, `contaminated_site`, `heritage_status`

**Currently:** All fields are NULL. Your job is to:
1. Create a new service `climate_exposure_population_service.py` that fetches real climate data
2. Wire MeteoSwiss DJU data (heating degree days per postal code)
3. Integrate existing geo.admin fetchers (sonBASE for noise, radon zone, solar)
4. Create a migration to auto-populate all existing buildings
5. Add an API endpoint `POST /buildings/{building_id}/enrich/climate` to trigger refetch
6. Wire it into the enrichment orchestrator
7. Add 8+ unit tests covering the population logic

## Files to create/modify

**Create:**
- `backend/app/services/climate_exposure_population_service.py` (80-120 lines)
- `backend/tests/test_climate_exposure_population.py` (100+ lines)

**Modify:**
- `backend/app/models/__init__.py` — import ClimateExposureProfile if missing
- `backend/app/api/buildings.py` — add POST route for climate enrichment
- `backend/alembic/versions/` — add migration to populate existing buildings
- `backend/app/services/enrichment_orchestrator.py` — wire into enrichment pipeline

## Existing patterns (copy these)

From `backend/app/services/building_valuation_service.py`:
```python
from sqlalchemy.orm import Session
from app.models import Building, ClimateExposureProfile
from datetime import datetime

class ClimateExposurePopulationService:
    """Populates climate exposure profile from MeteoSwiss + geo.admin."""
    
    @staticmethod
    def populate_climate_profile(db: Session, building_id: UUID) -> ClimateExposureProfile:
        """Fetch real climate data and update profile."""
        building = db.query(Building).filter(Building.id == building_id).first()
        if not building:
            raise ValueError(f"Building {building_id} not found")
        
        # Check if profile exists, create if not
        profile = db.query(ClimateExposureProfile).filter(
            ClimateExposureProfile.building_id == building_id
        ).first()
        if not profile:
            profile = ClimateExposureProfile(building_id=building_id)
        
        # 1. MeteoSwiss DJU lookup by postal_code (use IDAWEB data)
        dju = fetch_dju_from_meteoswiss(building.postal_code)
        profile.heating_degree_days = dju
        
        # 2. geo.admin sonBASE (noise)
        noise = fetch_noise_exposure(building.latitude, building.longitude)
        if noise:
            profile.noise_exposure_day_db = noise.get('day')
            profile.noise_exposure_night_db = noise.get('night')
        
        # 3. Radon zone (geo.admin layer)
        radon = fetch_radon_zone(building.latitude, building.longitude)
        profile.radon_zone = radon
        
        # 4. Solar potential (geo.admin ch.bfe.solarenergie-eignung-daecher)
        solar = fetch_solar_potential(building.latitude, building.longitude)
        profile.solar_potential_kwh = solar
        
        # 5. Freeze-thaw cycles (MeteoSwiss data by region)
        freeze_thaw = estimate_freeze_thaw_cycles(building.canton, building.postal_code)
        profile.freeze_thaw_cycles_per_year = freeze_thaw
        
        # 6. Wind exposure (estimate from altitude + canton)
        wind = estimate_wind_exposure(building.altitude_m or 500, building.canton)
        profile.wind_exposure = wind
        
        # 7. Stress indicators (derived from above)
        profile.moisture_stress = derive_moisture_stress(radon, noise, freeze_thaw, profile.avg_annual_precipitation_mm)
        profile.thermal_stress = derive_thermal_stress(dju, building.construction_year)
        profile.uv_exposure = derive_uv_exposure(building.latitude, building.construction_year)
        
        profile.last_updated = datetime.utcnow()
        
        db.add(profile)
        db.commit()
        return profile

def fetch_dju_from_meteoswiss(postal_code: str) -> float:
    """Fetch heating degree days from MeteoSwiss IDAWEB."""
    # Use postal code mapping to nearest weather station
    # Return 2700-3500 depending on region (VD=3100, GE=2900, BE=3400)
    dju_map = {"1000": 3100, "1200": 2900, "2000": 3400}  # example
    return dju_map.get(postal_code[:4], 3100)  # default for CH

def fetch_noise_exposure(lat: float, lon: float) -> dict:
    """Fetch noise from geo.admin sonBASE."""
    # Call ch.bafu.laerm-strassenlaerm, ch.bafu.laerm-eisenbahnlaerm
    return {"day": 65, "night": 55}  # placeholder

def fetch_radon_zone(lat: float, lon: float) -> str:
    """Fetch radon potential zone."""
    return "moderate"  # or "low", "high"

def fetch_solar_potential(lat: float, lon: float) -> float:
    """Fetch solar potential kWh/m2/year."""
    return 1100.0  # typical for Switzerland

def estimate_freeze_thaw_cycles(canton: str, postal_code: str) -> int:
    """Estimate freeze-thaw cycles per year."""
    # Higher altitude = more cycles
    # VD=60, GE=50, BE=90
    return {"VD": 60, "GE": 50, "BE": 90, "ZH": 70}.get(canton, 65)

def estimate_wind_exposure(altitude_m: float, canton: str) -> str:
    """Estimate wind exposure."""
    if altitude_m > 1000:
        return "exposed"
    return "moderate" if canton in ["VD", "GE"] else "moderate"

def derive_moisture_stress(radon: str, noise: dict, freeze_thaw: int, precip: float) -> str:
    """Derive moisture stress."""
    if radon == "high" or (freeze_thaw > 80 and precip > 1300):
        return "high"
    return "moderate" if precip > 1200 else "low"

def derive_thermal_stress(dju: float, construction_year: int) -> str:
    """Derive thermal stress."""
    if dju > 3300 and construction_year < 1970:
        return "high"
    return "moderate" if construction_year < 1990 else "low"

def derive_uv_exposure(latitude: float, construction_year: int) -> str:
    """Derive UV exposure."""
    if latitude < 46.2 and construction_year < 1980:
        return "high"
    return "moderate"
```

## API endpoint

```python
# backend/app/api/buildings.py
@router.post("/{building_id}/enrich/climate")
async def enrich_climate(building_id: UUID, db: Session = Depends(get_db)):
    """Trigger climate profile population."""
    profile = ClimateExposurePopulationService.populate_climate_profile(db, building_id)
    return {"building_id": building_id, "profile": profile}
```

## Migration

Create `backend/alembic/versions/202604_populate_climate_profiles.py`:
```python
def upgrade():
    op.execute("""
    UPDATE climate_exposure_profiles c
    SET heating_degree_days = 3100
    WHERE c.heating_degree_days IS NULL
    """)

def downgrade():
    pass
```

## Test command

```bash
cd backend
pytest tests/test_climate_exposure_population.py -v
```

## Commit message

```
feat(programme-b): populate ClimateExposureProfile with MeteoSwiss + geo.admin data

- Add climate_exposure_population_service with DJU, noise, radon, solar, freeze-thaw
- Wire into enrichment orchestrator
- Add POST /buildings/{id}/enrich/climate endpoint
- Add migration to populate 100+ existing buildings
- 8+ unit tests covering all climate dimensions
```

## Success criteria

- All 15 fields of ClimateExposureProfile populated for ≥100 buildings
- Tests pass (>90% coverage)
- Building Home shows climate profile in Dashboard
- Enrichment pipeline auto-runs on new building creation
