# Constraint Graph and Dependency Intelligence Program

## Mission

Turn SwissBuildingOS into a system that can explain not only what exists, but what blocks what, what depends on what, and which minimal move would unlock the most value or readiness.

## Why This Matters

Most building software shows:
- issues
- actions
- documents
- statuses

Very few systems explain:
- which blocker is upstream
- which missing proof invalidates several downstream states
- which dependency chain causes delay or rework
- what the smallest unlocking action is

This turns the product from a record system into a true decision engine.

## Recommended Workstreams

### Workstream A - Constraint graph model

Candidate objects:
- `ConstraintNode`
- `DependencyEdge`
- `BlockingCondition`

### Workstream B - Unlock opportunity logic

Candidate objects:
- `UnlockActionHint`
- `CriticalDependencyPath`

### Workstream C - Constraint surfaces

- show why a building is not ready
- show what one move unlocks multiple outcomes
- show where procedural, proof, budget, and execution blockers converge

## Acceptance Criteria

- SwissBuilding can represent cross-domain blockers and dependencies explicitly
- the product can explain leverage, not only status

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
- `npm run test:e2e`
- `npm run build`
