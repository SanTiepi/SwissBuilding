# Execution Quality and Hazardous Works Operations Program

## Mission

Extend SwissBuildingOS from readiness and proof into the quality control of hazardous work execution itself, so the system does not stop at "ready to start" but continues through checkpoints, acceptance, and closeout.

## Why This Matters

The product is becoming strong at:
- pre-work dossier readiness
- intervention planning
- post-works truth foundations

But a major operational gap remains:
- how hazardous works are actually executed
- what control points were passed
- what evidence was captured on site
- what was accepted, rejected, reopened, or escalated
- how disposal and remediation evidence ties back into truth

This is where the product becomes much harder to replace in real projects.

## Strategic Outcomes

- execution-side quality becomes explicit
- hazardous works become traceable beyond the planning phase
- post-works truth gains stronger operational evidence
- authority, contractor, and owner packs can eventually include richer execution proof

## Product Scope

This program should produce:
- work method and checkpoint concepts
- execution evidence records
- acceptance and reopen semantics
- disposal-chain linkage where relevant

It should not become:
- a generic construction management suite
- a field-only app detached from dossier truth

## Recommended Workstreams

### Workstream A - Work methods and control points

Model the operational plan of hazardous work at a useful level.

Expected capabilities:
- method statement / work method notion
- required checkpoints by intervention type
- sequencing of critical controls
- linkage to packs, rules, and zones

Candidate objects:
- `MethodStatement`
- `ExecutionCheckpoint`
- `CheckpointTemplate`

### Workstream B - Worksite quality evidence

Capture execution evidence as structured truth.

Examples:
- photos
- measurements
- air tests
- clearance results
- containment checks
- approvals
- exceptions and deviations

Candidate objects:
- `WorkQualityRecord`
- `ExecutionEvidence`
- `DeviationRecord`

### Workstream C - Interim and final acceptance

Make acceptance states explicit.

Expected capabilities:
- partial acceptance
- final acceptance
- rejection / reopen
- residual issue tracking
- link to post-works state

Candidate objects:
- `AcceptanceStep`
- `AcceptanceDecision`
- `ReopenTrigger`

### Workstream D - Waste and disposal chain linkage

Link hazardous waste handling into execution truth.

Expected outputs:
- disposal proof references
- chain linkage from intervention to removal/disposal records
- support for later legal-grade and insurer-facing packs

Candidate objects:
- `DisposalChainRecord`
- `WasteTransferRecord`
- `DisposalProofLink`

### Workstream E - Execution quality surfaces

Expose work-quality truth in a way that helps operators:
- intervention detail
- checkpoint progression
- blocked / reopened states
- missing execution evidence
- ready-for-closeout visibility

## Candidate Improvements

- `ExecutionCheckpoint`
- `CheckpointTemplate`
- `MethodStatement`
- `WorkQualityRecord`
- `ExecutionEvidence`
- `DeviationRecord`
- `AcceptanceStep`
- `AcceptanceDecision`
- `ReopenTrigger`
- `DisposalChainRecord`
- `WasteTransferRecord`
- `DisposalProofLink`

## Acceptance Criteria

- the product can reason about execution quality, not only pre-work readiness
- post-works truth can be supported by richer execution evidence
- hazardous works have clearer checkpoints, acceptance, and reopen logic
- disposal and removal chains have a defined path into dossier truth

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
