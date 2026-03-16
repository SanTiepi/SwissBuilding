# Frontend Performance and Bundle Hardening Program

## Mission

Reduce frontend bundle weight, improve route-level loading behavior, and keep SwissBuildingOS fast as the product surface keeps expanding.

This is a structural hardening pass, not cosmetic micro-optimization.

## Why This Matters

Recent build validation remains green, and one important hardening step has already landed:

- the base `index` chunk was materially reduced by lazy-loading the remaining static route surfaces
- the old monolithic `map` route hotspot has now been broken up by lazy-loading `mapbox-gl` inside the map surfaces themselves
- `charts` are isolated, but the overall frontend is still growing quickly

If left untreated, the product will stay functionally impressive while feeling heavier than it should on:

- first load
- lower-powered laptops
- mobile or constrained networks
- embedded enterprise environments

## Core Outcomes

### 1. Route and capability chunking stays intentional

Keep a clear split between:

- app shell
- admin surfaces
- map surfaces
- chart-heavy portfolio surfaces
- dossier / export / intelligence surfaces

### 2. Heavy capabilities load only when truly needed

Expected:

- map stack stays isolated
- chart stack stays isolated
- comparison / explorer / simulator surfaces do not bloat the base shell
- rarely used admin or expert pages stay lazy

### 3. Performance becomes observable

Expected:

- capture the current chunk profile
- identify the main contributors to the base chunk
- document why each large chunk exists
- avoid blind “split everything” behavior

## Recommended Workstreams

### Workstream A — Build profile and attribution

- inspect current chunk composition
- identify why the base `index` chunk is still large
- identify routes/components that accidentally pull heavy shared dependencies early

### Workstream B — Chunking strategy hardening

- refine route-level lazy loading where low-risk
- improve `manualChunks` only when it improves real separation
- avoid tiny-chunk explosion and brittle chunk naming

### Workstream C — Heavy-surface ergonomics

- add or improve loading skeletons/placeholders for:
  - map surfaces
  - comparison dashboards
  - simulator pages
  - portfolio charts
- keep heavy routes feeling responsive while chunks load

### Workstream D — Regression guardrails

- document expected chunk categories
- add a lightweight check or acceptance target so bundle growth does not become invisible

## Current Observed Pressure

Current build output already shows:

- `assets/index-*.js` is now down to roughly `365 kB` and is no longer the main concern
- `assets/charts-*.js` is roughly `411 kB`, but now sits behind dedicated `DashboardCharts` / `PortfolioCharts` lazy boundaries
- map route shells are now tiny:
  - `PollutantMap-*.js` is roughly `5.5 kB`
  - `PortfolioRiskMap-*.js` is roughly `6.0 kB`
- the current production build remains green with `90` precache entries and roughly `1610.26 KiB` total precache size

Current working assumption:

- the next meaningful gains are likely in:
  - chart stack topology
  - shared code that still bloats the base shell
  - heavy intelligence/dashboard surfaces that may deserve deeper lazy boundaries

Treat this as a real optimization target, not just a warning to ignore forever.

## Acceptance Criteria

- build remains green
- chunking strategy is clearer and more intentional than before
- large shared dependencies are not pulled into the base shell without reason
- map/chart/admin/intelligence surfaces remain meaningfully separated
- loading behavior for heavy routes is acceptable and explicit
- documentation reflects the chosen chunking strategy

## Validation

Frontend:

- `cd frontend`
- `npm run validate`
- `npm test`
- `npm run build`

Optional:

- compare before/after build output and record the major chunk shifts

## Metadata

- `macro_domain`: `Infrastructure, Standards, and Intelligence Layer`
- `ring`: `ring_4`
- `user_surface`: `internal / all`
- `go_to_market_relevance`: `supporting`
- `moat_type`: `performance_and_operability`
- `depends_on`: `current frontend surface + vite chunk topology`
