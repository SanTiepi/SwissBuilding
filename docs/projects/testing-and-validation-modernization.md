# Testing and Validation Modernization

## Mission

Upgrade SwissBuildingOS testing and validation so the test stack keeps up with the expanding product surface, rather than lagging behind it.

This project should improve:

- confidence
- speed
- signal quality
- maintainability
- separation between mock, real, and seeded integration validation

## Why This Matters

The product now includes:

- physical building modeling
- evidence chain
- dossiers and exports
- jurisdictions and regulatory packs
- campaigns
- search
- trust/readiness/data quality primitives

The old testing structure must keep evolving with that complexity.

The goal is not “more tests for the sake of more tests”.
The goal is:

- stronger product confidence
- cleaner failure diagnosis
- less brittle UI and e2e coverage
- clearer ownership of what is mocked vs real

Recent Codex QA has also highlighted a narrower but important gap:

- newer trust/readiness/passport/time-machine surfaces need explicit targeted frontend coverage as they are productized
- the gap should be closed incrementally instead of relying only on broader e2e/page flows

## Core Outcomes

### 1. Test topology stays explicit

Keep clear separation between:

- backend unit / API tests
- frontend unit tests
- mock e2e
- real e2e
- seeded scenario validation
- visual regression

### 2. Testing utilities evolve with the product

Expected:

- shared fixtures for new product domains
- less duplicated mocking
- better reusable helpers for:
  - campaigns
  - dossiers
  - search
  - trust/readiness/data quality
  - authority / pack workflows later

### 3. Visual regression becomes less flaky

Expected:

- reduce or eliminate pre-existing flaky snapshot baselines
- improve determinism for new pages
- document what is intentionally excluded from visual diffing

### 4. Real integration confidence improves

Expected:

- cleaner `test:e2e:real` environment targeting
- explicit seeded prerequisites
- clearer failure messages when the wrong backend or seed state is present

### 5. Testing ergonomics improve

Expected:

- scripts / tasks / docs remain aligned
- better changed-files-first validation where useful
- no IDE-only hidden testing logic
- optional VS Code testing accelerators should mirror the repo scripts rather than invent a parallel workflow

## Recommended Workstreams

### Workstream A — Mock e2e helper modernization

- shared helpers for new domains
- cleaner state setup
- reusable fixtures for campaigns, dossier, readiness, trust, search

### Workstream B — Real e2e hardening

- backend target ownership
- seeded-state preflight
- clearer diagnostics
- reduce false negatives caused by environment mismatch

### Workstream C — Visual regression cleanup

- fix known flakes
- stabilize deterministic states
- reduce noisy snapshots

### Workstream D — Seed-aware validation

- extend `seed_verify.py` or equivalent checks
- assert that required entities exist for real e2e and demo scenarios

### Workstream E — Validation tooling alignment

- make sure scripts, tasks, docs, and control plane all still match reality
- improve test commands only if it reduces friction without hiding signal

## Current Observed Friction

The first wave of frontend unit warning cleanup has largely landed.
The remaining friction is now more structural than noisy:

- real e2e environment risk:
  - `test:e2e:real` can still hit the wrong backend target if local ownership is ambiguous
- bundle topology and chunk size:
  - `assets/index-*.js` was materially reduced by lazy-loading the remaining static route surfaces
  - `assets/map-*.js` is now the dominant remaining warning surface and the next meaningful frontend perf target

Historical note:

- the former `act(...)` and React Router warning hotspots were valid cleanup targets and have now mostly been absorbed on the lead-side QA stream

Rule:
- prefer removing warning causes over muting them
- when intentional stderr is part of a test, make that explicit and scoped

Recently closed focused targets:

- dedicated frontend coverage now exists for:
  - `frontend/src/components/__tests__/PassportCard.test.tsx`
  - `frontend/src/components/__tests__/ContradictionCard.test.tsx`
  - `frontend/src/components/__tests__/TimeMachinePanel.test.tsx`
  - `frontend/src/components/__tests__/ReadinessWallet.test.tsx`
- validated by:
  - `npm test -- PassportCard ContradictionCard TimeMachinePanel ReadinessWallet` -> `12 passed`
  - `npm test` -> `166 passed`
- these surfaces now have both explicit inline/toast error handling and focused regression coverage

More recently closed focused targets:

- dedicated frontend coverage now exists for:
  - `frontend/src/components/__tests__/PostWorksDiffCard.test.tsx`
  - `frontend/src/components/__tests__/PortfolioSignalsFeed.test.tsx`
- validated by:
  - `npm test -- PostWorksDiffCard PortfolioSignalsFeed` -> `4 passed`
  - `npm test` -> `166 passed`
- both surfaces now render explicit inline error states instead of collapsing failures into empty/spinner fallbacks
- the previous Vitest `ErrorBoundary` stderr noise has been eliminated on this branch

Newest recently closed focused targets:

- dedicated frontend coverage now exists for:
  - `frontend/src/components/__tests__/TrustScoreCard.test.tsx`
  - `frontend/src/components/__tests__/UnknownIssuesList.test.tsx`
  - `frontend/src/components/__tests__/ChangeSignalsFeed.test.tsx`
  - `frontend/src/components/__tests__/CompletenessGauge.test.tsx`
- validated by:
  - `npm test -- TrustScoreCard UnknownIssuesList ChangeSignalsFeed CompletenessGauge` -> `8 passed`
  - `npm test` -> `166 passed`
- these surfaces now render explicit inline error states instead of silently degrading into no-data states when their queries fail

Latest recently closed focused targets:

- dedicated frontend coverage now exists for:
  - `frontend/src/components/__tests__/DataQualityScore.test.tsx`
  - `frontend/src/components/__tests__/ReadinessSummary.test.tsx`
  - `frontend/src/components/__tests__/ProofHeatmapOverlay.test.tsx`
- validated by:
  - `npm test -- DataQualityScore ReadinessSummary ProofHeatmapOverlay` -> `14 passed`
  - `npm run validate` -> green
  - `npm test` -> `166 passed`
  - `npm run build` -> green
- `DataQualityScore`, `ReadinessSummary`, and `ProofHeatmapOverlay` now render explicit error states instead of collapsing API failures into misleading empty/no-data views
- `Campaigns.tsx` timeline purity was fixed so frontend validate/build return to green on this branch

Newest recently closed focused targets:

- dedicated frontend coverage now exists for:
  - `frontend/src/components/__tests__/EvidenceChain.test.tsx`
  - `frontend/src/components/__tests__/NotificationBell.test.tsx`
- validated by:
  - `npm test -- EvidenceChain NotificationBell` -> `10 passed`
  - `npm run validate` -> green
  - `npm test` -> `168 passed`
  - `npm run build` -> green
- `EvidenceChain` now renders an explicit inline error state instead of silently degrading to empty/no-data
- `NotificationBell` now distinguishes loading, error, and empty states for recent notifications
- React Router warning noise was eliminated from the new `NotificationBell` test by enabling the future flags in the test harness

Newest recently closed focused targets:

- dedicated frontend coverage now exists for:
  - `frontend/src/components/__tests__/BuildingDetailPage.test.tsx`
- validated by:
  - `npm run validate` -> green
  - `npm test` -> `175 passed | 1 skipped`
  - `npm run build` -> green
- `BuildingDetail` now renders explicit error states for:
  - open actions query failures
  - activity tab query failures
  - documents load failures
- one documents-tab interaction assertion remains intentionally skipped rather than leaving a flaky test in the suite; the product behavior is now explicit, but the dedicated assertion still needs a more stable interaction harness

Latest recently closed focused targets:

- dedicated frontend coverage now exists for:
  - `frontend/src/components/__tests__/BuildingTimeline.test.tsx`
- validated by:
  - `npm test -- BuildingTimeline` -> `4 passed`
  - `npm run validate` -> green
  - `npm test` -> `176 passed | 1 skipped`
  - `npm run build` -> green
- `BuildingTimeline` now renders an explicit inline error state instead of degrading to a generic plain fallback when its query fails

Latest recently closed focused targets:

- dedicated frontend coverage now exists for:
  - `frontend/src/components/__tests__/ExportJobs.test.tsx`
  - `frontend/src/components/__tests__/SafeToXCockpit.test.tsx`
- validated by:
  - `npm test -- ExportJobs SafeToXCockpit` -> `4 passed`
  - `npm run validate` -> green
  - `npm test` -> `180 passed | 1 skipped`
- `ExportJobs` now has explicit focused coverage for:
  - load failure
  - empty state
- `SafeToXCockpit` now has explicit focused coverage for:
  - load failure
  - loaded readiness cards
- the React Router future-flag warning noise in the new `ExportJobs` harness has been removed

Latest recently closed focused targets:

- dedicated frontend coverage now exists for:
  - `frontend/src/components/__tests__/RequalificationTimeline.test.tsx`
- validated by:
  - `npm test -- RequalificationTimeline` -> `2 passed`
  - `npm run validate` -> green
  - `npm test` -> `182 passed | 1 skipped`
- `RequalificationTimeline` now has explicit focused coverage for:
  - query failure
  - empty timeline state

Latest recently closed focused targets:

- dedicated frontend coverage now exists for:
  - `frontend/src/components/__tests__/TransferPackagePanel.test.tsx`
- validated by:
  - `npm test -- TransferPackagePanel` -> `2 passed`
  - `npm run validate` -> green
  - `npm test` -> `184 passed | 1 skipped`
  - `npm run build` -> green
- `TransferPackagePanel` now has focused coverage for:
  - generation failure with explicit inline error state + toast
  - successful generation summary rendering + JSON download affordance
- route-level bundle topology was also improved in the same hardening pass:
  - the remaining static routes in `App.tsx` were moved to lazy loading
  - `assets/index-*.js` dropped from roughly `643 kB` to roughly `364 kB`
  - the primary remaining perf residue is now `assets/map-*.js`

- component-test runner stability was also hardened:
  - `QueryClient` harnesses now standardize on `gcTime: 0` across the focused component test suite
  - `vitest` now runs with `fileParallelism: false` for this repo to reduce jsdom/react-query flake and timer bleed
  - `CommandPalette.test.tsx` now uses a stable i18n mock and deterministic RAF stub instead of timing-sensitive defaults
  - full frontend unit baseline after this hardening pass is `186 passed | 1 skipped`

- chart-heavy surfaces were also productized more cleanly:
  - `Dashboard` and `Portfolio` now lazy-load their chart blocks through dedicated wrappers
  - `assets/index-*.js` now sits at roughly `365 kB`
  - `assets/charts-*.js` sits at roughly `411 kB`
  - `PollutantMap` and `PortfolioRiskMap` now lazy-load `mapbox-gl` dynamically
  - the former route-level `map` hotspot is gone; the next perf targets are `charts` and remaining shared-shell creep

Recent tooling alignment:

- `.vscode/extensions.json` now recommends the Vitest extension alongside Playwright/Python tooling
- `.vscode/tasks.json` now exposes explicit test tasks for:
  - repo related checks
  - frontend confidence suite
  - frontend surface suite
  - frontend surface suite + e2e
  - frontend unit tests
  - frontend mock e2e smoke
  - frontend mock e2e
  - frontend real e2e
  - backend confidence suite
  - backend tests
  - backend seed verification
- these remain optional accelerators only; repo scripts and CLI commands are still the source of truth

Current fast-confidence path:

- repo:
  - `python scripts/run_related_checks.py --list`
  - `python scripts/run_related_checks.py frontend/src/pages/ReadinessWallet.tsx`
  - `python scripts/run_related_checks.py frontend/e2e-real/smoke.spec.ts`
  - `python scripts/run_related_checks.py --run frontend/src/pages/ReadinessWallet.tsx`
  - `python scripts/test_inventory.py --write`
  - `python scripts/test_budget_guard.py --write-current`
  - `python scripts/lead_control_plane_check.py --strict`
  - `python scripts/frontend_async_state_audit.py --write --strict`
- frontend:
  - `npm run test:unit:critical`
  - `npm run test:surface:list`
  - `npm run test:surface -- readiness`
  - `npm run test:surface -- trust --with-e2e`
  - `npm run test:e2e:smoke`
  - `npm run test:e2e:real:preflight`
  - `npm run test:confidence`
- backend:
  - `python scripts/run_confidence_suite.py --list`
  - `python scripts/run_confidence_suite.py`

Intent:

- give the team and agents a higher-signal, lower-cost validation path than full-suite runs
- add product-surface suites so the repo can validate by domain (`trust`, `readiness`, `timeline`, `portfolio`, `dossier`, `shell`) instead of jumping straight from a tiny targeted test to the full frontend suite
- add a repo-level related-checks runner so agents can infer the smallest sensible validation path from touched files instead of guessing
- keep full-suite runs for:
  - merge confidence
  - architecture shifts
  - repo-wide refactors
  - maturity-gate acceptance

Validated examples:

- `python scripts/run_related_checks.py --run frontend/src/pages/ReadinessWallet.tsx`
  - inferred `readiness`
  - executed the matching surface suite successfully (`12 passed`)
- `python scripts/run_related_checks.py --run backend/app/services/passport_service.py`
  - inferred backend confidence group `operating`
  - executed successfully (`94 passed`)
- `python scripts/test_inventory.py --write`
  - generated `docs/test-inventory.md` and `docs/test-inventory.json`
  - surfaced the current large-suite review targets instead of relying on intuition
- `python scripts/lead_control_plane_check.py --strict`
  - verified control-plane hygiene (`Next 10` count + required sections/files)
- `python scripts/frontend_async_state_audit.py --write --strict`
  - verified explicit async error handling coverage for all query-driven surfaces
  - writes:
    - `docs/frontend-async-state-audit.md`
    - `docs/frontend-async-state-audit.json`
- `python scripts/test_budget_guard.py --write-current`
  - enforces growth guardrails for oversized and broad suites
  - baseline/config:
    - `docs/test-budget-guard.json`
  - uses current test inventory snapshot to fail fast on runaway suite growth
- `npm run test:e2e:real:preflight`
  - validates backend reachability and seeded-state minimums before real Playwright runs
  - checks:
    - `/health`
    - `/api/v1/auth/login`
    - `/api/v1/auth/me`
    - minimum building and diagnostic counts for real-e2e viability
  - env overrides:
    - `E2E_REAL_API_BASE`
    - `E2E_REAL_ADMIN_EMAIL`
    - `E2E_REAL_ADMIN_PASSWORD`
    - `E2E_REAL_MIN_BUILDINGS`
    - `E2E_REAL_MIN_DIAGNOSTICS`
  - script:
    - `frontend/scripts/e2e_real_preflight.mjs`
- `python scripts/run_related_checks.py frontend/e2e-real/smoke.spec.ts`
  - now infers and recommends `npm run test:e2e:real:preflight` for real-e2e touched files

Current inventory hotspots from `docs/test-inventory.md`:

- backend:
  - `backend/tests/test_compliance_edge_cases.py`
  - `backend/tests/test_transaction_readiness.py`
  - `backend/tests/test_access_control.py`
  - `backend/tests/test_occupant_safety.py`
  - `backend/tests/test_timeline_enrichment.py`
- frontend broad mock e2e:
  - `frontend/e2e/buildings.spec.ts`
  - `frontend/e2e/pages.spec.ts`

## Candidate Improvements

- domain-specific Playwright fixtures
- better test data builders for frontend mocks
- richer backend factories for campaigns, packs, trust/readiness objects
- preflight check before `test:e2e:real`
- snapshot naming and grouping cleanup
- selective visual regression suites by area
- more explicit environment banners in real e2e

## Acceptance Criteria

- mock and real test layers remain clearly separated
- new domains have reusable fixtures/helpers instead of ad hoc duplication
- visual regression flakes are reduced
- real e2e fails fast when environment is wrong
- validation docs and commands still reflect reality

## Validation

Backend if touched:

- `cd backend`
- `ruff check app/ tests/`
- `ruff format --check app/ tests/`
- `python -m pytest tests/ -q`

Frontend:

- `cd frontend`
- `npm run validate`
- `npm test`
- `npm run test:e2e`
- `npm run build`

Real integration if touched:

- `cd frontend`
- `npm run test:e2e:real`
