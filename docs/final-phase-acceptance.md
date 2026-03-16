# Final Phase Acceptance

Use this checklist before accepting a "done" claim for the current dataset/UI/test hardening phase.

## Acceptance Gates

### 1. Dataset Flow

- `python -m app.seeds.seed_data` stays network-free
- `python -m app.seeds.seed_demo ...` is the explicit enriched-demo entry point
- Vaud imports and demo enrichment use consistent dataset identifiers
- imported Vaud buildings are prioritized intentionally when enrichment says they are
- reseed / rerun behavior is documented and reasonably idempotent

### 2. Test Topology

- mock e2e and real e2e are clearly separated
- mock suite remains fast and self-contained
- real suite targets the running app and seeded backend without route mocks
- commands for backend, frontend, mock e2e, and real e2e are explicit and reproducible

### 3. Coverage Expectations

The enriched dataset should make these screens meaningfully testable:

- login
- dashboard
- buildings list
- building detail
- diagnostic detail
- documents
- risk simulator
- map
- settings

The dataset should include at least:

- buildings with no diagnostics
- draft / in-progress / completed / validated diagnostics
- samples across multiple pollutant types
- documents across multiple document types
- timeline/event coverage
- varied risk levels
- some incomplete but non-broken cases

### 4. UI Review Evidence

- Playwright screenshot or interaction audit exists for desktop and mobile
- any final UI/UX claim distinguishes:
  - mock rendering validation
  - real backend-seeded validation
- final review notes identify what was fixed, simplified, or intentionally deferred

### 5. Repo Hygiene

- no duplicated source-of-truth text across `CLAUDE.md`, `AGENTS.md`, and `MEMORY.md`
- no stale docs or comments that contradict code
- no repeated business literals where a shared constant is the safer option
- no overlapping scripts with unclear purpose

## Rejection Triggers

Do not accept "all done" if any of these remain true:

- a doc claims behavior the code does not implement
- a test validates mocked data while the summary claims real integration coverage
- a dataset priority rule depends on a mismatched string literal
- a new flow exists but has no clear command to run it
- a review summary hides remaining blockers behind passing mocked tests

## Required Delivery Evidence

Ask for all of the following:

- commands actually run
- test results actually observed
- exact commands for start / seed / mock e2e / real e2e
- explicit statement of what was validated on mocks vs real seeded data
- remaining risks or deferred work
