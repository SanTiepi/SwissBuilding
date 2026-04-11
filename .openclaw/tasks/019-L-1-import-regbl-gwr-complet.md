# Brief L.1 — Import RegBL/GWR complet

## Context
- RegBL (Registre fédéral des bâtiments) = 1.7M+ buildings Suisse
- GWR API endpoint exists: https://data.geo.admin.ch/api/building_gwr
- Current import: seulement surface, nb étages estimés
- Manquent: chauffage, période construction, usage principal, renovation year, eau chaude, nb logements

## Outcome
Bulk import GWR pour TOUS les bâtiments VD/GE (initial scope) avec TOUS les champs:
- heat_source (gaz, mazout, pompe à chaleur, bois, électrique, district, autre)
- construction_period (estimation: 1800-1900, 1900-1920, …, 2010-2025)
- primary_use (habitation, commerce, industrie, agriculture, etc.)
- renovation_year (if tracked)
- hot_water_source (centralisé, décentralisé, sans)
- num_households (si disponible)
- Tous les champs BFS existants

## Files to modify
- `backend/app/ingestion/gwr_importer.py` — NEW (complete importer using geo.admin API)
- `backend/app/models/building.py` — add fields: heat_source, construction_period, primary_use, renovation_year, hot_water_source, num_households
- `backend/app/models/__init__.py` — export Building updates
- `backend/app/api/router.py` — POST /import/gwr/bulk (admin only)
- `backend/app/database/migrations/` — Alembic migration for new columns

## Patterns existants to copy
```python
# backend/app/ingestion/vaud_public_importer.py
# Similar structure — iterate GWR API, upsert buildings, track source
```

## Constraints
1. Idempotent: running import twice = same result
2. Track source: every field has "source": "gwr", "fetched_at": ISO timestamp
3. Merge with existing: if building exists, update missing fields only (don't overwrite)
4. Batch upsert for performance: 1000 buildings per transaction
5. Log every 10k buildings (progress tracking)
6. No delete — only update existing or create new

## Commit message
```
feat(import): complete RegBL/GWR bulk import with all BFS fields

- GWR API integration for heat_source, construction_period, primary_use, renovation_year, hot_water_source, num_households
- Idempotent importer: upsert with source tracking
- Initial scope: VD + GE (1.2M buildings)
- Batch processing: 1000/transaction, 10k/batch log
- Tests: 5 scenarios (first import, re-import idempotent, partial update, missing field, API error)
```

## Tests
```bash
npm run test:inventory && npm run test:related && npm run gate:safe-to-start:plan
```

## Exit = done when
- [ ] L.1 — GWR importer runs successfully on 10k test buildings
- [ ] All 8 fields populated + source tracked
- [ ] Idempotent: re-run = no change
- [ ] Performance: <10 seconds for 10k buildings
- [ ] Merge logic verified (existing data not overwritten)
- [ ] Tests green
