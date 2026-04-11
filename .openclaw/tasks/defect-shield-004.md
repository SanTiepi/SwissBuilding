# Task: DefectShield — API endpoints

## Commit message
feat(defect-shield): add 4 API endpoints for defect timeline management

## What to do
Expose the existing defect_timeline_service via 4 API routes: POST /defect-timelines (create), GET /defect-timelines/{id} (fetch), PATCH /defect-timelines/{id} (update status), DELETE /defect-timelines/{id} (soft delete). Validate all inputs, enforce state transitions (active→notified→resolved), and integrate with defect_alert_service for notifications on state changes.

## Files to modify
- `backend/app/api/defect_timeline.py` (add/complete the 4 endpoint handlers)
- `backend/app/router.py` (register routes if not already done; check for "defect" prefix)
- `backend/tests/test_defect_timeline_api.py` (add full endpoint tests with state transitions)

## Existing patterns to follow

From `defect_timeline_service.py`:
```python
async def create_defect_timeline(
    db: AsyncSession, building_id: UUID, discovery_date: date, defect_type: str
) -> DefectTimeline:
    """Create timeline, compute deadlines, validate defect type."""

def notify_defect(timeline: DefectTimeline) -> date:
    """Mark as notified, lock deadline."""

def resolve_defect(timeline: DefectTimeline) -> None:
    """Mark resolved."""
```

From existing FastAPI patterns (router.py):
```python
@router.post("/defect-timelines", response_model=DefectTimelineCreate)
async def create_defect(request: DefectTimelineCreate, session: AsyncSession = Depends(get_session)):
    return await defect_timeline_service.create_defect_timeline(...)

@router.get("/defect-timelines/{id}", response_model=DefectTimelineResponse)
async def get_defect(id: UUID, session: AsyncSession = Depends(get_session)):
    ...
```

## Acceptance criteria
- [ ] POST /defect-timelines creates new timeline with computed deadlines
- [ ] GET /defect-timelines/{id} fetches timeline + current state
- [ ] PATCH /defect-timelines/{id} updates status (enforce valid transitions)
- [ ] DELETE /defect-timelines/{id} soft-deletes (mark deleted, don't remove)
- [ ] All endpoints return correct status codes (201, 200, 400, 404)
- [ ] Notifications fired on state transitions (via defect_alert_service)
- [ ] Tests pass for all 4 endpoints

## Test command
cd backend && python -m pytest tests/test_defect_timeline_api.py -v

## Rules
- Do NOT modify files outside the list above
- Do NOT push
- Validate state transitions per VALID_STATUS_TRANSITIONS
- Commit with the message above if tests pass
