# Agent Governance and Knowledge Workbench Program

## Mission

Build the internal force-multiplier layer that keeps SwissBuildingOS agentic, explainable, and improvable:

- agent auditability
- knowledge capture
- dataset curation
- terminology and extraction correction workflows

## Why This Matters

If the product is going to rely more and more on invisible agents, extraction pipelines, and recommendation engines, then internal governance becomes part of the moat.

The system should not only automate. It should:

- audit automation
- improve automation
- curate building truth

## Core Outcomes

### 1. Agent Audit Console

Expected:

- who/what proposed which recommendation
- on which evidence
- with what confidence
- accepted or overridden by whom

### 2. Knowledge Capture Workbench

Expected:

- fix OCR/extraction issues
- normalize terminology
- curate evidence links
- improve training and rules quality

### 3. Dataset Curation Bench

Expected:

- collect edge cases
- contradictions
- post-works cases
- transfer-ready scenarios

## Recommended Workstreams

### Workstream A — Agent run audit model

- persist agent runs, outputs, confidence, validations

### Workstream B — Knowledge correction surfaces

- correction UI or admin workflow
- structured re-labeling where useful

### Workstream C — Curation and replay

- reusable test/demo/training scenarios from corrected cases

## Acceptance Criteria

- agent outputs become inspectable and governable
- extraction/rules corrections are not lost in ad hoc edits
- internal learning loops become a product advantage

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
