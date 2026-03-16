# Read Models, Query Topology, and Aggregate APIs Program

## Mission

Reduce query fragmentation, frontend waterfalls, and duplicated read composition by introducing better aggregate read models and API surfaces for SwissBuildingOS.

This program is about making a very large product feel coherent and efficient, not just “adding another endpoint”.

## Why This Matters

The product now has:

- many entity-specific APIs
- many frontend query surfaces
- increasingly rich building, portfolio, and readiness screens
- more cross-domain surfaces that need the same truth in slightly different shapes

Without explicit read-model design, the system risks:

- frontend query waterfalls
- duplicated composition logic in pages
- inconsistent fallback behavior
- more cache invalidation complexity
- slower productization of new intelligence layers

Recent lead-side review already shows this pattern clearly:

- `BuildingDetail` composes many independent reads
- some pages still mix query state and imperative fetch logic
- the frontend already contains a high number of query consumers across pages and components

## Core Outcomes

### 1. Aggregate read surfaces become intentional

Expected:

- building-level summary reads
- portfolio-level summary reads
- pack/export progress reads
- timeline/activity reads
- readiness/trust/completeness summary reads

### 2. Frontend pages compose less manually

Expected:

- fewer query waterfalls
- fewer separate fetches for one screen-level decision surface
- clearer ownership of:
  - shell read
  - detail read
  - heavy drill-down read

### 3. Cache topology becomes simpler

Expected:

- clearer query keys
- less accidental invalidation spread
- more predictable refresh behavior

## Recommended Workstreams

### Workstream A — Read surface audit

- inventory high-value pages with too many independent reads
- identify where a summary or projection endpoint is justified
- prioritize:
  - building detail
  - portfolio surfaces
  - comparison surfaces
  - readiness/trust dashboards

### Workstream B — Aggregate API design

- add low-regret read models where composition is repeated
- keep write APIs domain-specific
- avoid creating giant “god endpoints” with unstable shapes

### Workstream C — Frontend query topology cleanup

- migrate pages from ad hoc composition toward cleaner aggregate reads
- reduce imperative `useEffect` fetches when they belong in query topology
- standardize screen-level loading/error/empty states around the new read models

### Workstream D — Projection and summary discipline

- define which aggregates are:
  - live-computed
  - cached
  - projection-backed
- avoid recomputing expensive screen-level summaries everywhere

## Candidate Targets

- `BuildingDetail` summary aggregate
- portfolio execution aggregate
- pack/export status aggregate
- building comparison aggregate refinements
- trust/readiness/quality composite summary
- authority/contractor/owner pack summaries

## Acceptance Criteria

- fewer screen-level query waterfalls on major pages
- clearer screen-level ownership of `loading / error / empty / data`
- aggregate reads exist only where they reduce real complexity
- no duplication of the same read composition across many pages
- query invalidation remains understandable

## Validation

Backend if touched:

- `cd backend`
- `ruff check app/ tests/`
- `ruff format --check app/ tests/`
- `python -m pytest tests/ -q`

Frontend if touched:

- `cd frontend`
- `npm run validate`
- `npm test`
- `npm run build`

## Metadata

- `macro_domain`: `Infrastructure, Standards, and Intelligence Layer`
- `ring`: `ring_4`
- `user_surface`: `internal / all`
- `go_to_market_relevance`: `supporting`
- `moat_type`: `operating_coherence`
- `depends_on`: `current APIs + growing query surface`
