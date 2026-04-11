# 🚀 DEV-RUNNER V4 — COUNTDOWN TO 19:00 CET

**Current Time:** 2026-04-03 03:28 CET  
**Relaunch Time:** 2026-04-03 19:00 CET  
**Time Remaining:** 15 hours 32 minutes

---

## STATUS REPORT

```
📊 API Status:         RESET @ 19:00 (fresh limit, no rate restriction)
✅ Briefs Queued:      25 ready for execution
✅ Commits This Week:  12 (distributed across sessions 1-2)
✅ Features Complete:  14 programmes + infrastructure
🔄 Expected Runtime:   3-4 hours (19:00 — 22:30 / 23:00)
🎯 Target Commits:     7-10 new (I-2, Wave-10, DefectShield 001-007, RenoPredict)
```

---

## EXECUTION SEQUENCE (19:00 START)

### WAVE A (19:00 — 20:15) — UI + Integration
**Priority:** CRITICAL

| # | Task | Brief | Duration | Status |
|---|------|-------|----------|--------|
| 1 | I-2 Frontend | ExpertReviewQueue + ExpertDecisionCard | 30 min | 🔴 Ready |
| 2 | Wave-10 | Permits (H-1) + Expert Review (I-2) frontend | 60 min | 🔴 Ready |

**Expected outcome:** 2 commits, full expert + permit governance wired

---

### WAVE B (20:15 — 21:45) — Models + Migrations
**Priority:** HIGH

| # | Task | Brief | Duration | Status |
|---|------|-------|----------|--------|
| 3 | DefectShield 001 | Model + migration | 25 min | 🔴 Ready |
| 4 | DefectShield 002 | Service layer | 20 min | 🔴 Ready |
| 5 | DefectShield 003 | API routes | 20 min | 🔴 Ready |

**Expected outcome:** 3 commits, defect-shield foundation complete

---

### WAVE C (21:45 — 23:00) — Final Features
**Priority:** MEDIUM

| # | Task | Brief | Duration | Status |
|---|------|-------|----------|--------|
| 6 | DefectShield 004-007 | Edge tests + integration | 45 min | 🔴 Ready |
| 7 | RenoPredict | Cost estimation full pipeline | 75 min | 🔴 Ready |

**Expected outcome:** 5+ commits, cost estimation + full defect tracking complete

---

## VALIDATION GATES

After each brief, Claude Code will:
1. ✅ Run `npm run validate` (frontend)
2. ✅ Run `ruff check` + `ruff format` (backend)
3. ✅ Run `pytest` for related tests
4. ✅ Verify commit created
5. ✅ Delete brief file
6. ✅ Update dev-queue.json

All must pass before moving to next task.

---

## STANDBY QUEUE (If Time Permits After 23:00)

```
• Q2-02: Meilisearch integration (search indexing)
• Q2-03: Feedback loop v1 (AI feedback table)
• Q3-03: Field observation mobile (mobile form)
• Q3-04: Completeness dashboard
• 019-L: REGBL/GWR import pipeline
• 020-R: Rental yield metric
• 021-K: Timeline immersive UX
• 022-T: Vegetation NDVI index
• 023-Z: Quality-of-life scoring
```

Any of these can be executed if API still has capacity after primary wave.

---

## FAILURE RECOVERY

If a task fails:
1. Debug for 10 minutes max
2. Log failure reason in `.openclaw/progress.md`
3. Mark brief as `failed` (not `done`)
4. Move to next brief
5. Return to failed task in next session if time permits

---

## SUCCESS METRICS

**Session is SUCCESSFUL if:**
- ✅ I-2 + Wave-10 done (2 commits)
- ✅ DefectShield 001-003 done (3 commits)
- ✅ RenoPredict done (1 commit)
- ✅ All tests pass
- ✅ 0 regressions in existing code

**Session is EXCELLENT if:**
- ✅ All above + DefectShield 004-007 (4 commits)
- ✅ 10+ commits total
- ✅ Started Q2 features

---

## HUMAN INTERVENTION

If CloudCode session hits timeout or error:
1. Log the error + stack trace
2. Create issue on GitHub (label: `p0`, `dev-runner-failure`)
3. Await human direction or auto-relaunch next day

---

## AUTO-RELAUNCH PROTOCOL

At end of session (23:00 or timeout):
```bash
# Automatic trigger:
openclaw system event --text "dev-done" --mode now

# This spawns next dev-runner session immediately if:
- API limit is reset
- No critical errors in logs
- Briefs remain in queue
```

---

## NOTES FOR CLAUDE CODE

**When executing at 19:00:**

1. **Read SOUL.md first** — understand project identity + rules
2. **Read AGENTS.md** — understand execution model + validation
3. **For each brief:**
   - Read the `.md` file completely
   - Grep existing code for patterns
   - Implement with focus on:
     - Type safety (no `any` types)
     - Full test coverage (golden path + edge cases)
     - Dark mode (`dark:` classes in frontend)
     - Idempotent operations (no duplicate keys)
   - Validate before committing
   - Commit with message from brief
   - Delete brief file

4. **Update tracking:**
   - After EACH commit: update `dev-queue.json` (add to `completed`, remove from `pending`)
   - Log: `echo "✅ [HH:MM] Task X: commit abc1234" >> .openclaw/progress.md`

5. **No waiting for resets** — if API hits limit mid-task:
   - Commit what's done
   - Exit cleanly
   - Next session (auto-spawned at 19:00 next day) will continue

---

**Prepared by:** DEV-RUNNER V4 (autonomous architecture system)  
**Prepared at:** 2026-04-03 03:28 CET  
**Ready for:** 2026-04-03 19:00 CET relaunch  

🚀 **SEE YOU AT 19:00!**
