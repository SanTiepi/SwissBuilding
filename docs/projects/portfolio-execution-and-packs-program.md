# Portfolio Execution and Packs Program

## Mission

Turn SwissBuildingOS from:

- a portfolio dashboard and dossier generator

into:

- a portfolio execution system that recommends campaigns, tracks export progress, and produces the right pack for the right actor

## Why Now

The repo already has:

- campaigns
- search
- export jobs
- dossiers
- saved simulation foundations
- portfolio dashboard foundations

The next step is to make the portfolio actionable and the packs operational.

## Core Outcomes

### 1. Campaign recommendation logic

Expected:

- recommend which campaign to run next based on:
  - readiness gaps
  - risk clusters
  - pollutant prevalence
  - documentation debt
  - trust deficits

### 2. Campaign progress and impact visibility

Expected:

- show progress beyond a static list
- reveal:
  - buildings covered
  - blockers
  - completed actions
  - impact on risk/readiness/completeness where feasible

### 3. Export job progress becomes visible

Expected:

- real-time or poll-based status UI
- recovery-friendly UX
- clear download / retry states

### 4. SavedSimulation becomes product-visible

Expected:

- save and compare building scenarios
- use them as portfolio decision inputs later

### 5. Pack scaffolding expands beyond dossier

Expected low-regret scaffolding for:

- `AuthorityPack`
- `ContractorPack`
- `OwnerPack`

The goal is not full final polish, but reusable pack architecture.

## Recommended Workstreams

### Workstream A — Campaign recommendation engine

- backend recommendation logic
- explainable outputs
- seed data support

### Workstream B — Campaign progress UI

- progress / impact states
- useful filters
- no faux-enterprise clutter

### Workstream C — Export job progress UI

- statuses
- polling / refresh behavior
- success / failure / retry

### Workstream D — Saved simulation UI

- save
- load
- compare

### Workstream E — Pack scaffolding

- internal pack object structure
- export hooks
- preparation for authority / contractor / owner variants

## Acceptance Criteria

- campaigns are recommendable, not just creatable
- portfolio users can see what is moving and what is blocked
- long-running exports feel operational
- saved simulations are no longer backend-only
- pack architecture can grow without redesign

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
- `npm run build`
