# Dev Priority Manifest — Wave 10+ (2026-04-03)

## Execution Order (by priority + effort balance)

Generated: 2026-04-03 02:45 UTC+2 (SwissBuilding DEV-RUNNER V4)

### Priority Tier 1 (EXECUTE ASAP when rate limit resets)

#### WAVE-10: Permits & Expert Review (H-1 + I-2)
- **File:** `.openclaw/tasks/wave-10-permits-and-expert-review-frontend.md`
- **Effort:** L (8-10h)
- **Impact:** ⭐⭐⭐⭐⭐ (unlocks Gate 1 closure, pilot-ready)
- **Dependencies:** None
- **Blockers:** None
- **Status:** READY TO EXECUTE
- **Test Command:** `npm run test:inventory && npm run test:related && npm run gate:safe-to-start:plan`

#### 019-L-1: RegBL + GWR Complete Import
- **File:** `.openclaw/tasks/019-L-1-import-regbl-gwr-complet.md`
- **Effort:** M (5-6h)
- **Impact:** ⭐⭐⭐⭐
- **Dependencies:** None
- **Status:** READY

#### 020-R-9: Rental Yield Calculation
- **File:** `.openclaw/tasks/020-R-9-rendement-locatif.md`
- **Effort:** S (3-4h)
- **Impact:** ⭐⭐⭐
- **Dependencies:** Land registry data (completes faster after 019)
- **Status:** READY

### Priority Tier 2 (Q2 delivery, non-blocking)

#### Q2-02: Meilisearch Integration
- **File:** `.openclaw/tasks/Q2-02-meilisearch-integration.md`
- **Effort:** M (4-5h)
- **Impact:** ⭐⭐⭐⭐ (search performance)
- **Dependencies:** None
- **Status:** READY

#### Q2-03: Feedback Loop v1
- **File:** `.openclaw/tasks/Q2-03-feedback-loop-v1.md`
- **Effort:** M (5h)
- **Impact:** ⭐⭐⭐⭐ (AI learning)
- **Dependencies:** None
- **Status:** READY

### Priority Tier 3 (Q3+ features)

#### 021-K-1: Timeline Immersive
- **File:** `.openclaw/tasks/021-K-1-timeline-immersive.md`
- **Effort:** M (4-5h)
- **Impact:** ⭐⭐⭐⭐ (UX polish)
- **Status:** READY

#### Q3-03: Field Observation Mobile
- **File:** `.openclaw/tasks/Q3-03-field-observation-mobile.md`
- **Effort:** M (6h)
- **Impact:** ⭐⭐⭐⭐⭐ (fieldwork essential)
- **Status:** READY

#### Q3-04: Completeness Dashboard
- **File:** `.openclaw/tasks/Q3-04-completeness-dashboard.md`
- **Effort:** M (4h)
- **Impact:** ⭐⭐⭐⭐ (visibility)
- **Status:** READY

---

## Cleanup Actions Done (this session)

✅ Removed 9 DONE briefs:
- A-15 (GeoContextPanel)
- A-16 (GeoRiskScore)
- B-01 (ClimateProfile)
- C-1 (InventoryCRUD)
- E-03 (CECB Integration)
- G-1 (TrustScore)
- G-2 (UnknownIssues)
- G-3 (Contradiction)
- H.1 (old RDPPF — already in identity_chain_service)
- N-1 (ComplianceScan)

**Briefs before cleanup:** 34
**Briefs after cleanup:** 25
**Delta:** -9 (27% reduction, quality ↑)

---

## Next Actions (for next DEV-RUNNER cycle)

1. **When Claude Code rate limit resets (≈7pm UTC+2):**
   - Execute WAVE-10 first (H-1 + I-2, 8-10h)
   - Chain execute: 019 → 020 (sequential, 3h each)
   - Report: 3 commits, 23 hours dev

2. **Parallel tracks (if subagent available):**
   - Q2-02 (Meilisearch, 4-5h)
   - Q2-03 (Feedback Loop, 5h)
   - = 3 weeks cumulative to all Q2 milestones

3. **Quality gates:**
   - Run `npm run test:inventory` after each pair
   - Run full CI before merging to `building-life-os`

---

## Session Summary

| Metric | Value |
|--------|-------|
| Session Start | 2026-04-03 02:45 UTC+2 |
| Briefs Audited | 34 |
| Briefs Cleaned | 9 |
| Briefs Ready | 25 |
| High Priority (Tier 1) | 3 |
| Est. Total Dev Time | ~35-40h (across next 2 weeks) |
| Next Checkpoint | WAVE-10 execution (pending rate limit) |
