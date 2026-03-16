# Building Passport Standard and Exchange Program

## Mission

Push SwissBuildingOS beyond internal dossiers and exports toward:

- a true building passport
- a portable exchange format
- a reusable market artefact that can move between actors and systems

This is one of the strongest long-term moat candidates in the entire product.

## Why This Matters

If SwissBuilding only generates PDFs and app-local records, it remains a powerful application.

If SwissBuilding defines how building truth, readiness, proof, and memory move between:

- owners
- managers
- contractors
- diagnosticians
- authorities
- lenders
- insurers
- partner systems

then it starts to become market infrastructure.

## Core Outcomes

### 1. Passport object structure

Expected:

- canonical structure for:
  - identity
  - structure
  - materials
  - evidence
  - readiness
  - interventions
  - post-works state
  - trust / unknowns / contradictions

### 2. Exportable passport package

Expected:

- versioned export package
- machine-readable plus human-readable layers
- durable provenance preserved

### 3. Exchange and transfer contract

Expected:

- package suitable for transfer between actors and systems
- importer/exporter discipline
- future-compatible with partner ecosystem work

### 4. Diffable passport states

Expected:

- compare one passport version to another
- show what changed and why

## Recommended Workstreams

### Workstream A — Passport schema and packaging

- define canonical object structure
- serialization strategy
- version strategy

### Workstream B — Export and import contract

- package creation
- validation
- import safety and provenance retention

### Workstream C — Passport diff layer

- compare versions
- expose structural and evidentiary changes

### Workstream D — UI and operator visibility

- passport summary
- transfer/export actions
- diff review where useful

## Acceptance Criteria

- the building passport is more than a PDF
- a structured exchange package exists
- provenance survives export/import
- state diffs are understandable

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
