# Milestone: Safe-to-Start Dossier — Pilot-Ready

> Execution brief. Not a vision doc. Not a feature list.
> Goal: close the commercial loop on the safe-to-start wedge.

## Proof Contract (Phase 0 — locked)

One pilot, one canonical building, one operator surface, one proof.

| Element | Value |
|---|---|
| **Canonical building** | `Rue de Bourg 12` (Regie Pilote SA) — partially ready, 2 fixable blockers |
| **Org** | Regie Pilote SA (`seed_prospect_scenario`) |
| **User** | marc.favre@regiepilote.ch / pilot123 (role: owner) |
| **Transition to prove** | `blocked -> ready -> pack_generated -> submitted` |
| **Portfolio context** | 5 other buildings in same org show range of states |
| **Surface** | Building Home shows proved/missing/changed/next for this building |
| **Scorecard** | PilotScorecard page reflects real readiness data from the org |
| **Proof** | 1 real e2e test proving the transition on Rue de Bourg 12 |

### Why Rue de Bourg 12, not Chemin des Alpes 28

- Bourg 12 is already in the pilot org (Regie Pilote SA) — the user sees it naturally
- It has 2 fixable blockers (expired asbestos + missing waste plan) — simpler to demo
- G1 (Alpes 28) is in a separate org — would require org merge or user switch
- A 2-blocker scenario is more convincing in 15 minutes than a 4-blocker one

## Exit Criteria (all 4 must pass)

### EC-1: Rue de Bourg 12 goes from blocked to ready
- Login as marc.favre -> navigate to Bourg 12 -> see blockers
- Fix blocker 1 (expired asbestos) via dossier workflow
- Fix blocker 2 (missing waste plan) via dossier workflow
- Readiness flips to ready -> generate authority pack -> submit

### EC-2: Pilot scorecard reflects the real state
- PilotScorecard page shows 6 buildings with real readiness status
- After fixing Bourg 12, scorecard updates (1 more building ready)

### EC-3: Building Home shows 4-quadrant operator view
- **Proved**: valid diagnostics, existing evidence
- **Missing**: blockers, expired diagnostics, missing docs
- **Changed**: recent signals (new diagnostic, fixed blocker)
- **Next**: recommended actions to reach readiness

### EC-4: One green real e2e
- `dossier-workflow.spec.ts` includes a test that proves the transition
- Test targets Rue de Bourg 12 specifically
- Proves: blocked -> fix -> ready -> pack -> submit

## Gaps to Close

| Gap | Action | Effort |
|---|---|---|
| `fix-blocker` not consumed by UI | Wire DossierWorkflowPanel to call fix-blocker API | 0.5d |
| Real e2e doesn't test transition | Write 1 test: fix Bourg 12 blockers via API, assert ready | 0.5d |
| Scorecard uses legacy endpoint? | Verify PilotScorecard → pilot_scorecard_service chain | 0.25d |
| 4-quadrant view dispersed | Check if Building Home tabs already show all 4 quadrants | 0.25d |

## Constraints

- No new models or services
- No frontend redesign — wire existing components
- Scope = pilot demo works end-to-end on Rue de Bourg 12
- If a gap is >1 day, document as blocker and ship what works
