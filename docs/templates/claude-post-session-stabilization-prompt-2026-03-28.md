# Claude Post-Session Stabilization Prompt

Use with:
- `docs/projects/post-session-stabilization-program-2026-03-28.md`
- `AGENTS.md`
- `MEMORY.md`
- `ORCHESTRATOR.md`
- `docs/projects/swissbuilding-moonshot-v2-autonomous-market-infrastructure-plan-2026-03-28.md`
- `docs/projects/claude-moonshot-evaluation-and-feedback-pack-2026-03-28.md`

---

## Full Prompt

```md
Post-session stabilization starts now.

Assume commit `6650d68` is the protected baseline for the current repo state.
Assume the mission is no longer expansion-first.
The mission is now to absorb the volume already created without degrading repo quality.

Read and use as active references:
- `docs/projects/post-session-stabilization-program-2026-03-28.md`
- `AGENTS.md`
- `MEMORY.md`
- `ORCHESTRATOR.md`
- `docs/projects/swissbuilding-moonshot-v2-autonomous-market-infrastructure-plan-2026-03-28.md`
- `docs/projects/claude-moonshot-evaluation-and-feedback-pack-2026-03-28.md`

Primary objective:
- make the current repo safer, rerunnable, verifiable, and better bounded

This is not a new feature sprint.
This is not a new vision sprint.
This is not a breadth sprint.

Hard rules:
- no new top-level product centers
- no reopening settled doctrine
- no broadening just because more infrastructure could be added
- no claiming closure without rerunnable evidence
- no leaving `ORCHESTRATOR.md` stale once a stabilization wave materially changes reality
- no ignoring hub-file discipline mismatches
- no treating partial test subsets as full truth if the blocked full-suite path can be repaired

Execute in this order unless a better closure-first reason is explicit:

1. restore full validation truth
2. add one real shell e2e smoke path
3. sync `ORCHESTRATOR.md`
4. reconcile hub-file discipline
5. cleanly bound remaining `ChangeSignal` compatibility
6. finish the in-flight `partner-submissions` lot
7. densify frontend confidence on high-value new surfaces
8. turn guard scripts into trusted routine gates
9. inventory and classify new monolith hotspots
10. align docs/evidence
11. prepare the first consolidation wave

Priority 1 is mandatory:
- fix `backend/tests/test_seed_demo.py`
- rerun the backend full suite
- rerun relevant frontend validation

Priority 2 is also mandatory:
- add at least one meaningful shell e2e smoke test for the new 5-hub runtime

Optimize for:
- closure before breadth
- rerunnable evidence
- runtime confidence
- bounded compatibility
- reviewable follow-up commits
- lower structural risk

Allowed pre-flight behavior:
- you may return a short `pre-flight adjustments` section before implementation
- only include changes that tighten stabilization
- mark each as `add now`, `defer`, or `reject`

At the end of each wave, return:
- `wave`
- `priorities advanced`
- `what is closed`
- `what remains partial`
- `validations run`
- `tests run`
- `failures fixed`
- `blocking debt`
- `accepted debt`
- `repo-quality risk reduced`
- `next best wave`
- `repo object names` when checkpoint wording uses shorthand

Do not try to look fast.
Try to make the repo trustworthy after an extremely high-volume session.
```

---

## Compact Prompt

```md
Use commit `6650d68` as the stabilization baseline.

Do not broaden the product.
Do not reopen doctrine.
Do not start a new expansion sprint.

Read:
- `docs/projects/post-session-stabilization-program-2026-03-28.md`
- `AGENTS.md`
- `MEMORY.md`
- `ORCHESTRATOR.md`

Mission:
- absorb the current repo volume safely
- restore full validation truth
- prove one real shell e2e smoke path
- sync control-plane reality
- close compatibility and in-flight partner-submissions debt
- prepare the first consolidation wave

Priority order:
1. fix `backend/tests/test_seed_demo.py`
2. rerun full backend validation
3. add 1 shell e2e smoke test
4. update `ORCHESTRATOR.md`
5. reconcile hub-file discipline
6. bound `ChangeSignal` compatibility
7. finish `partner-submissions`
8. densify frontend confidence on key V2 surfaces
9. inventory new monolith hotspots

Return per wave:
- closed
- partial
- validations
- tests
- failures fixed
- blockers
- accepted debt
- next wave
```
