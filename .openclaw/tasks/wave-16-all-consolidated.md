# WAVE 16 CONSOLIDATED — 5 Features in One Lot

## MISSION
Implement 5 Q2 features in sequence: feedback loop, OCR hardening, quote extraction, authority pack real test, and GE rules pack. All in one session, one commit per feature, comprehensive testing.

## FEATURES (IN EXECUTION ORDER)

### Feature 1: Feedback Loop v1
**What:** Capture user corrections to AI extractions (diagnostics, rules, recommendations) → feed into learning pipeline.
**Files to create:**
- `backend/app/models/ai_feedback.py` (model with original_value, corrected_value, feedback_type)
- `backend/app/services/feedback_service.py` (service)
- `backend/app/api/feedback_router.py` (POST /api/feedback, GET /api/feedback?building_id=X)
- `backend/alembic/versions/061_ai_feedback_table.py` (migration)
- `frontend/src/components/FeedbackButton.tsx` (small "this is wrong?" button)
- `backend/tests/test_feedback_service.py` (8+ test cases)

**Patterns:**
- Model: copy from `backend/app/models/action_item.py`
- Service: copy from `backend/app/services/document_service.py`
- Router: copy from `backend/app/api/document_router.py`
- Migration: last is `060_ged_audit_trail.py`, next is `061_ai_feedback_table.py`
- Frontend: `AsyncStateWrapper` + toast notification

**Acceptance:** Model exists with required fields, POST endpoint works, GET anonymizes building_id, tests pass, frontend submits async.

---

### Feature 2: OCR Pipeline Hardening
**What:** Retry logic (3x exponential backoff), ClamAV antivirus scan, performance tuning (<5s/page), latency metrics.
**Files to modify:**
- `backend/app/services/ocr_service.py` (add retry decorator, timeout handling)
- `backend/app/services/document_classifier.py` (add ClamAV pre-scan)
- `backend/app/tasks/ocr_retry_handler.py` (Dramatiq retry task, new)
- `backend/app/services/antivirus_service.py` (ClamAV wrapper, new)
- `backend/tests/test_ocr_hardening.py` (15+ test cases)

**Patterns:**
- Service: extend existing `OcrService`, no breaking changes
- Task: copy pattern from `backend/app/tasks/email_scheduler.py`
- Antivirus: wrap ClamAV via subprocess or clamd daemon
- Tests: copy from `backend/tests/test_document_service.py`

**Acceptance:** Retry logic works (test with timeout), ClamAV scans PDFs before OCR, latency p50/p95/p99 logged, tests pass.

---

### Feature 3: Quote Extraction v1
**What:** Automatic extraction of contractor quotes (devis) from PDFs: price, scope, timeline, contractor info. LLM-powered with confidence scoring.
**Files to create:**
- `backend/app/models/contractor_quote.py` (model)
- `backend/app/services/quote_extraction_service.py` (service using LLM)
- `backend/app/api/quote_router.py` (POST /api/documents/{id}/extract-quote, GET /api/buildings/{id}/quotes)
- `backend/alembic/versions/062_contractor_quotes_table.py` (migration)
- `frontend/src/components/QuoteViewer.tsx` (display quotes with confidence)
- `backend/tests/test_quote_extraction.py` (12+ test cases)

**Patterns:**
- Model: copy from `backend/app/models/action_item.py`
- Service: reuse `DocumentClassifierService` + `llm_extraction_service.py` (existing)
- Router: copy from `backend/app/api/document_router.py`
- Frontend: `AsyncStateWrapper` + table (reuse from DiagnosticDetail)

**Acceptance:** Model has contractor_name, total_price, scope, timeline, confidence, ai_generated flag. LLM extraction works, confidence scoring <70% flags for manual review, tests pass.

---

### Feature 4: Authority Pack Real Validation
**What:** End-to-end real test: build pack for real building, submit to VD authority portal, verify acceptance.
**Files to create:**
- `tests/e2e/e2e-authority-pack-real.spec.ts` (Playwright test)
- `backend/tests/test_authority_pack_submission.py` (service tests)

**Patterns:**
- E2E: reuse `tests/e2e/building-flow.spec.ts` pattern
- Service: extend existing `backend/app/services/authority_pack_service.py`
- Fixtures: real building from `tests/e2e/fixtures/real-buildings-dataset.json`

**Acceptance:** E2E test runs: org → building → diagnostic → pack generation → real submission to VD. Pack passes all VD validation checks, returns submission_id + status. No flakiness.

---

### Feature 5: Rules Pack GE v1
**What:** Geneva-specific compliance rules pack (40+): contamination, energy (CECB), legal/lease obligations.
**Files to create:**
- `backend/app/services/rules_packs/ge_rules_service.py` (~40 rules)
- `backend/app/services/rules_packs/ge_energy_rules.py` (CECB + heating)
- `backend/app/services/rules_packs/ge_contamination_rules.py` (polluants limits)
- `backend/tests/test_ge_rules_pack.py` (20+ test cases)

**Files to modify:**
- `backend/app/constants.py` (add GE thresholds: RADON_LIMIT_GE=300, etc.)
- `backend/app/services/completeness_engine.py` (wire GE rules to Geneva buildings)

**Patterns:**
- Rules service: copy structure from `backend/app/services/rules_packs/vd_rules_service.py`
- Thresholds: store constants in `backend/app/constants.py`
- Rules engine: existing engine handles both cantons automatically

**Acceptance:** 40+ rules implemented (12 contamination, 10 energy, 8 legal, 10+ other). Each rule has article reference + FR remediation text. Tests pass. Rules auto-select for canton='GE'.

---

## HARD RULES
1. **NO BREAKING CHANGES** — existing APIs / models / tests must remain functional
2. **LANGUAGE**: code/commits in English, comments/docstrings in French when domain-specific
3. **IDEMPOTENCE**: migrations, imports, service methods must be idempotent
4. **TESTS**: Feature 1 (8+ tests), Feature 2 (15+ tests), Feature 3 (12+ tests), Feature 4 (1 golden-path E2E), Feature 5 (20+ tests)
5. **PERFORMANCE**: OCR <5s/page (Feature 2), feedback submission async <100ms (Feature 1), quote extraction <3s per PDF (Feature 3)
6. **PRIVACY**: Feature 1 & 3 don't expose PII to external APIs (anonymize or local processing)
7. **SCOPE**: stick to files listed above, don't touch others

## VALIDATION COMMANDS
```bash
# After each feature:
cd backend && python -m pytest tests/test_[feature].py -v --tb=short
cd backend && ruff check app/ tests/ && ruff format --check app/ tests/
cd frontend && npm run validate && npm test

# Full suite at end:
cd backend && python -m pytest tests/ -q --tb=short
cd frontend && npm test
```

## COMMIT STRATEGY
- 1 commit per feature (5 total commits for this wave)
- Commit messages:
  1. `feat: feedback loop v1 — capture user corrections for AI learning pipeline`
  2. `feat: OCR pipeline hardening — retry logic, ClamAV scan, performance tuning for 99%+ reliability`
  3. `feat: quote extraction v1 — automatic contractor estimate parsing with confidence scoring`
  4. `test: authority pack validation real — submit to VD authority portal and verify acceptance`
  5. `feat: Rules Pack GE v1 — Geneva-specific compliance rules (40+), LQAEN + energy + lease aligned`

## CLOSURE
- All 5 commits created and pushed
- Backend tests pass (0 errors)
- Frontend tests pass (0 errors)
- No new warnings introduced
- Code follows patterns from codebase

## EXISTING RESOURCES TO REUSE
- `backend/app/services/ocr_service.py` — extend, don't rewrite
- `backend/app/services/document_classifier.py` — already exists
- `backend/app/services/completeness_engine.py` — reuse for feature 5
- `backend/app/services/llm_extraction_service.py` — use for feature 3
- `backend/app/services/authority_pack_service.py` — extend for feature 4
- `backend/app/enrichment/` — already 24 geo.admin layers active
- `frontend/src/components/AsyncStateWrapper.tsx` — reuse for all features
- Gotenberg — already in stack for PDFs
- Dramatiq — already configured for async tasks

## Context
- Repo: SanTiepi/SwissBuilding
- Branch: building-life-os (active development)
- Backend: FastAPI + PostgreSQL/PostGIS (7150+ tests)
- Frontend: React 18 (996 tests)
- Last 7 Wave 15 features completed: pilot onboarding, notifications, GED hardening, multi-org dashboard, rules pack VD v2, scorecard, web checkup

## NOW
Read this brief thoroughly. For EACH feature:
1. Grep the codebase for existing patterns/files
2. Implement the feature (create/modify files as listed)
3. Write tests (quantities specified above)
4. Run validation commands → 0 errors required
5. Commit with exact message provided
6. Continue to next feature

When ALL 5 features are complete and all tests pass, you're done. No partial completion.
