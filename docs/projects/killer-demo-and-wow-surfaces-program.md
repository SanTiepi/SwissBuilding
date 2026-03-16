# Killer Demo and Wow Surfaces Program

## Mission

Build a set of visibly impressive product capabilities that make SwissBuildingOS feel category-defining in demos, without turning the product into vaporware.

These features must be:

- demonstrable
- evidence-backed
- tied to real domain objects
- reusable by the rest of the platform

They are not gimmicks. They are high-impact surfaces built on top of the core proof, memory, readiness, and portfolio layers.

## Why This Program Exists

SwissBuildingOS already has strong foundations:

- physical building model
- evidence chain
- dossiers
- regulatory packs
- campaigns
- search
- trust/readiness/data quality foundations

The next step is to create a few **killer surfaces** that make the product feel unmistakably ahead of the market.

## Core Wow Features

### 1. Building Time Machine

Purpose:

- let users replay the building at a chosen point in time

Core experience:

- what was known then
- what was proven then
- what was missing then
- what changed since

Why it matters:

- audit
- claims / disputes
- requalification
- “post-works truth” visibility
- huge demo impact

### 2. Proof Heatmap on Plans

Purpose:

- show proof density, uncertainty, and contradictions directly on plans

Core experience:

- strong proof zones
- weak proof zones
- unknown areas
- contradiction hotspots

Why it matters:

- spatially explains the dossier
- turns plans into an intelligence surface

### 3. Intervention Simulator

Purpose:

- simulate what a planned intervention changes in the building truth

Core experience:

- which zones become impacted
- which evidence becomes stale
- what must be resampled / re-diagnosed
- which packs become invalid
- what new actions are triggered

Why it matters:

- converts the product from descriptive to predictive

### 4. Readiness Wallet

Purpose:

- show all building readiness states together as a decision cockpit

Core states:

- `safe_to_start`
- `safe_to_tender`
- `safe_to_renovate`
- `safe_to_sell`
- `safe_to_insure`
- `safe_to_finance`

Why it matters:

- one of the clearest “this is more than a dossier” moments

### 5. Autonomous Dossier Completion Agent

Purpose:

- visibly demonstrate invisible agency without turning the app into a generic chatbot

Core experience:

- detect missing items
- identify likely contributor
- generate missing-items list
- propose next follow-up steps
- rebuild dossier completeness after updates

Why it matters:

- strong wow factor
- strong commercial story
- still grounded in evidence and workflow

## Recommended Workstreams

### Workstream A — Time machine foundations

- timeline snapshots or diffable historical states
- compare then vs now
- focus on explainability over perfect temporal replay if necessary

### Workstream B — Spatial proof visualization

- use plans, zones, elements, and evidence density
- produce a clear overlay

### Workstream C — Intervention simulation layer

- simulation service
- impact summary
- action / readiness consequences

### Workstream D — Readiness wallet UI

- aggregate readiness states
- make blockers and strengths understandable

### Workstream E — Dossier completion agent

- no generic chat UI required
- task-focused agent behavior only
- generate concrete follow-ups and completion suggestions

## Product Rules

- do not ship these as decorative toys
- each wow surface must deepen:
  - proof
  - memory
  - readiness
  - orchestration
- if a wow feature cannot be grounded in current data/model truth, keep it behind the frontier, not in visible UI

## Acceptance Criteria

- at least one time-based surface exists
- at least one spatial proof surface exists
- at least one predictive intervention surface exists
- readiness is visible as a wallet/cockpit, not just isolated badges
- the dossier completion agent is evidence-driven and workflow-specific

## Validation

Backend if touched:

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

Real integration if touched:

- `cd frontend`
- `npm run test:e2e:real`
