# Task: DefectShield — Alertes + notifications

## Commit message
feat(defect-shield): integrate defect notifications with alert service

## What to do
Wire the defect_timeline_service (which already exists and calculates deadlines) into the notification system. When a DefectTimeline is created or updated, check if notification deadline is approaching (within 7 days), and trigger alerts via the existing notification_service. Create defect-specific alert rules that respect the 60-day legal notification window (Art. 367 CO).

## Files to modify
- `backend/app/services/defect_alert_service.py` (create or complete: notification dispatch logic, deadline monitoring)
- `backend/app/api/defect_timeline.py` (integrate alert service on POST/PATCH)
- `backend/tests/test_defect_alert.py` (create new: test alert triggering on deadline approach)

## Existing patterns to follow

From `defect_timeline_service.py` (states + transitions):
```python
VALID_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "active": {"notified", "expired", "resolved"},
    "notified": {"resolved"},
    "expired": {"resolved"},
    "resolved": set(),
}

def notify_defect(timeline: DefectTimeline) -> date:
    """Mark as notified, lock deadline, validate transition."""
```

Existing notification pattern (from other services):
```python
from app.services.notification_service import NotificationService
ns = NotificationService(session)
await ns.create_alert(
    building_id=building_id,
    alert_type="defect_deadline",
    priority="high",
    details={"days_remaining": d},
    target_users=[owner_id]
)
```

## Acceptance criteria
- [ ] DefectTimeline state transitions trigger alert checks
- [ ] Alerts fired when deadline is within 7 days (warning level)
- [ ] Alerts fired when deadline has passed (critical level)
- [ ] Notification message includes building_id, defect_type, deadline_date
- [ ] Alert respects existing notification settings (user preferences, DND)
- [ ] Tests pass for alert logic

## Test command
cd backend && python -m pytest tests/test_defect_alert.py -v

## Rules
- Do NOT modify files outside the list above
- Do NOT push
- Follow Art. 367 CO (60 days from discovery)
- Commit with the message above if tests pass
