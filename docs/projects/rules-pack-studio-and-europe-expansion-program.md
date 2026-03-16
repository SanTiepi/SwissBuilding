# Rules Pack Studio and Europe Expansion Program

## Mission

Build the internal and product foundations that let SwissBuildingOS scale from:

- Swiss wedge

to:

- Europe-ready rules and workflow architecture

without rewriting the core product each time a new jurisdiction is added.

## Why This Matters

The moat will not come from hard-coding more local rules forever.
It will come from a productized rules architecture:

- Europe model
- country layer
- canton / state / region layer
- authority layer
- workflow / playbook layer

## Core Outcomes

### 1. Rules Pack Studio foundations

Expected:

- internal tools or admin surfaces to author, compare, validate, and version rules packs

### 2. Regulatory diffing

Expected:

- compare:
  - Europe vs country vs canton
  - older vs newer pack versions
  - obligations by stage and intervention type

### 3. Rules-driven readiness

Expected:

- readiness and pack generation consume the layered rules architecture cleanly

## Recommended Workstreams

### Workstream A — Rules model hardening

- pack structure
- inheritance / override logic
- versioning rules

### Workstream B — Authoring and validation tooling

- pack validation
- conflict detection
- missing-rule detection

### Workstream C — Diff and explainability

- why a rule applies
- what changed between packs
- which authority or jurisdiction layer drove the result

## Acceptance Criteria

- rules expansion no longer requires repeated hard-coded logic
- at least one useful rules diff or pack validation surface exists
- the architecture feels Europe-ready, not Swiss-hardcoded

## Validation

Backend:

- `cd backend`
- `ruff check app/ tests/`
- `ruff format --check app/ tests/`
- `python -m pytest tests/ -q`

Frontend if touched:

- `cd frontend`
- `npm run validate`
- `npm test`
- `npm run test:e2e`
- `npm run build`
