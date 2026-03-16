# Portfolio Intelligence Command Center Program

## Mission

Transform SwissBuildingOS from:

- a portfolio dashboard

into:

- a portfolio command center that can prioritize, simulate, cluster, and orchestrate intervention strategy across many buildings

## Why This Matters

Once dossiers, readiness, trust, campaigns, and packs exist, the next leap is not more reporting.
It is decision power:

- what to do first
- what can wait
- what should be grouped
- what destroys value if postponed
- where evidence effort unlocks the most progress

## Core Outcomes

### 1. Portfolio opportunity engine

Expected:

- identify highest-value next moves
- balance:
  - risk
  - trust
  - readiness
  - cost of delay
  - campaign leverage

### 2. CAPEX translation layer

Expected:

- turn readiness gaps and interventions into budget scenarios
- compare urgency vs cost vs confidence

### 3. Campaign orchestration cockpit

Expected:

- progress
- blockers
- grouped actions
- portfolio-wide impact

### 4. Executive decision surfaces

Expected:

- decision cards
- opportunity clusters
- quick wins
- critical blockers
- near-ready assets

## Recommended Workstreams

### Workstream A — Opportunity scoring

- rules and heuristics for next-best portfolio moves

### Workstream B — CAPEX / sequence simulation

- budget, sequence, and impact comparison

### Workstream C — Command-center UX

- strong portfolio surfaces
- not just charts: decisions, blockers, actionability

### Workstream D — Portfolio demo scenarios

- seeded scenarios that prove the concept in demos

## Acceptance Criteria

- portfolio becomes steerable, not just observable
- at least one decision surface clearly recommends action
- campaigns and simulations influence portfolio strategy

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
