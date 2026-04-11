# Task: DefectShield — Tests exhaustifs edge cases

## Commit message
feat(defect-shield): comprehensive edge case tests for all DefectShield modules

## What to do
Add comprehensive test coverage for DefectShield across all 6 completed modules (model + schema, timeline service, alerts, API endpoints, PDF generation, frontend widget). Test edge cases: boundary dates (leap years, year transitions), status transition errors, timezone handling, missing/malformed data, Gotenberg failures, concurrent alert creation, i18n (FR/DE/IT), dark mode CSS, API rate limiting, and integration scenarios (create defect → auto-alert → update status → generate PDF).

## Files to modify
- `backend/tests/test_defect_timeline_edge_cases.py` (create: boundary dates, year 2030 leap year, midnight UTC, timezone shifts, Swiss holiday handling)
- `backend/tests/test_defect_status_machine.py` (create: invalid transitions, terminal state enforcement, idempotent updates, concurrent updates)
- `backend/tests/test_defect_gotenberg_resilience.py` (create: PDF generation failures, timeout, invalid HTML, missing building, lang validation)
- `frontend/tests/DefectTimelineWidget.edge.test.tsx` (create: empty list, all-expired, all-critical urgency, dark mode variants, loading/error states, PDF download failure, delete confirmation scenarios)
- `backend/tests/test_defect_shield_integration.py` (create: full flow test: POST timeline → auto-alert fires → PATCH to notified → GET alerts → DELETE → verify audit trail)

## Existing patterns to follow

From `test_defect_timeline.py` (test structure):
```python
def test_notification_deadline_leap_year():
    """Feb 28, 2028 + 60 days = May 1, 2028 (leap year)."""
    discovery = date(2028, 2, 28)
    deadline = compute_notification_deadline(discovery)
    assert deadline == date(2028, 4, 28)

def test_swiss_holiday_extends_deadline():
    """If deadline falls on 1 Aug (national day), extends to next workday."""
    discovery = date(2027, 6, 1)  # deadline = 30 Jul (Fri)
    assert ...

@pytest.mark.asyncio
async def test_concurrent_status_updates():
    """Two PATCH requests to update status simultaneously."""
    # Simulate race condition, verify only one succeeds or last-write-wins
```

From existing integration test patterns:
```python
@pytest.mark.asyncio
async def test_full_defect_lifecycle():
    """Create → Alert fires → Update status → Generate letter → Delete."""
    # 1. POST /defects/timeline → 201
    # 2. check alert was created (GET /defects/alerts)
    # 3. PATCH to "notified" → 200
    # 4. POST /defects/{id}/generate-letter → PDF bytes
    # 5. DELETE /defects/{id} → 200
    # 6. GET /defects/{id} → 404 or status="deleted"
```

## Acceptance criteria
- [ ] Backend: 25+ edge case tests covering dates, timezones, holidays, leap years
- [ ] Backend: 10+ status machine tests (invalid transitions, terminal states, idempotent)
- [ ] Backend: 8+ Gotenberg resilience tests (failures, timeouts, invalid input)
- [ ] Frontend: 12+ edge case tests (empty, all-expired, dark mode, loading/error)
- [ ] Integration: 1 full lifecycle test (create→alert→update→pdf→delete)
- [ ] All tests pass (60+ total new tests)
- [ ] All existing tests still pass (no regression)

## Test command
cd backend && python -m pytest tests/test_defect_timeline_edge_cases.py tests/test_defect_status_machine.py tests/test_defect_gotenberg_resilience.py tests/test_defect_shield_integration.py -v && cd ../.. && cd frontend && npm test -- DefectTimelineWidget.edge

## Rules
- Do NOT modify files outside the list above
- Do NOT push
- Use @pytest.mark.asyncio for async tests
- Test with real Swiss holidays + timezone conversions
- Commit with the message above if all tests pass
