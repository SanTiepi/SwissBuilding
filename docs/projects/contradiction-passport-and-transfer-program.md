# Contradiction, Passport, and Transfer Program

## Mission

Build the next deep moat layer:

- contradiction detection
- durable building passport logic
- structured transfer of building truth between actors and systems

## Why Now

SwissBuildingOS already has:

- evidence links
- building structure
- dossiers
- interventions
- trust/readiness/data quality foundations emerging

The next major differentiator is not just knowing more, but knowing:

- where the truth conflicts
- how stable the passport is
- how to transfer building memory without loss

## Core Outcomes

### 1. Contradiction Engine foundations

Expected:

- detect conflicts between:
  - samples and reports
  - manual data and imports
  - interventions and current state
  - plan assumptions and field observations

### 2. Building Passport state becomes explicit

Expected:

- passport-level summary of:
  - proven
  - inferred
  - stale
  - contradictory
  - unknown

### 3. Building Memory Transfer

Expected:

- package the building truth for transfer between:
  - managers
  - owners
  - contractors
  - future partner systems

### 4. Passport export foundations

Expected:

- reusable export structure
- versioned package logic
- future compatibility with a building passport standard

## Recommended Workstreams

### Workstream A — Contradiction detection service

- contradiction rules
- conflict objects or conflict generation on top of existing quality issues
- severity and review workflow

### Workstream B — Passport summary service

- state aggregation across evidence, trust, readiness, unknowns, post-works state

### Workstream C — Transfer/export package

- package a building for transfer
- preserve provenance and history
- low-regret architecture for future standardization

### Workstream D — UI visibility

- contradiction surfaces
- passport summary card or section
- transfer/export action if ready

## Acceptance Criteria

- contradictions are visible, not hidden in silence
- a building passport summary exists as a coherent state
- transfer/export of building truth has an explicit architecture
- the product gets closer to infrastructure and standard status

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
