# Frontend Async State Standardization Program

## Mission

Standardize how SwissBuildingOS frontend surfaces render asynchronous data so new product capabilities stop reintroducing the same `loading / error / empty / data` drift.

This is not a cosmetic cleanup. It is a structural productization pass meant to reduce repeated QA patches and make the UI more trustworthy as the system grows.

## Why This Matters

Recent lead-side QA has repeatedly found the same class of issues:

- query failures collapsing into misleading empty states
- cards implying "no data" when the API actually failed
- inconsistent inline vs toast vs silent fallback behavior
- newer intelligence surfaces shipping with good backend logic but weaker UX state discipline

The product now has many async surfaces:

- trust
- readiness
- unknowns
- contradictions
- passport
- time machine
- post-works
- signals
- dossiers
- packs
- portfolio intelligence

Those surfaces need a stable contract.

## Current Audit Status

Lead-side QA has already closed many of the most obvious regressions on:

- readiness
- trust
- unknowns
- contradictions
- passport
- time machine
- post-works
- portfolio signals
- evidence chain
- notification surfaces
- building timeline

Additional note:

- a broad scan of the remaining `useQuery` surfaces did not reveal any new obvious panels that completely lack explicit error handling
- this means the next meaningful gain is less about one-off fixes and more about:
  - shared async-state primitives
  - cleaner hook/component contracts
  - aggregate reads that reduce repeated per-card query branching
  - targeted perf and query-topology cleanup

## Core Outcomes

### 1. Async surfaces follow a shared state model

Every major async surface should fit one of a small number of explicit patterns:

- loading
- error
- empty
- data

Rule:
- do not silently map API failure to empty/no-data

### 2. Reusable UI primitives exist for common async cards

Expected:

- card-level async shells
- list-level async shells
- centered error/empty blocks
- consistent retry affordance when relevant

### 3. Hooks and components stop splitting responsibility arbitrarily

Expected:

- shared guidance on what belongs in:
  - query hook
  - view-model/helper
  - component rendering
- less repeated ad hoc branching in pages

### 4. Tests cover the state contract, not only the happy path

Expected:

- each new intelligence-style component gets targeted error coverage
- a new surface should not rely only on broad e2e/page flows for failure handling confidence

## Recommended Workstreams

### Workstream A - State pattern audit

- inventory high-value async surfaces
- group them by pattern:
  - metric card
  - list feed
  - timeline
  - tab content
  - action panel
- identify outliers and repeated mistakes

### Workstream B - Shared primitives

- create or refine low-risk shared UI helpers for:
  - async card shell
  - explicit empty state
  - explicit error state
  - retry affordance where meaningful

### Workstream C - Hook contract cleanup

- reduce duplicate branching between hooks and components
- define a cleaner contract for:
  - data present
  - no data
  - hard error
  - mutation side effects / toasts

### Workstream D - Targeted migration of critical surfaces

Priority surfaces:

- BuildingDetail intelligence panels
- readiness / trust / unknowns / contradictions
- portfolio intelligence cards and feeds
- pack/export status cards
- campaign and signal surfaces

### Workstream E - Regression coverage

- add focused tests where the shared pattern is adopted
- document what remains intentionally deferred

## Suggested Improvement Targets

- `BuildingDetail`
- `ReadinessWallet`
- `PassportCard`
- `TrustScoreCard`
- `UnknownIssuesList`
- `ChangeSignalsFeed`
- `ContradictionCard`
- `PostWorksDiffCard`
- `PortfolioSignalsFeed`
- `EvidenceChain`
- future export / campaign / pack surfaces

## Acceptance Criteria

- critical async surfaces stop conflating API failure with empty state
- repeated rendering patterns are reduced
- new async cards use shared primitives/contracts where low-risk
- focused tests exist for migrated high-value surfaces
- the product feels more trustworthy because failures are explicit and consistent

## Validation

Frontend:

- `cd frontend`
- `npm run validate`
- `npm test`
- `npm run build`

Optional:

- rerun targeted suites for migrated surfaces before promoting the workstream as complete

## Metadata

- `macro_domain`: `Infrastructure, Standards, and Intelligence Layer`
- `ring`: `ring_2_to_4`
- `user_surface`: `internal / all`
- `go_to_market_relevance`: `supporting`
- `moat_type`: `productization_discipline`
- `depends_on`: `current frontend query topology + testing modernization`
