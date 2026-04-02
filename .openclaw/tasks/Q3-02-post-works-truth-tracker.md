# Task Q3.02 — Post-Works Truth Tracker v1

## What to do
Implement post-works verification system: contractors report completion of work items, system captures photos + timestamps, builds audit trail for completeness verification.

**Pipeline:**
1. Create `post_work_item` table with work_item_id + completion_status + photo_uris + timestamp + contractor_signature
2. Create mobile-friendly upload form (contractor sees work items list, checks off completed ones, uploads photos)
3. Service validates: photo count ≥1 per item, timestamp logical (after start date), contractor authenticated
4. Flag for manual review if confidence <80% (e.g., photo quality poor, missing documentation)
5. Calculate "works completion %" for building (visible in Building Home)
6. Generate completion certificate PDF once all items verified

**Models:**
```python
class PostWorkItem(Base):
    work_item_id: UUID  # link to WorkItem (from planning)
    building_id: UUID
    building_element_id: UUID
    completion_status: str  # pending, in_progress, completed, verified
    completion_date: Optional[datetime]
    contractor_id: UUID
    photo_uris: JSON  # [url1, url2, ...]
    before_after_pairs: JSON  # [{before_photo_id, after_photo_id}]
    notes: str
    verification_score: float  # 0-100
    flagged_for_review: bool
    ai_generated: bool = False
    created_at: datetime

class WorksCompletionCertificate(Base):
    building_id: UUID
    pdf_uri: str
    total_items: int
    verified_items: int
    completion_percentage: float
    issued_date: datetime
    contractor_signature_uri: str
```

**API:**
- `POST /buildings/{id}/post-work-items/{id}/complete` — contractor submits completion
- `GET /buildings/{id}/post-work-items` — list with completion status
- `GET /buildings/{id}/completion-status` — overall % + breakdown
- `GET /buildings/{id}/completion-certificate` — download certificate PDF

**Frontend:**
- PostWorksTracker component (mobile-first, contractor view)
- Shows list of work items with: before photo, completion checkbox, photo upload, notes
- Displays overall completion % as progress bar
- "Generate Completion Certificate" button (appears at 100%)
- Building Home integration (shows completion % + last updated timestamp)

## Files to modify
- **Create:** `backend/app/models/post_work_item.py` (30 lines)
- **Create:** `backend/app/models/works_completion_certificate.py` (20 lines)
- **Create:** `backend/app/services/post_works_tracker_service.py` (100 lines)
- **Create:** `backend/app/services/completion_certificate_generator.py` (80 lines)
- **Create:** `backend/app/schemas/post_work.py` (35 lines)
- **Modify:** `backend/app/api/buildings.py` (add post-work endpoints, 50 lines)
- **Create:** `frontend/src/pages/Contractor/PostWorksTracker.tsx` (200 lines, mobile-first)
- **Create:** `frontend/src/components/PostWorkItemCard.tsx` (150 lines)
- **Modify:** `frontend/src/pages/Building/BuildingHome.tsx` (add completion widget, 20 lines)
- **Create:** `backend/alembic/versions/0XX_add_post_work_tracking.py`
- **Create:** `backend/tests/services/test_post_works_tracker.py` (12 tests)
- **Create:** `frontend/src/pages/Contractor/PostWorksTracker.test.tsx` (8 tests)

## Existing patterns to copy

From `backend/app/models/diagnostic.py` (photo storage pattern):
```python
photo_uris: JSON = Column(JSON, nullable=True)  # [{uri, uploaded_at, size}]
```

From `backend/app/services/authority_report_generator.py` (PDF generation):
```python
async def generate_pdf(template_name: str, context: dict, session) -> str:
    response = await session.post(GOTENBERG_URL, json={"content": html})
    return f"s3://{bucket}/certificate_{uuid4()}.pdf"
```

From `frontend/src/pages/Contractor/MaterialPhotoCapture.tsx` (mobile upload):
```tsx
const handlePhotoUpload = async (files: File[]) => {
  const formData = new FormData();
  files.forEach(f => formData.append("photos", f));
  await api.uploadPhotos(building_id, formData);
};
```

## Commit message
feat(programme-p): Post-works verification tracker with photo evidence + completion certificates

## Test command
```bash
cd backend && python -m pytest tests/services/test_post_works_tracker.py -v
cd frontend && npm run validate
npm run test:e2e  # mobile upload flow
```

## Success criteria
- ✅ PostWorkItem + Certificate models created + migrations run
- ✅ Service validates photos + timestamps + contractor auth
- ✅ API endpoints for submission + status queries working
- ✅ Frontend tracker mobile-responsive (touch-friendly UI)
- ✅ Completion % calculated correctly (verified_items / total_items)
- ✅ Certificate PDF generated on 100% completion
- ✅ Before/after photo pairing working
- ✅ 12+ backend tests covering validation logic
- ✅ 8+ frontend tests for upload/progress states
- ✅ Dark mode support
- ✅ No type errors, no warnings
