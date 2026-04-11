# Brief T.1 — NDVI + indice végétation

## Context
- Satellite imagery available: Sentinel-2 (free, 10m resolution every 5 days)
- NDVI (Normalized Difference Vegetation Index) = (NIR - RED) / (NIR + RED), ranges 0-1
- VD/GE have significant greenspace — vegetation = wellbeing factor
- Data: Sentinel Hub API (free tier available)

## Outcome
For each building in VD/GE:
1. Fetch latest Sentinel-2 image (30 days rolling window)
2. Calculate NDVI for 200m radius around building
3. Classify: no_veg (0-0.2), low (0.2-0.4), moderate (0.4-0.6), high (0.6-1.0)
4. Calculate % coverage by class
5. Store in BuildingEnvironment + expose in UI

## Files to modify
- `backend/app/services/satellite_ndvi_service.py` — NEW
  - fetch_sentinel2_image(lat, lon) — Sentinel Hub API
  - calculate_ndvi(image_data) — numpy array processing
  - classify_vegetation(ndvi_raster) — classify by coverage %
  - cache 30 days
- `backend/app/models/building.py` — add fields: vegetation_coverage_percent, vegetation_class (enum: none/low/moderate/high)
- `backend/app/enrichment/enrichment_orchestrator.py` — add NDVI fetcher to dispatch
- `backend/app/api/router.py` — GET /buildings/{egid}/environment/vegetation
- `frontend/src/pages/BuildingDetail.tsx` — add "Environnement" card with vegetation badge + mini heatmap

## Patterns existants to copy
```python
# backend/app/services/geo_admin_service.py
# API fetch pattern + caching

# backend/app/services/swissbuildings3d_service.py
# Raster processing pattern (if similar)
```

## Constraints
1. Resolution: 10m (Sentinel-2) is sufficient for 200m radius assessment
2. Clouds: fetch latest image <30% cloud cover, fallback to older if all recent cloudy
3. Frequency: calculate on-demand, cache 30 days (satellite passes every ~5 days anyway)
4. No ML: pure NDVI calculation (deterministic)
5. Fallback: if no Sentinel2 available for region, use OSM tree density heuristic

## Commit message
```
feat(environment): satellite NDVI vegetation coverage + classification

- SatelliteNDVIService: Sentinel-2 fetch via Sentinel Hub API, NDVI calculation
- Vegetation classification: none/low/moderate/high with % coverage
- 30-day caching, <30% cloud cover filter
- Frontend: Environment card with vegetation badge
- Tests: 5 scenarios (fetch image clear, cloudy fallback, calculate NDVI, classify coverage, missing data)
```

## Tests
```bash
npm run test:inventory && npm run test:related && npm run gate:safe-to-start:plan
```

## Exit = done when
- [ ] T.1 — NDVI calculated for 3 test buildings (known vegetation)
- [ ] Classification correct (high veg = high %, low veg = low %)
- [ ] Caching works (no redundant API calls <30 days)
- [ ] Fallback to OSM if Sentinel-2 unavailable
- [ ] Frontend shows vegetation badge
- [ ] Tests green
