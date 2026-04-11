# Execution Plan for 19:00 CET Reset (2026-04-03)

**Time:** 19:00 CET (17:00 UTC)  
**API Status:** Reset + fresh (no rate limit)  
**Duration:** ~3-4 hours (until 22:00-23:00 or timeout)  
**Agent:** Claude Code (bypassPermissions mode)

---

## PRIORITY STACK (IN ORDER)

### 1️⃣ **I-2 Frontend — Expert Review Queue**
**File:** `.openclaw/tasks/I-2-expert-review-override-governance.md`  
**Effort:** S (30 min)  
**What:** Wire React components for expert review UI. Backend service + API exist.  
**Create:**
- `frontend/src/pages/ExpertReviewQueue.tsx` (200 lines)
- `frontend/src/components/ExpertDecisionCard.tsx` (100 lines)
- Test file (6 tests)

**Key pattern:**
```tsx
// Use AsyncStateWrapper for loading/error/empty states
import { AsyncStateWrapper } from '@/components/AsyncStateWrapper';
import { useExpertReviews } from '@/hooks/useExpertReviews';

export const ExpertReviewQueue = () => {
  const { data, isLoading, error } = useExpertReviews();
  
  return (
    <AsyncStateWrapper state={{ data, isLoading, error }}>
      {/* Card list with decision options */}
    </AsyncStateWrapper>
  );
};
```

**Expected commit:** `feat(I-2): expert-review-queue-frontend`

---

### 2️⃣ **Wave-10 Consolidation — Permits + Expert Review**
**File:** `.openclaw/tasks/wave-10-permits-and-expert-review-frontend.md`  
**Effort:** M (60 min)  
**What:** H-1 permit model + API + frontend. I-2 frontend integration.

**Create (H-1):**
- `backend/app/models/permit.py` (permit model)
- `backend/app/services/permit_service.py` (CRUD)
- `backend/app/api/permits.py` (router)
- Tests (6 tests)
- `frontend/src/components/buildings/PermitManagementPanel.tsx` (140 lines)

**Modify:**
- `backend/app/models/__init__.py` — add Permit import
- `backend/app/api/router.py` — register permits router
- `frontend/src/pages/buildings/BuildingHome.tsx` — add PermitManagementPanel to tabs

**Expected commit:** `feat(wave-10): permits-and-expert-review-integration`

---

### 3️⃣ **DefectShield 001-007 — Construction Defect Tracking**
**Files:** `.openclaw/tasks/defect-shield-00X.md` (X=001-007)  
**Effort:** L (90 min, 7 small tasks)  
**What:** DefectTimeline model + migrations + tests for Swiss law art. 367 CO (60-day defect notification deadline).

**Sequence:**
1. **001:** Model + schema + migration (NEW model, not reusing existing)
2. **002:** Service layer (CRUD + deadline logic)
3. **003:** API router (GET/POST/PUT endpoints)
4. **004:** Edge case tests (zero volume, missing canton, expired deadlines)
5. **005:** Notification service (alert when deadline approaching)
6. **006:** Frontend DefectTimeline component
7. **007:** Integration tests (full chain)

**Key fields:**
```python
class DefectTimeline(Base):
    __tablename__ = "defect_timelines"
    id = UUID (PK)
    building_id = UUID (FK) [indexed]
    defect_type = String(100)
    discovery_date = Date
    notification_deadline = Date [computed: discovery_date + 60 days]
    notification_sent_at = DateTime [nullable]
    status = String [open/notified/expired/resolved]
    severity = String [low/medium/high/critical]
    responsible_party = String
    legal_reference = String [default "art. 367 al. 1bis CO"]
    metadata_json = JSON [nullable]
    created_at, updated_at = DateTime
```

**Expected commits (7 total):**
```
feat(defect-shield-001): model + migration
feat(defect-shield-002): service layer
feat(defect-shield-003): api-routes
feat(defect-shield-004): edge-case-tests
feat(defect-shield-005): notification-service
feat(defect-shield-006): frontend-component
feat(defect-shield-007): integration-tests
```

---

### 4️⃣ **RenoPredict — Cost Estimation Pipeline**
**File:** `.openclaw/tasks/reno-predict-all.md`  
**Effort:** M (75 min)  
**What:** Full cost estimation for remediation work (model + service + API + frontend modal + PDF export).

**Files to create/modify:**
- `backend/app/seeds/seed_cost_references.py` — populate 6 pollutants × 5+ cantons
- `backend/app/services/cost_predictor_service.py` — lookup + coefficients + fourchette logic
- `backend/app/api/cost_prediction.py` — POST /predict/cost endpoint
- `backend/tests/test_cost_predictor.py` — all pollutant combos + edge cases
- `frontend/src/components/DiagnosticView/CostEstimationModal.tsx` (140 lines)
- `frontend/src/hooks/useCostPrediction.ts` (hook)

**Key service logic:**
```python
# Canton coefficients (realistic Swiss market)
CANTON_COEFFICIENTS = {
    "VD": 1.0, "GE": 1.15, "ZH": 1.10, "BE": 1.0, 
    "VS": 0.95, "FR": 1.0, "NE": 1.05, "JU": 0.95,
}

# Cost breakdown
BREAKDOWN = [
    ("Dépose / Intervention", 0.45),
    ("Traitement déchets", 0.20),
    ("Analyses contrôle", 0.08),
    ("Remise en état", 0.22),
    ("Frais généraux", 0.05),
]

async def predict_cost(req: CostPredictionRequest) -> dict:
    # lookup reference by pollutant
    # apply CANTON_COEFFICIENTS[canton]
    # apply ACCESSIBILITY_COEFFICIENTS[accessibility]
    # apply CONDITION_COEFFICIENTS[condition]
    # compute min/median/max
    # return fourchette + breakdown
```

**Expected commit:** `feat(reno-predict): complete-cost-estimation-pipeline`

---

### 5️⃣ **Q2/Q3 Features (If Time Permits)**
**Priority order:**
1. `Q2-02-meilisearch-integration.md` (search indexing)
2. `Q2-03-feedback-loop-v1.md` (AI feedback table)
3. `Q3-02-post-works-truth-tracker.md` (already done in prior session — skip)
4. `Q3-03-field-observation-mobile.md` (mobile form)
5. `Q3-04-completeness-dashboard.md` (dashboard)

---

## VALIDATION COMMANDS

**After each brief:**
```bash
# Frontend
cd frontend
npm run validate   # tsc + eslint + prettier (must be 0 errors)
npm test           # vitest (must pass)

# Backend
cd backend
ruff check app/ tests/        # lint (must be 0 errors)
ruff format --check app/ tests/  # format (must be 0 errors)
python -m pytest tests/ -q    # tests (must pass all related)
```

**Gate check (safe to start):**
```bash
npm run test:inventory && npm run test:related && npm run gate:safe-to-start:plan
```

---

## AFTER EACH TASK

1. **Verify commit created:**
   ```bash
   git log --oneline -1
   ```

2. **Update `dev-queue.json`:**
   - Add to `completed` array: `{"epic": "programme-X", "tasks": "ID", "status": "done", "date": "2026-04-03", "commits": ["hash"]}`
   - Move from `pending_briefs` to done

3. **Delete task file:**
   ```bash
   rm .openclaw/tasks/task-file.md
   ```

4. **Log progress:**
   ```bash
   echo "✅ [HH:MM] Task X done — commit: abc1234" >> .openclaw/progress.md
   ```

---

## CHECKPOINT

**After 1 hour (20:00 CET):** I-2 + Wave-10 should be done (2 commits).  
**After 2 hours (21:00 CET):** DefectShield 001-003 done (3+ commits).  
**After 3 hours (22:00 CET):** DefectShield 004-007 + RenoPredict done (4+ commits).  
**After 4 hours (23:00 CET):** Q2/Q3 features if time permits.

---

## END OF SESSION

**Report (max 1500 chars):**
- Features done (short list)
- Total commits
- Any failures + reason
- Est. ETA for remaining briefs

**Auto-relaunch:**
```bash
openclaw system event --text "dev-done" --mode now
```

---

## GOTCHAS

1. **I-2 Frontend:** Backend service exists at `backend/app/services/expert_review_service.py`. Just wire React components.
2. **Wave-10:** When adding Permit import to `models/__init__.py`, check exact position (alphabetical order).
3. **DefectShield:** Each task is 1 commit. Do NOT combine 001+002+003 into one commit.
4. **RenoPredict:** Use realistic Swiss prices. Example: asbestos removal = CHF 250-500/m³ (vary by canton).
5. **Tests must pass:** If any test fails, fix immediately before moving to next task.

---

**Status:** READY FOR 19:00 EXECUTION ✅
