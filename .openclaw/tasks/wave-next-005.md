# Task: Activate 24 geo.admin layers

## Commit message
feat(wave-next): activate all 24 geo.admin fetchers in enrichment pipeline

## What to do
The enrichment orchestrator imports 24+ geo.admin fetchers (solar, thermal, monuments, radon, contaminated, forest, agricultural, military, accident, flood, seismic, noise variants, etc.) but only ~6 are actively called in the pipeline. Wire ALL fetchers into the orchestration so results are persisted in enrichment_meta and BuildingGeoContext. Gracefully handle individual fetcher failures (timeout/retry) so one failure doesn't block the whole enrichment.

## Files to modify
- `backend/app/services/enrichment/orchestrator.py` (add calls to all 24 fetchers in the enrichment pipeline; lines ~300-400)
- `backend/tests/test_geo_enrichment_activation.py` (add specific test cases for each newly activated fetcher)

## Existing patterns to follow

From `orchestrator.py` (current fetchers already called):
```python
enrichment_meta["solar_potential"] = await fetch_solar_potential(coords, session=session)
enrichment_meta["thermal_networks"] = await fetch_thermal_networks(coords, session=session)
enrichment_meta["noise_data"] = await fetch_noise_data(coords, session=session)
# Pattern: await + assign to dict key, wrapped in try/except for failures
```

From the import block (lines 26-50):
```python
from app.services.enrichment.geo_admin_fetchers import (
    fetch_accident_sites,
    fetch_agricultural_zones,
    fetch_aircraft_noise,
    fetch_broadband,
    fetch_building_zones,
    fetch_contaminated_sites,
    fetch_ev_charging,
    fetch_flood_zones,
    fetch_forest_reserves,
    fetch_groundwater_zones,
    fetch_heritage_status,
    fetch_military_zones,
    fetch_mobile_coverage,
    fetch_natural_hazards,
    fetch_noise_data,
    fetch_protected_monuments,
    fetch_radon_risk,
    fetch_railway_noise,
    fetch_seismic_zone,
    fetch_solar_potential,
    fetch_thermal_networks,
    fetch_transport_quality,
    fetch_water_protection,
)
```

## Acceptance criteria
- [ ] All 24 geo.admin fetchers called during building enrichment
- [ ] Results persisted in enrichment_meta / BuildingGeoContext
- [ ] Fetcher failures don't block enrichment (graceful degradation with try/except)
- [ ] New tests added for each fetcher activation (or update existing test coverage)
- [ ] Existing enrichment tests still pass (no regression)

## Test command
cd backend && python -m pytest tests/test_geo_enrichment_activation.py -v

## Rules
- Do NOT modify files outside the list above
- Do NOT push
- Follow existing try/except + timeout pattern for each fetcher call
- Commit with the message above if tests pass
