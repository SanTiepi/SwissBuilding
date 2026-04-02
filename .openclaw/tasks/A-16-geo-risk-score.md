# Task A.16 — Geo Risk Score Composite Service

## What to do
Create a new service `geo_risk_score_service.py` that computes a composite geospatial risk score (0-100) for each building.
The score combines:
- Inondation risk (ch.bafu.gefahrenkarte-hochwasser)
- Seismic class (ch.bafu.erdbeben-baugrundklassen)
- Grele frequency (swisscom/mobiliar historical data or proxy)
- Contaminated sites nearby (ch.bafu.altlasten-kataster within 500m)
- Radon potential (geological type)

Each sub-score is 0-10, weighted equally, combined to 0-100.

Add API route: `GET /buildings/{building_id}/geo-risk-score`

## Files to create/modify
- **Create:** `backend/app/services/geo_risk_score_service.py` (~150 lines)
- **Modify:** `backend/app/api/geo_context.py` - add GET route (10 lines)
- **Modify:** `backend/app/models/__init__.py` - if needed for import
- **Create:** `backend/tests/test_geo_risk_score.py` (~80 lines, 4 tests)
- **Modify:** `backend/app/models/building_geo_context.py` - add optional `geo_risk_score` JSON field (1 line)

## Existing patterns to copy

From `backend/app/services/amenity_analysis_service.py`:
```python
def _score_from_count(count: int, threshold: int) -> float:
    """Convert count to 0-10 score based on threshold."""
    if count <= 0:
        return 0.0
    return min(10.0, round(count / threshold * 10.0, 1))

async def get_amenity_data(db: AsyncSession, building_id: UUID) -> dict:
    building = await db.execute(select(Building).where(Building.id == building_id))
    if not building:
        raise ValueError(f"Building {building_id} not found")
    return { "composite": 7.5 }  # Example
```

From `backend/app/api/compliance_summary.py`:
```python
@router.get("/buildings/{building_id}/geo-risk-score")
async def get_geo_risk_score(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    result = await get_geo_risk_score_service(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result
```

## Commit message
```
feat(programme-a): geo risk score composite service (inondation+seismic+grele+contamination+radon)
```

## Test command
```bash
cd backend && python -m pytest tests/test_geo_risk_score.py -v
```

## Notes
- Use existing `building_geo_context.context_data` JSON for source data
- If a sub-dimension is missing, treat as 0 for that component (conservative)
- Return: `{"score": 72, "inondation": 8, "seismic": 6, "grele": 7, "contamination": 5, "radon": 9}`
- Store result in `building_geo_context.context_data["geo_risk_score"]` for caching
