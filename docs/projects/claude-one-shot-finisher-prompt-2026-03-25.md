# Claude One-Shot Finisher Prompt

Use this prompt when the goal is to stop re-planning and finish the highest
value slice in one coherent pass.

```text
Claude,

Ignore the usual small-wave cadence for this restart.

Your job is to finish one coherent macro-slice, not to open another planning
loop.

Immediate precondition:
- close the backend auth regression cluster `unauthenticated 401 vs 403`
- do not run repeated full backend suites until that cluster is closed

Read in this order:
1. `docs/projects/claude-now-priority-stack-2026-03-25.md`
2. `docs/projects/claude-one-shot-finisher-pack-2026-03-25.md`
3. `docs/projects/claude-wave-brief-kit-2026-03-25.md`
4. `docs/projects/authority-submission-room-pack-2026-03-25.md`
5. `docs/projects/confidence-ladder-and-manual-review-pack-2026-03-25.md`
6. `docs/projects/data-freshness-and-staleness-contract-2026-03-25.md`
7. `docs/projects/must-win-workflow-map-2026-03-25.md`

This one-shot combines:
- `1` PermitProcedure Core
- `2` ControlTower v2
- `3` ProofDelivery
- `25` Must-Win Workflow Instrumentation
- `26` Proof Reuse Scenario Seeds
- `27` Confidence Ladder and Review Queue Foundations
- `31` Switching Cost Removal Foundations
- `32` Freshness and Staleness Foundations
- `33` Canonical Identity Resolution Foundations
- `51` Authority Submission Room Foundations

Non-negotiable rules:
- `egid` != `egrid` != `official_id`
- no second permit engine beside `permit_tracking`
- no second deadline entity beside `Obligation`
- no second persistent action system
- no second DMS or proof storage layer
- keep `Batiscan` as diagnostic source of truth
- keep `SwissBuilding` as building workspace source of truth
- do not directly edit reserved hub files

Implementation order:
1. canonical backend spine
2. aggregation into ControlTower and building surfaces
3. authority submission room
4. proof reuse and seeded acceptance path
5. trust polish on confidence, freshness, and identity

Required product result:
- one building becomes obviously understandable
- blockers and next actions are explicit
- procedure state is visible and ordered
- proof can be reused instead of rebuilt
- authority-facing work feels like a bounded room
- ambiguous or stale facts are visible, not hidden

Validation discipline:
- during work: changed-file loops only
- before closeout:
  - `cd backend && ruff check app/ tests/`
  - `cd backend && ruff format --check app/ tests/`
  - `cd backend && python scripts/run_local_test_loop.py changed`
  - `cd backend && python scripts/run_local_test_loop.py confidence`
  - `cd frontend && npm run validate`
  - `cd frontend && npm run test:changed:strict`
- full backend or frontend suites only once at the end

Acceptance story:
1. the building opens with blockers, deadlines, proof, and freshness visible
2. a procedure is visible with current step and state
3. an authority request or complement loop is actionable
4. proof reuse is visible and traced
5. delivery and acknowledgement history are visible
6. confidence and review state are explicit
7. identity semantics are safe and explainable

Do not stop at partial foundations.
Finish the macro-slice, then report:
- what shipped
- what remains intentionally deferred
- what was validated
```
