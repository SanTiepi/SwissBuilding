# Trust, Readiness, and Post-Works Program

## Mission

Turn SwissBuildingOS from:

- a dossier and risk platform

into:

- a system that explicitly knows what is trusted, what is missing, what is ready, and what is still true after works

This program should stay backend-first when needed, but it must land enough product surfaces to make the new primitives operational.

## Why Now

The repo already has foundations for:

- `SavedSimulation`
- `DataQualityIssue`
- `ChangeSignal`
- `ReadinessAssessment`
- `BuildingTrustScore`
- `UnknownIssue`
- `PostWorksState`

The next step is to stop treating them as isolated objects and make them work together as a coherent trust/readiness layer.

## Core Outcomes

### 1. BuildingTrustScore becomes real

Expected:

- score computed from evidence strength, completeness, contradictions, stale data, and missing critical artefacts
- clear separation from raw risk score
- building detail and list surfaces can show trust separately from risk

### 2. UnknownIssue becomes generated, not just stored

Expected:

- unknowns generated from:
  - missing plans
  - missing diagnostics
  - uninspected zones
  - unconfirmed materials
  - undocumented interventions
- unknowns grouped by severity and scope

### 3. ReadinessAssessment becomes the operational gate layer

Expected readiness types:

- `safe_to_start`
- `safe_to_tender`
- `safe_to_reopen`
- `safe_to_requalify`
- `safe_to_document`

Each readiness output must include:

- status
- score if applicable
- blockers
- conditions
- legal/workflow basis where available

### 4. PostWorksState becomes real before/after truth

Expected:

- represent:
  - removed
  - remaining
  - encapsulated
  - treated
  - unknown_after_intervention
  - recheck_needed
- connect to interventions, materials, evidence, and readiness
- allow before/after comparison

### 5. ChangeSignal becomes action-driving

Expected:

- first generators from:
  - imports
  - documents
  - interventions
  - trust/readiness changes
- clear connection to follow-up actions where appropriate

## Recommended Workstreams

### Workstream A — Trust computation service

- scoring logic
- API if not already sufficient
- unit tests

### Workstream B — Unknown generation service

- unknown extraction from dossier gaps
- severity logic
- grouping by building / zone / category

### Workstream C — Readiness UI

- building detail surfaces
- clear blockers / conditions
- not a generic KPI card; a real operational gate

### Workstream D — Post-Works truth service

- post-intervention state update
- before/after diff
- bridge to dossier and evidence

### Workstream E — Data quality dashboard

- combine:
  - `DataQualityIssue`
  - `ChangeSignal`
  - `UnknownIssue`
  - `BuildingTrustScore`

## Acceptance Criteria

- trust score is visibly distinct from risk score
- unknowns are auto-generated from real gaps
- at least one readiness state is operationally useful, not decorative
- post-works states are persisted and comparable
- building detail can show trust/readiness/unknowns without looking overloaded

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
