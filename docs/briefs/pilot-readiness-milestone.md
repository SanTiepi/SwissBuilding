# Milestone: Safe-to-Start Dossier — Pilot-Ready

> Execution brief. Not a vision doc. Not a feature list.
> Goal: close the commercial loop on the safe-to-start wedge.

## Exit Criteria (all 4 must pass)

### EC-1: One end-to-end dossier scenario, fully demonstrable
- A seeded building (`Chemin des Alpes 28`, G1 scenario, 4 blockers) must progress from **blocked** to **ready** through operator actions in the UI
- The flow: login as pilot user -> see blockers -> fix each blocker -> readiness flips to green -> generate authority pack -> submit
- Demonstrable = someone who isn't us can follow the flow in 15 minutes

### EC-2: One pilot scorecard tied to a real dossier flow
- The Today page (or portfolio view) shows the pilot org's 6 buildings with readiness state per building
- Scorecard = summary of: buildings ready / blocked / unknown, top blockers, overdue actions
- Must reflect real data from EC-1, not hardcoded

### EC-3: One operator surface for proved / missing / changed / next
- Building Home shows clearly:
  - **Proved**: what evidence exists and is valid
  - **Missing**: what's blocking readiness (unknowns, expired diagnostics, missing docs)
  - **Changed**: recent change signals (new diagnostic, expired evidence, intervention completed)
  - **Next**: recommended actions to reach readiness
- This is the "4-quadrant" view the operator uses daily

### EC-4: One green real e2e proof
- `npm run test:e2e:real` passes with backend running + pilot seed
- At minimum: `dossier-workflow.spec.ts` passes all tests against real data
- Or: a documented evidence bundle (screenshots + API responses) proving the flow works

## Current State Assessment

| Component | State | Gap |
|---|---|---|
| `seed_pilot_ready.py` | Exists (88 lines) | Verify it actually creates the 6 buildings with correct readiness states |
| `readiness_reasoner.py` | Full (765+ lines) | Mature, 4 readiness types |
| `safe_to_start_service.py` | Full | Produces go/no-go with blockers |
| `dossier_workflow.py` API | Full (206 lines) | 7 endpoints covering full lifecycle |
| `dossier-workflow.spec.ts` | Exists (164 lines) | 4 real e2e tests, need to verify they pass |
| ReadinessWallet page | Exists | Marked for migration to BuildingDetail (ADR-005) |
| Building Home tabs | 7 tabs | Need to verify 4-quadrant info is surfaced |
| Today page | Exists | Need to verify pilot org scoping works |
| Pilot setup guide | Exists (59 lines) | Documents flow, credentials, demo walkthrough |

## Likely Gaps to Close

1. **EC-1**: Does the seed actually create fixable blockers? Test the full fix-blocker -> re-evaluate -> ready flow
2. **EC-2**: Is there a scorecard/summary component on Today or Portfolio? Or just raw building list?
3. **EC-3**: Are the 4 quadrants (proved/missing/changed/next) visible on Building Home, or scattered across tabs?
4. **EC-4**: Does `dossier-workflow.spec.ts` pass right now? Run it and find out

## Execution Plan

### Phase 1: Diagnostic (2h)
- Start backend + seed pilot data
- Run `dossier-workflow.spec.ts` against real backend
- Walk the demo flow manually (pilot-setup-guide.md)
- Document exactly what works, what doesn't, what's missing

### Phase 2: Fix (based on diagnostic)
- Fix whatever blocks the 4 exit criteria
- Likely: UI wiring, seed data completeness, missing scorecard component
- NOT: new services, new models, architectural changes

### Phase 3: Prove (1h)
- Green real e2e
- 15-minute demo walkthrough documented
- Evidence bundle committed to `artifacts/`

## Constraints

- No new models or services unless absolutely required
- No frontend redesign — wire existing components
- Scope = pilot demo works end-to-end, nothing more
- If a gap is too large (>1 day), document it as a blocker and ship what works
