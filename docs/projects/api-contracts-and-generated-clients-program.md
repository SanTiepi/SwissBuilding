# API Contracts and Generated Clients Program

## Mission

Strengthen contract integrity between backend and frontend by making API shapes, types, and client behavior more systematic and less drift-prone.

## Why This Matters

The product is now large enough that contract drift becomes expensive:

- backend grows quickly
- frontend grows quickly
- new domains appear frequently
- manual type and client upkeep can silently lag behind reality

This is especially risky for:

- readiness/trust/unknowns surfaces
- packs and dossier flows
- portfolio aggregates
- future partner APIs and exchange formats

## Core Outcomes

### 1. Contract drift risk goes down

Expected:

- clearer source of truth for API shapes
- stronger alignment between schemas and frontend types
- fewer silent mismatches across waves

### 2. New domains become cheaper to expose

Expected:

- cleaner client generation or synchronization path
- reduced manual retyping
- better consistency of:
  - enums
  - paginated responses
  - summary shapes
  - nested resource contracts

### 3. Partner and external surfaces get safer foundations

Expected:

- better readiness for:
  - exchange APIs
  - embedded widgets
  - bounded viewers
  - passport/export contracts

## Recommended Workstreams

### Workstream A — Contract inventory

- inventory current backend schema -> frontend type duplication
- identify high-drift zones
- identify which contracts should stay hand-shaped vs generated

### Workstream B — Generation strategy

- define a practical strategy for:
  - OpenAPI-driven client generation
  - shared schema extraction
  - enum synchronization
- keep the solution lightweight and repo-native

### Workstream C — High-value migration

- migrate the highest-risk/highest-change surfaces first
- likely targets:
  - readiness / trust / unknowns
  - passport / snapshots / time machine
  - packs / exports
  - search / portfolio summaries

### Workstream D — Guardrails

- add validation or review steps that make contract drift visible
- document what remains intentionally manual

## Acceptance Criteria

- fewer duplicated or drift-prone contract definitions
- a clear repo-native strategy exists for generated vs hand-maintained clients
- high-change domains become less error-prone to expose in frontend
- future exchange/API work has stronger foundations

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
- `user_surface`: `internal / partner`
- `go_to_market_relevance`: `supporting`
- `moat_type`: `contract_integrity`
- `depends_on`: `current schema + api client surface`
