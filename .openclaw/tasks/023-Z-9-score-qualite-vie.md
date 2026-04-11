# Brief Z.9 — Score qualité de vie global 0-100

## Context
- Composite score = combination of 7-10 sub-scores already computed elsewhere
- Sub-scores exist: mobilité (transport), nature (vegetation), services (education/sante), commerces (walk score), securite (crime rate), culture (loisirs), energie
- Need: single 0-100 "qualité de vie" score combining all, with breakdown by dimension

## Outcome
For each building:
1. Aggregate sub-scores (already exist or will exist):
   - Mobilité score (transport.quality_score: 0-10)
   - Nature/verd (vegetation.coverage_percent: 0-10)
   - Proximité services (education/sante distance: 0-10)
   - Vitalité commerces (walk_score: 0-10)
   - Sécurité (crime_rate inferred: 0-10)
   - Culture/loisirs (musees/theatres/sport count: 0-10)
   - Energie (energy_class A-G → 0-10)
2. Weight them (equal weight 1/7 or custom)
3. Calculate composite: (sum of weighted) × 10
4. Return score 0-100 + breakdown by dimension
5. Frontend: radar chart with 7 axes

## Files to modify
- `backend/app/services/quality_of_life_service.py` — NEW
  - calculate_qol_score(egid) — aggregate & weight
  - QOLBreakdown model (7 dimensions + reasoning per dimension)
- `backend/app/models/building.py` — add field: quality_of_life_score (int 0-100), qol_breakdown (QOLBreakdown object)
- `backend/app/api/router.py` — GET /buildings/{egid}/quality-of-life
- `frontend/src/pages/BuildingDetail.tsx` — add "Qualité de vie" card with radar chart (Recharts)

## Patterns existants to copy
```python
# backend/app/services/readiness_reasoner.py
# Multi-factor composite calculation pattern

# frontend/src/components/ScoreBreakdown.tsx
# Radar chart pattern (7 axes)
```

## Constraints
1. Weights: initially equal (1/7 each), configurable later
2. Missing sub-score: skip it (don't zero out the calculation)
3. Normalization: all sub-scores to 0-10 scale before aggregation
4. Reasoning: brief text explaining each dimension's contribution
5. Comparison: show vs. commune average (if data available)

## Commit message
```
feat(qol): quality of life composite score 0-100

- QualityOfLifeService: aggregate mobilité, nature, services, commerces, sécurité, culture, énergie
- Equal weighting (1/7), configurable
- Missing sub-scores skipped (graceful degradation)
- QOLBreakdown model: 7 dimensions + reasoning
- Frontend: radar chart, comparison vs commune
- Tests: 5 scenarios (all scores present, missing one, all missing, calculate QOL, radar chart data)
```

## Tests
```bash
npm run test:inventory && npm run test:related && npm run gate:safe-to-start:plan
```

## Exit = done when
- [ ] Z.9 — QOL score calculated for 3 test buildings
- [ ] All 7 dimensions contribute
- [ ] Score 0-100 reasonable (not skewed)
- [ ] Breakdown explains each dimension
- [ ] Radar chart displays in frontend
- [ ] Comparison vs commune shows (if available)
- [ ] Tests green
