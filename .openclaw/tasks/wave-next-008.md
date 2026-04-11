# Task: Populate ClimateExposureProfile

## Commit message
feat(wave-next): populate ClimateExposureProfile from enrichment data

## What to do
The ClimateExposureProfile model has 10+ fields that are currently empty. Wire up the enrichment orchestrator to populate ALL fields from existing fetchers after enrichment completes: radon_zone (from geo.admin radon), heating_degree_days (from osm_fetchers climate), freeze_thaw_cycles (from frost_days), moisture/thermal/uv stress indicators (computed from climate data), noise_exposure (from geo.admin noise), natural_hazard_zones, and altitude. Compute stress indicators (low/moderate/high) based on thresholds.

## Files to modify
- `backend/app/services/enrichment/orchestrator.py` (add mapping logic after enrichment completes, around line 400+)
- `backend/app/models/climate_exposure.py` (NO CHANGES — model already exists with correct schema)
- `backend/tests/test_climate_exposure_population.py` (add/update population tests with computed values)

## Existing patterns to follow

From `orchestrator.py` (example of how enrichment_meta is populated):
```python
enrichment_meta["solar_potential"] = await fetch_solar_potential(coords, session=session)
enrichment_meta["thermal_networks"] = await fetch_thermal_networks(coords, session=session)
# After all fetchers: persist to BuildingGeoContext or enrichment_meta dict
```

From `climate_exposure.py` model (fields to populate):
```python
radon_zone = Column(String(50), nullable=True)
noise_exposure_day_db = Column(Float, nullable=True)
noise_exposure_night_db = Column(Float, nullable=True)
solar_potential_kwh = Column(Float, nullable=True)
natural_hazard_zones = Column(JSON, nullable=True)  # [{type, level}]
heating_degree_days = Column(Float, nullable=True)
avg_annual_precipitation_mm = Column(Float, nullable=True)
freeze_thaw_cycles_per_year = Column(Integer, nullable=True)
moisture_stress = Column(String(20), nullable=False, default="unknown")  # low/moderate/high/unknown
thermal_stress = Column(String(20), nullable=False, default="unknown")
uv_exposure = Column(String(20), nullable=False, default="unknown")
```

Data sources already fetched (used in orchestrator):
- osm_fetchers: `fetch_climate_data()` returns temperature, precipitation, frost_days, sunshine_hours, HDD
- geo_admin_fetchers: `fetch_radon_risk()`, `fetch_noise_data()`, `fetch_natural_hazards()`

## Acceptance criteria
- [ ] All ClimateExposureProfile fields populated during enrichment (radon, heating_degree_days, freeze_thaw, noise, hazards, altitude, stress indicators)
- [ ] Stress indicators computed (low/moderate/high) based on climate thresholds
- [ ] Data_sources field tracks which sources provided each field
- [ ] Tests for population logic pass (with realistic test values)
- [ ] Existing climate tests still pass (no regression)

## Test command
cd backend && python -m pytest tests/test_climate_exposure_population.py -v

## Rules
- Do NOT modify files outside the list above
- Do NOT push
- Follow existing enrichment patterns (try/except, logging, source tracking)
- Commit with the message above if tests pass
