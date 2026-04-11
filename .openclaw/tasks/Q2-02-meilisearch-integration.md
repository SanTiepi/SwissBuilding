# Task Q2.02 — Meilisearch Integration (Full-Text Search)

## What to do
Integrate Meilisearch for full-text search across buildings, diagnostics, documents, and work items. Enable instant search results (< 100ms) across all indexed entities.

**Search indices (3 primary):**
1. **buildings_index** — egid, address, canton, postal_code, owner_name, materials, hazards (1 sec to populate 10k buildings)
2. **diagnostics_index** — building_id, type (asbestos/lead/PCB/etc), date, findings, severity, contractor_name
3. **documents_index** — name, type, content (OCR text), building_id, upload_date, source

**Features:**
- Faceted search: filter by canton, material type, hazard level, document type
- Typo tolerance (1-2 typos forgiven)
- Search suggestions (autocomplete)
- Boolean operators (AND, OR, NOT)
- Geospatial search optional (radius around postal code)

**Integration:**
1. Setup Meilisearch service container (docker-compose.yml addition)
2. Sync script (initial import of 10k buildings from DB)
3. Webhook on building_create/update → index update (near real-time)
4. Same for diagnostics and documents

**API Endpoint:**
- `GET /search?q={query}&limit=20&facets=canton,material,hazard` — unified search

**Frontend:**
- SearchBar component (input + dropdown suggestions + filters)
- SearchResults component (tabbed: buildings | diagnostics | documents)
- Each result links to detail page
- Integrate into main NavBar (visible on all pages)

## Files to modify
- **Modify:** `docker-compose.yml` (add meilisearch service)
- **Create:** `backend/app/services/search_service.py` (100 lines)
- **Create:** `backend/app/indexing/buildings_indexer.py` (50 lines)
- **Create:** `backend/app/indexing/diagnostics_indexer.py` (40 lines)
- **Create:** `backend/app/indexing/documents_indexer.py` (40 lines)
- **Create:** `backend/app/api/search.py` (30 lines, new router)
- **Create:** `scripts/sync_meilisearch.py` (80 lines, migration script)
- **Create:** `frontend/src/components/SearchBar.tsx` (150 lines)
- **Create:** `frontend/src/pages/SearchResults.tsx` (180 lines)
- **Modify:** `frontend/src/layouts/MainLayout.tsx` (integrate SearchBar, 5 lines)
- **Create:** `backend/tests/services/test_search_service.py` (15 tests)
- **Create:** `frontend/src/components/SearchBar.test.tsx` (8 tests)

## Existing patterns to copy

From `backend/app/services/document_classifier.py` (webhook pattern):
```python
async def on_document_created(doc_id: UUID, event: Event):
    # trigger indexing
    await index_document(doc_id)
```

From `frontend/src/components/filters/FilterBar.tsx` (facet UI):
```tsx
export const SearchFilters = memo(({ facets, onFilter }: Props) => {
  return (
    <div className="flex gap-4 p-4 dark:bg-gray-800">
      {facets.map(f => (
        <select key={f} onChange={e => onFilter(f, e.target.value)}>
          <option value="">All {f}</option>
          {/* options */}
        </select>
      ))}
    </div>
  );
});
```

## Commit message
feat(programme-i): Meilisearch integration — full-text search across buildings, diagnostics, documents

## Test command
```bash
docker-compose up -d meilisearch  # start service
cd backend && python -m pytest tests/services/test_search_service.py -v
python scripts/sync_meilisearch.py --test  # validate indexing
cd frontend && npm run validate
```

## Success criteria
- ✅ Meilisearch container starts in docker-compose
- ✅ Sync script indexes 10k buildings in <30 seconds
- ✅ Buildings_index searchable (by egid, address, canton, material)
- ✅ Diagnostics_index searchable (by type, date, contractor)
- ✅ Documents_index searchable (by name, content)
- ✅ Search API returns results in <100ms
- ✅ Typo tolerance working (1-2 typo forgiveness)
- ✅ Faceted filters working (canton dropdown, hazard level, etc)
- ✅ SearchBar component with autocomplete
- ✅ SearchResults page tabbed (buildings | diagnostics | documents)
- ✅ 15+ backend tests covering indexing + search queries
- ✅ 8+ frontend tests for SearchBar + results
- ✅ Dark mode support on SearchResults page
- ✅ No type errors, no lint warnings
