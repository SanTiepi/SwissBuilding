# Cross-Modal Change Detection and Reconstruction Program

## Mission

Detect and reconstruct building change by comparing evidence across time and modality:
- plans
- reports
- photos
- interventions
- post-works records
- field observations

The goal is to understand what likely changed, what is still uncertain, and what must be requalified.

## Why This Matters

This became newly practical as models improved at:
- comparing heterogeneous evidence
- extracting structured visual and textual deltas
- reasoning with uncertainty across multiple modalities

That enables SwissBuilding to do something unusual:
- rebuild the before/after state of a building even when the evidence is messy

## Strategic Outcomes

- stronger post-works truth
- better change signals
- better contradiction detection
- more reliable building memory over long time horizons

## Product Scope

This program should produce:
- cross-modal diff logic
- reconstruction hypotheses with confidence
- requalification triggers tied to change evidence

It should not become:
- a fake certainty engine
- an ungrounded visual guesser without provenance

## Recommended Workstreams

### Workstream A - Change hypothesis model

Candidate objects:
- `ChangeHypothesis`
- `ReconstructionHypothesis`
- `ChangeEvidenceSet`

### Workstream B - Cross-modal diff engine

Expected capabilities:
- compare plan vs photo
- compare report version vs report version
- compare pre-works vs post-works evidence
- surface likely change zones and unknown residuals

Candidate objects:
- `CrossModalDiff`
- `DeltaConfidence`

### Workstream C - Requalification triggers

Candidate objects:
- `RequalificationTrigger`
- `ChangeConfidenceBand`

## Acceptance Criteria

- SwissBuilding can express likely building change across mixed evidence
- change detection remains provenance-backed and uncertainty-aware
- post-works and contradiction layers gain much stronger foundations

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
