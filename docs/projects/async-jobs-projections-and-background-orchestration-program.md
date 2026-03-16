# Async Jobs, Projections, and Background Orchestration Program

## Mission

Turn long-running or recomputed product behaviors into an explicit background execution and projection layer that can scale with SwissBuildingOS.

## Why This Matters

The product now contains or is moving toward:

- dossier generation
- packs and exports
- search indexing
- campaign effects
- trust/readiness recomputation
- completion agents
- cross-building and cross-modal signals

If each of these evolves independently, the system risks:

- inconsistent job handling
- opaque progress
- duplicated retry logic
- poor replay/recovery
- expensive recomputation on read paths

## Core Outcomes

### 1. Long-running work becomes first-class

Expected:

- clearer job lifecycle
- better progress reporting
- better retry / failure semantics
- more consistent operator visibility

### 2. Projections become intentional

Expected:

- expensive summaries move out of ad hoc request-time computation when justified
- search and portfolio/intelligence surfaces can rely on maintained projections
- replay and backfill are possible

### 3. Agentic and export-heavy features scale more safely

Expected:

- bounded background orchestration for completion, packs, signals, indexing, and comparisons
- clearer foundations for future Temporal / worker / orchestration pulls if needed

## Recommended Workstreams

### Workstream A — Current job audit

- inventory current async or pseudo-async flows
- identify what is:
  - sync but should stay sync
  - sync but should become background
  - background but under-instrumented

### Workstream B — Projection candidates

- identify summary or intelligence surfaces that should become projection-backed
- likely candidates:
  - portfolio signals
  - pack/export status
  - search indexing
  - readiness/trust summaries
  - authority-ready dossier state

### Workstream C — Orchestration and recovery model

- define a consistent job/projection lifecycle
- align with reliability/recovery goals
- avoid building a giant orchestration platform prematurely

### Workstream D — UX and operator visibility

- progress tracking
- failure explanation
- replay/retry controls
- stale projection visibility

## Acceptance Criteria

- long-running product behavior has a clearer shared model
- projection-backed candidates are identified and optionally implemented where high-value
- retry/recovery/progress semantics are more consistent
- future agentic and export-heavy surfaces have stronger infrastructure

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
- `user_surface`: `internal / operator`
- `go_to_market_relevance`: `supporting`
- `moat_type`: `execution_infrastructure`
- `depends_on`: `exports + signals + search + growing async surface`
