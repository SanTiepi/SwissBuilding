# Brief R.9 — Rendement locatif estimé + benchmark commune

## Context
- Building valuation service exists (building_valuation_service.py)
- Financial entries tracked (21 categories)
- But: rendement = f(loyer, valeur) — no benchmark against commune
- Data needed: loyers médians par commune (OFS, OBLF, comparis)
- Killer demo: "Ce bâtiment rend 4.2% vs 3.8% moyenne commune"

## Outcome
For each building:
1. Estimate loyer (based on type, age, location, energy class)
2. Fetch median loyer commune (OFS/OBLF)
3. Calculate rendement brut = loyer_annuel / valeur × 100
4. Benchmark: vs. commune, vs. canton, vs. CH
5. Frontend: rendement score, benchmark card

## Files to modify
- `backend/app/services/rental_market_service.py` — NEW
  - fetch_median_rents_by_commune() — OFS data
  - calculate_estimated_rent() — ML heuristic (type + age + location + energy)
  - calculate_gross_yield() — loyer / valeur
  - benchmark_yield() — compare commune/canton/CH
- `backend/app/models/building.py` — add fields: estimated_monthly_rent, gross_yield_percent, yield_benchmark (object with commune/canton/ch comparison)
- `backend/app/api/router.py` — GET /buildings/{egid}/rental-market
- `frontend/src/pages/BuildingDetail.tsx` — add "Rendement locatif" card with benchmark chart

## Patterns existants to copy
```python
# backend/app/services/building_valuation_service.py
# Similar composite calculation: multi-factor → single score

# frontend/src/components/BuildingScoreCard.tsx
# Reuse pattern for benchmark display
```

## Constraints
1. Rendement = gross yield only (brut, pas net)
2. Estimate rent = heuristic (pas ML sophistiqué), avec confiance score
3. Benchmark data cached 30 jours (OFS data stale ok)
4. Display "estimated" vs "actual" if locataire rents known
5. Footnote: "Basé sur données OFS + OBLF, estimation imprécise"

## Commit message
```
feat(rental): estimate gross yield + commune benchmark

- RentalMarketService: OFS median rents, estimated rent calculation, yield benchmark
- Building model: estimated_monthly_rent, gross_yield_percent, yield_benchmark (commune/canton/ch)
- Frontend: Rendement locatif card with benchmark comparison
- Tests: 6 scenarios (estimate rent calculation, OFS fetch, benchmark vs CH, missing data, caching)
```

## Tests
```bash
npm run test:inventory && npm run test:related && npm run gate:safe-to-start:plan
```

## Exit = done when
- [ ] R.9 — Rendement calculated for 3 test buildings
- [ ] Benchmark vs commune/canton/CH working
- [ ] OFS data fetch cached correctly
- [ ] Frontend card displays with chart
- [ ] "estimated" label shown (not false precision)
- [ ] Tests green
