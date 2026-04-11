# Task: DefectShield Model + Schema + Migration

## Commit message
feat(defect-shield): DefectTimeline model + schema + migration

## What to do
Create the DefectTimeline SQLAlchemy model for tracking construction defect notification deadlines per Swiss law art. 367 al. 1bis CO (60 days from defect discovery to notify). This is a NEW model — do not reuse existing ones.

Fields needed:
- id: UUID primary key (same pattern as ActionItem)
- building_id: FK to buildings.id (required, indexed)
- defect_type: String(100) — type of construction defect
- discovery_date: Date — when the defect was discovered
- notification_deadline: Date — computed: discovery_date + 60 days
- notification_sent_at: DateTime — nullable, when notification was actually sent
- status: String(20) — open/notified/expired/resolved, default "open"
- description: Text — nullable, defect description
- severity: String(20) — low/medium/high/critical
- responsible_party: String(200) — nullable, who is responsible
- legal_reference: String(100) — default "art. 367 al. 1bis CO"
- metadata_json: JSON — nullable, extra data
- created_at, updated_at: DateTime with func.now()

## Files to modify
1. **CREATE** `backend/app/models/defect_timeline.py` — the new model
2. **EDIT** `backend/app/models/__init__.py` — add import: `from app.models.defect_timeline import DefectTimeline`
3. **CREATE** `backend/alembic/versions/037_add_defect_timeline.py` — migration
4. **CREATE** `backend/tests/test_defect_timeline_model.py` — model tests

## Existing patterns to follow

Model pattern (copy from backend/app/models/action_item.py):
```python
import uuid
from sqlalchemy import JSON, Column, Date, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class DefectTimeline(Base):
    __tablename__ = "defect_timelines"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    # ... rest of fields
```

Migration pattern (copy from backend/alembic/versions/036_add_swissbuildings3d_fields.py):
```python
revision = "037_defect_timeline"
down_revision = "036_swissbuildings3d"

def upgrade() -> None:
    op.create_table("defect_timelines", ...)

def downgrade() -> None:
    op.drop_table("defect_timelines")
```

Import pattern in __init__.py — just add alphabetically:
```python
from app.models.defect_timeline import DefectTimeline
```

## Acceptance criteria
- [ ] DefectTimeline model exists with all fields listed above
- [ ] Model is registered in __init__.py
- [ ] Alembic migration 037 creates the table with all columns
- [ ] Migration has both upgrade() and downgrade()
- [ ] Basic model test: create instance, check fields, check defaults
- [ ] Test that notification_deadline is not auto-computed in the model (that's for the service layer)

## Test command
cd backend && python -m pytest tests/test_defect_timeline_model.py -v 2>&1 | tail -20

## Rules
- Do NOT modify files outside the 4 files listed above
- Do NOT push
- Follow the ActionItem model pattern EXACTLY for style/imports
- Follow the 036 migration pattern for migration structure
- Commit with the message above if tests pass
