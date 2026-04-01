# Claude One-Shot Finisher Pack

Date de controle: `25 mars 2026`

## Purpose

This pack exists for one case only:

- Claude should stop thinking in many small waves
- the repo already contains enough strategic guidance
- the next useful move is one coherent macro-slice

The goal is to finish the highest-value product jump in one pass.

## One-shot outcome

Ship one integrated slice where SwissBuilding becomes obviously stronger on:

- procedure state
- operating inbox
- proof trace
- confidence and review visibility
- freshness and identity safety
- authority-facing execution

In product terms, this should make one building feel:

- understandable
- actionable
- procedurally ready
- proof-backed
- authority-operable

## First, remove active noise

Do not start the macro-slice while the active auth regression cluster is still
noisy.

First close:

- `unauthenticated 401 vs 403`

Use:

- [auth-regression-sweep-pack-2026-03-25.md](./auth-regression-sweep-pack-2026-03-25.md)

Rule:

- no repeated full backend runs before the cluster is closed

## Macro-slice composition

This one-shot combines these existing briefs:

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

## Non-negotiable rules

- `egid` is never `egrid`
- `egrid` is never `official_id`
- no second permit engine beside `permit_tracking`
- no second deadline entity beside `Obligation`
- no second persistent action system beside the canonical sources aggregated by
  `ControlTower`
- no second DMS or proof storage layer
- preserve `Batiscan` as diagnostic source of truth
- preserve `SwissBuilding` as building workspace source of truth
- do not edit reserved hub files directly during sub-work:
  - `backend/app/api/router.py`
  - `backend/app/models/__init__.py`
  - `backend/app/schemas/__init__.py`
  - `frontend/src/i18n/{en,fr,de,it}.ts`

## Internal execution order

### Phase A - Canonical backend spine

Build or complete the shared backend primitives first:

- `PermitProcedure`
- `PermitStep`
- `AuthorityRequest`
- `ProofDelivery`
- shared confidence, freshness, and identity semantics

This phase should also ensure:

- procedure steps and requests can project blockers
- proof and procedure objects can be linked without JSON-only glue
- identity resolution stays explicit and explainable

### Phase B - Aggregation and projection

Project those primitives into the canonical read surfaces:

- `ControlTower`
- building detail procedure surfaces
- proof history and delivery trace
- blocker summaries
- review-required states
- freshness states

Rule:

- build one operating story, not isolated widgets

### Phase C - Authority room

Make the authority path feel operational:

- current procedure state
- active submission room
- current proof set
- complement loop
- acknowledgement or resend trace
- next move

### Phase D - Proof reuse and seeds

Make the value obvious with reusable proof stories:

- seeded proof-reuse scenarios
- must-win workflow instrumentation
- explicit confidence ladder output
- explicit freshness and identity hints

### Phase E - Final polish for trust

Before calling it done, remove the trust gaps that make the slice feel fake:

- stale facts must not look current
- ambiguous identity must not look certain
- review-required branches must be visible
- blockers must route to a person or org, not stay abstract

## What this one-shot must NOT include

Do not widen into:

- full SwissRules watch implementation
- partner marketplace behavior
- generic portfolio analytics
- openBIM authoring
- territory/public-systems expansion
- pricing, CRM, or buyer-packaging work

Those are follow-on blocks, not part of the finishing slice.

## Minimum file zones

Expected write zones:

- `backend/app/models/`
- `backend/app/schemas/`
- `backend/app/services/`
- `backend/app/api/`
- `backend/alembic/versions/`
- `backend/tests/`
- `frontend/src/api/`
- `frontend/src/components/`
- `frontend/src/pages/`
- `frontend/src/components/__tests__/`
- `frontend/e2e-real/` only if one golden path needs extension

Expected no-touch zones:

- reserved hub files
- unrelated ERP or legacy breadth areas

## Acceptance story

The one-shot is successful when one seeded building can demonstrate all of this:

1. the building opens with explicit blockers, deadlines, proof state, and
   freshness state
2. a procedure is visible with ordered steps and current status
3. an authority request or complement loop is visible and actionable
4. existing proof can be reused instead of rebuilt
5. delivery and acknowledgement trace are visible
6. ambiguity is shown through confidence and review state
7. identity is explicit and safe enough to avoid silent drift

## Validation discipline

### Before implementation

- close the auth cluster first

### During implementation

- use changed-file loops only
- prefer targeted backend integration tests over broad suite reruns
- prefer targeted frontend tests over broad suite reruns

### Before closeout

Run:

- `cd backend && ruff check app/ tests/`
- `cd backend && ruff format --check app/ tests/`
- `cd backend && python scripts/run_local_test_loop.py changed`
- `cd backend && python scripts/run_local_test_loop.py confidence`
- `cd frontend && npm run validate`
- `cd frontend && npm run test:changed:strict`

Optional, if real environment is ready:

- one golden-path real e2e covering building -> procedure -> proof ->
  authority-facing flow

Full backend or frontend suite:

- only once at the end
- only after targeted loops are already green

## Read order for this pack

1. [claude-now-priority-stack-2026-03-25.md](./claude-now-priority-stack-2026-03-25.md)
2. this pack
3. [claude-wave-brief-kit-2026-03-25.md](./claude-wave-brief-kit-2026-03-25.md)
4. [authority-submission-room-pack-2026-03-25.md](./authority-submission-room-pack-2026-03-25.md)
5. [confidence-ladder-and-manual-review-pack-2026-03-25.md](./confidence-ladder-and-manual-review-pack-2026-03-25.md)
6. [data-freshness-and-staleness-contract-2026-03-25.md](./data-freshness-and-staleness-contract-2026-03-25.md)
7. [must-win-workflow-map-2026-03-25.md](./must-win-workflow-map-2026-03-25.md)

## Final rule

Do not treat this as ten separate waves.

Treat it as one coherent product jump with one acceptance story.
