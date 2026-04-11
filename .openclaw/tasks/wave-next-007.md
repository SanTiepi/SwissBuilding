# Task: Composite geo risk score

## Commit message
feat(wave-next): compute composite geo risk score from all 24 geo.admin layers

## What to do
Create a composite geospatial risk score that combines results from all 24 geo.admin fetchers (flood, seismic, contamination, radon, noise, landslide, rockfall, groundwater, Seveso proximity) into a single 0-100 score with A-F grade and breakdown by dimension. Add the function to score_computers.py and wire it into the enrichment pipeline so every building gets a geo_risk field computed.

## Files to modify
- `backend/app/services/enrichment/score_computers.py` (add compute_geo_risk_score function; ~50-80 lines)
- `backend/app/services/enrichment/orchestrator.py` (call compute_geo_risk_score after all 24 geo.admin fetchers, assign to enrichment_meta)
- `backend/tests/test_geo_risk_score.py` (add tests for score computation with various risk combinations)

## Existing patterns to follow

From `score_computers.py` (existing score functions):
```python
def compute_environmental_risk_score(enrichment_meta: dict) -> float:
    """Weighted sum of environmental factors."""
    factors = {
        "contamination": enrichment_meta.get("contaminated_sites", {}).get("risk", 0),
        "flood_risk": enrichment_meta.get("flood_zones", {}).get("risk", 0),
        "radon": enrichment_meta.get("radon_risk", {}).get("index", 0),
    }
    return sum(v * w for v, w in factors.items()) / sum(factors.keys())

# Pattern: extract from enrichment_meta, compute weighted sum, return 0-100 + grade
```

From orchestrator.py (how to integrate):
```python
enrichment_meta["geo_risk_score"] = await compute_geo_risk_score(enrichment_meta)
```

## Acceptance criteria
- [ ] Composite score combines 9+ geo factors (flood, seismic, contamination, radon, noise, landslide, rockfall, groundwater, Seveso)
- [ ] Output: score (0-100) + grade (A-F) + breakdown dict {dimension: value}
- [ ] Weights reflect Swiss building code priorities (contamination & flood = 3.0, seismic = 2.5, etc.)
- [ ] Integrated into enrichment pipeline (called after all geo fetchers)
- [ ] Tests pass for various risk combinations (all low, all high, mixed)
- [ ] No regression in existing enrichment tests

## Test command
cd backend && python -m pytest tests/test_geo_risk_score.py tests/test_geo_enrichment_activation.py -v

## Rules
- Do NOT modify files outside the list above
- Do NOT push
- Use weighted_sum pattern from existing score functions
- Commit with the message above if tests pass
