# Ecosystem Network and Market Infrastructure Program

## Mission

Push SwissBuildingOS toward becoming:

- the coordination and exchange layer for the building ecosystem

not just an internal tool for one actor.

## Why This Matters

The strongest category outcome is not only better workflows.
It is when multiple actors begin to depend on the same building truth, evidence chain, and packs.

This is where the product starts behaving like infrastructure.

## Core Outcomes

### 1. Contributor ecosystem surfaces

Expected:

- bounded contributor workflows for:
  - diagnosticians
  - labs
  - contractors
  - authorities later where relevant

### 2. Structured handoff and exchange

Expected:

- partner-facing APIs or exchange hooks
- contributor pack interfaces
- inbound/outbound evidence discipline

### 3. Public-data delta and requalification monitoring

Expected:

- detect meaningful source changes
- notify or open signals/actions when the building truth changes

### 4. Cross-building and cross-actor learning loops

Expected:

- improve recommendation quality as the network grows
- do this without opaque behavior

## Recommended Workstreams

### Workstream A — Contributor exchange surfaces

- contributor uploads
- acknowledgment flows
- scoped evidence exchange

### Workstream B — Partner API/webhook foundations

- events
- webhooks
- import/export contracts

### Workstream C — Source delta monitoring

- meaningful change detection from registries and public layers

### Workstream D — Network learning foundations

- portfolio and cross-building pattern learning where explainable

## Acceptance Criteria

- the product is no longer only inward-facing
- contributor and partner exchange has a clear architecture
- public-data change can re-open or requalify building truth
- the first network-effect foundations exist

## Validation

Backend:

- `cd backend`
- `ruff check app/ tests/`
- `ruff format --check app/ tests/`
- `python -m pytest tests/ -q`

Frontend/admin if touched:

- `cd frontend`
- `npm run validate`
- `npm test`
- `npm run test:e2e`
- `npm run build`
