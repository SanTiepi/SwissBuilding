# Brief K.1 — Timeline immersive batiment

## Context
- Time Machine service exists (time_machine_service.py) — traces state at each date
- Events exist: diagnostics, interventions, incidents, permits
- But frontend: no unified timeline
- Need: chronological view of ALL events, with photos/docs/context

## Outcome
Timeline page showing every event on a batiment:
- Diagnostics (photos, date, polluants trouvés)
- Interventions (date, type, entreprise, avant/après photos)
- Incidents (date, type, impact, resolution)
- Permis (date, type, status)
- Permits
- Mutations (ownership change)
- Contrats (lease start/end)
- Mesures (capteurs: radon, test amiante)
- Règlementations changeantes (new law applicable)

## Files to modify
- `backend/app/services/building_timeline_service.py` — NEW
  - get_timeline_events(egid, start_date, end_date) — aggregate all events chronologically
  - TimelineEvent model: type, date, title, description, photos[], links[], metadata
- `backend/app/models/__init__.py` — add TimelineEvent
- `backend/app/api/router.py` — GET /buildings/{egid}/timeline?start_date=X&end_date=Y
- `frontend/src/pages/BuildingTimeline.tsx` — NEW page
  - Vertical timeline (left-right or top-bottom, designer choice)
  - Event cards with icons by type (🔍 diagnostic, 🔨 intervention, ⚠️ incident, 📋 permit, etc.)
  - Click event → expand with full details + photos
  - Filter by event type (checkbox sidebar)
  - Date range picker

## Patterns existants to copy
```python
# backend/app/services/time_machine_service.py
# Already retrieves state at date; reuse same structure

# frontend/src/components/BuildingTimeline.tsx (if exists)
# or Timeline.tsx pattern from other pages
```

## Constraints
1. Order: strict chronological (ISO date sort)
2. Photos: max 2 per event (size optimization)
3. Events from MULTIPLE sources: diagnostics + building_event + interventions + incidents tables
4. No delete: hidden events still counted (but flagged "deleted")
5. Frontend: responsive (mobile = vertical, desktop = can be side-by-side)

## Commit message
```
feat(timeline): immersive building timeline with all events

- TimelineEvent aggregator: diagnostics, interventions, incidents, permits, mutations, contracts, measurements, regulatory changes
- Chronological ordering with event type icons
- Frontend: interactive timeline page, filterable by type, expandable events
- Photos + links + metadata preserved per event
- Tests: 8 scenarios (get timeline 5 years, empty timeline, photos loading, filter by type, date range, performance 1000+ events)
```

## Tests
```bash
npm run test:inventory && npm run test:related && npm run gate:safe-to-start:plan
```

## Exit = done when
- [ ] K.1 — Timeline loads for test building (20+ events)
- [ ] All event types appear (diagnostic + intervention + incident + permit + contract + measurement)
- [ ] Chronologically sorted (no date inconsistencies)
- [ ] Frontend page renders, filterable
- [ ] Photos load (max 2 per event)
- [ ] Mobile responsive
- [ ] Tests green
