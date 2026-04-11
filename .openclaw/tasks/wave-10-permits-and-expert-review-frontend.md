# WAVE 10 — Permits & Expert Review Frontend (H-1 + I-2)

## Mission
Wire two critical governance features that complete Building Home UX:
1. **H-1:** Permit Workflow Integration (new)
2. **I-2:** Expert Review Queue (frontend only, backend exists)

## What to do

### H-1 — Permit Workflow Integration
Create end-to-end permit tracking for buildings linked to remediation projects.

**Files to create:**
- `backend/app/models/permit.py` — Permit + PermitStatus models
- `backend/app/services/permit_service.py` — CRUD + deadline tracking
- `backend/app/api/permits.py` — /buildings/{id}/permits endpoints
- `backend/tests/services/test_permit_service.py` — 6 tests
- `frontend/src/components/buildings/PermitManagementPanel.tsx` — UI (140 lines)
- `frontend/src/hooks/usePermits.ts` — fetch + format
- `frontend/src/components/buildings/__tests__/PermitManagementPanel.test.tsx` — 4 tests

**Model:**
```python
class PermitStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    EXPIRED = "expired"
    REVOKED = "revoked"

class Permit(Base):
    __tablename__ = "permits"
    id: UUID = Column(UUID, primary_key=True)
    building_id: UUID = Column(UUID, ForeignKey("buildings.id"))
    permit_type: str = Column(String)  # "renovation", "subsidy", "declaration"
    status: PermitStatus = Column(Enum(PermitStatus))
    issued_date: datetime = Column(DateTime)
    expiry_date: datetime = Column(DateTime)
    subsidy_amount: float = Column(Float, nullable=True)
    notes: str = Column(Text)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
```

**Service logic:**
- CRUD operations
- Deadline alerts (notify 30/14/7 days before expiry)
- Link permits to subsidy tracking
- Validation: expiry_date > issued_date

**API:**
- `GET /buildings/{id}/permits` — list all permits
- `POST /buildings/{id}/permits` — create permit
- `PATCH /buildings/{id}/permits/{permit_id}` — update status/dates
- `GET /buildings/{id}/permits/alerts` — list expiring permits

**Frontend:**
- PermitManagementPanel showing permit table + status badges
- "Add Permit" button → form
- Deadline warnings (red if <7 days, amber if <14 days)
- Link to subsidy tracking

**Effort:** M | **Commit message:** `feat(programme-h): permit workflow integration — deadline tracking + alerts`

---

### I-2 — Expert Review Queue (Frontend)
Wire admin page to approve/reject expert overrides on contradictions & risk scores.

**Files to create:**
- `frontend/src/pages/admin/ExpertReviewQueue.tsx` — Admin page (180 lines)
- `frontend/src/components/ExpertDecisionCard.tsx` — Review card (100 lines)
- `frontend/src/hooks/useExpertReviews.ts` — fetch pending reviews
- `frontend/src/components/__tests__/ExpertDecisionCard.test.tsx` — 4 tests

**Page structure:**
- Header: "Expert Review Queue" + stats (high/normal/low priority counts)
- Filter: decision_type (contradiction, risk_score, trust_score, etc.)
- List: ExpertDecisionCard for each pending review
  - Left: system value + reasoning
  - Middle: comparison icon (→)
  - Right: expert override input + approval button
  - Bottom: priority badge + created timestamp

**Hooks:**
```ts
useExpertReviews() → { reviews[], loading, approve, reject }
```

**Integration:**
- Route: `/admin/expert-reviews` (admin role required)
- Add link in admin sidebar

**Effort:** S-M | **Commit message:** `feat(programme-i): expert review queue admin page — override governance`

---

## Existing Patterns

### Backend permit model pattern (use this)
See `backend/app/models/complaint.py` for reference:
- Status enum + Base class
- ForeignKey to building_id
- DateTime created_at
- Optional metadata JSON

### Frontend panel pattern (use this)
See `frontend/src/components/buildings/IncidentsPanel.tsx`:
- memo() wrapper
- useQuery hook for fetch
- AsyncStateWrapper for loading
- Action buttons (delete, edit)
- Dark mode support

### Tests
Backend: pytest fixtures + parametrize
Frontend: vitest + @testing-library/react

---

## Constraints
- No breaking changes to existing schemas
- Permit expiry notifications use existing alert system
- Admin page requires role check: `require_permission("admin", "review")`
- Dark mode classes required throughout

---

## Exit Criteria
1. ✅ H-1: 6 backend tests pass + 4 frontend tests pass
2. ✅ I-2: 4 frontend tests pass
3. ✅ Both features validate (`npm run validate`)
4. ✅ 1 clean commit per feature
5. ✅ No partial exposure (both features fully wired or hidden)

---

## Test Commands
```bash
cd backend && python -m pytest tests/services/test_permit_service.py -v
cd frontend && npm run validate && npm test -- PermitManagementPanel
cd frontend && npm test -- ExpertDecisionCard
```

---

## Execution Path
1. Create H-1 backend (model + service + tests) — 30 min
2. Create H-1 frontend (component + tests) — 20 min
3. Create I-2 frontend (admin page + tests) — 25 min
4. Validate + commit (per feature)
5. Total: ~75 min

---

*Brief prepared: 2026-04-03 01:24 UTC*
*Wave-10 | Session: dev-runner-swissbuilding*
