# Permit Procedure and Public Funding Program

## Mission

Extend SwissBuildingOS from readiness and proof into the orchestration of permit procedures, authority submissions, and public-funding / subsidy readiness.

## Why This Matters

A building can be technically ready and still be blocked by:
- permit sequencing
- missing authority artifacts
- subsidy prerequisites
- late procedural dependencies

This program closes the gap between "ready in substance" and "ready in procedure".

## Strategic Outcomes

- stronger authority-facing orchestration
- better linkage between proof packs and procedural steps
- credible support for renovation subsidies and public funding paths

## Product Scope

This program should produce:
- permit-step tracking
- authority submission checkpoints
- subsidy / grant readiness scaffolding
- procedural blockers tied to building truth

## Recommended Workstreams

### Workstream A - Permit workflow model

- represent procedural steps
- required artifacts
- deadlines
- decision states

Candidate objects:
- `PermitProcedure`
- `PermitStep`
- `AuthoritySubmission`

### Workstream B - Subsidy and grant readiness

- capture eligibility evidence
- missing subsidy prerequisites
- grant pack preparation

Candidate objects:
- `FundingProgram`
- `FundingEligibilityCheck`
- `FundingPack`

### Workstream C - Procedural blocker surfaces

- show what blocks the procedure
- connect blockers to packs, documents, and readiness states

## Acceptance Criteria

- SwissBuilding can model procedural readiness, not only technical readiness
- authority and subsidy workflows gain a native path

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
