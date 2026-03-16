# Test Right-Sizing and Integration Confidence Program

## Mission

Stop test growth from becoming breadth without depth.

Reshape the SwissBuildingOS test stack so it optimizes for:

- decision confidence
- integration truth
- fast diagnosis
- maintainability
- realistic product behavior

The goal is not fewer tests at any cost.
The goal is **more signal per test**, less duplicated broad coverage, and more proof that the real product chain works.

## Why This Matters

The repo now has:

- a very large backend service surface
- many route modules
- a growing number of frontend surfaces
- a high raw test count

The current risk is not “too little testing”.
The current risk is:

- oversized broad tests
- isolated calculator tests that do not prove composition
- synthetic confidence without realistic seeded scenarios
- maintenance surface growing faster than product truth

## Core Outcomes

### 1. The test pyramid becomes explicit again

Keep a clearer split between:

- pure unit tests
- API / router behavior tests
- domain-integration tests
- seeded scenario tests
- mock e2e smoke
- real e2e proof

### 2. Broad tests become thinner and more intentional

Expected:

- no giant “assert everything on one page” tests unless they prove a critical workflow
- fewer broad mock flows that duplicate what unit/API tests already prove
- each broad e2e should justify its cost

### 3. Full-chain integration confidence improves

Expected:

- canonical end-to-end seeded scenarios prove:
  - import
  - enrich
  - diagnose
  - action generation
  - readiness
  - dossier / pack generation
  - post-works / requalification where relevant

### 4. Service sprawl stops leaking into test sprawl

Expected:

- more tests at domain-facade / aggregate level
- fewer new isolated tests for every micro-service if a facade already proves the behavior
- dead or unconsumed services do not keep accumulating dedicated tests by default

### 5. Test signal becomes measurable

Expected:

- clearer notion of:
  - high-value tests
  - duplicated tests
  - flaky tests
  - expensive tests with low marginal signal

## Recommended Workstreams

### Workstream A — Test inventory and redundancy audit

- classify the current suite by:
  - unit
  - API
  - integration
  - mock e2e
  - real e2e
- identify broad tests that mostly re-assert lower-level coverage
- identify domain areas with many isolated calculator tests but little composed proof

### Workstream B — Canonical integration scenarios

Create a small number of high-value seeded scenario tests that prove real chains end to end.

Priority scenarios:

- import -> enrich -> readiness -> dossier
- contradiction -> trust -> action generation
- intervention -> post-works -> requalification
- authority-ready dossier / pack on realistic seed data

### Workstream C — Broad e2e right-sizing

- prune or slim broad mock e2e tests that duplicate unit/API coverage
- keep broad e2e for:
  - route wiring
  - key UX flows
  - regressions visible only at page/workflow level
- move detailed logic assertions down into targeted unit/API/integration tests
- promote **surface suites** over ad hoc broad reruns:
  - `trust`
  - `readiness`
  - `timeline`
  - `portfolio`
  - `dossier`
  - `shell`

### Workstream D — Facade-first backend testing

- when a bounded-context facade exists, prefer testing it over every inner helper independently
- only keep helper/service tests when:
  - logic is genuinely complex
  - logic is reused outside the facade
  - failure diagnosis would otherwise become opaque

### Workstream E — Seed realism over synthetic comfort

- prioritize realistic scenario datasets over large synthetic unit combinatorics
- extend `seed_verify.py` and scenario seeds to support integration truth
- make real e2e and demo scenarios share a stronger seeded backbone

## Concrete Guidance

Prefer this order when validating active frontend work:

1. targeted component/unit test
2. repo-level related-check suggestion:
   - `python scripts/run_related_checks.py <file>`
   - `python scripts/test_inventory.py --write` when deciding whether to grow or split a broad suite
3. relevant `test:surface` suite
4. `test:e2e:smoke` or `test:surface -- --with-e2e` if route wiring matters
5. full frontend suite only when the scope is broad enough to justify it

Use these rules when deciding whether to add a test:

1. Does this test prove something not already strongly covered?
2. Is this assertion best made at this layer?
3. Would one seeded integration scenario replace several isolated tests?
4. Is this test likely to fail with a clear diagnosis?
5. Does it improve confidence in the actual product chain, not just a local function?

If the answer is mostly “no”, do not add the test.

## Anti-Patterns to Reduce

- giant page tests that assert many unrelated concerns
- new e2e tests for behavior already proven by component/unit/API coverage
- backend micro-service test growth without matching UI or composed consumption
- synthetic test matrices that do not resemble actual SwissBuilding scenarios
- counting tests as a success metric by itself

## Acceptance Criteria

- a clear inventory exists of current test layers and redundancy hotspots
- a small set of canonical integration scenarios exists and is green
- at least some broad mock tests are simplified, merged, or demoted to lower layers
- new backend test additions follow facade/domain logic more often than micro-service logic
- the repo has a more credible “integration truth” signal than before
- the testing doctrine clearly favors signal quality over raw count

## Validation

Backend:

- `cd backend`
- `ruff check app/ tests/`
- `ruff format --check app/ tests/`
- `python -m pytest tests/ -q`

Frontend:

- `cd frontend`
- `npm run validate`
- `npm test`
- `npm run test:e2e`

Real integration when relevant:

- `cd frontend`
- `npm run test:e2e:real`

## Metadata

- `macro_domain`: `12_infrastructure_standards_and_intelligence`
- `ring`: `ring_1_to_4`
- `user_surface`: `internal / qa / all`
- `go_to_market_relevance`: `supporting`
- `moat_type`: `signal_quality_and_integration_truth`
- `depends_on`: `dataset strategy + full-chain integration + testing modernization`
