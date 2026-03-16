# Co-Ownership Governance and Resident Operations Program

## Mission

Prepare SwissBuildingOS for co-ownership, PPE/HOA-like governance, resident communication, and building-level collective decision workflows.

## Why This Matters

Many buildings are not governed by a single simple owner.
They involve:
- co-owners
- boards
- resident constraints
- collective decisions
- communication and acknowledgement needs

This is a major missing layer for becoming the operating system of real-world building ownership.

## Strategic Outcomes

- stronger fit for multi-owner buildings
- more credible resident-facing coordination
- a path to collective building governance workflows

## Product Scope

This program should produce:
- co-ownership structures
- decision / approval scaffolding
- resident operations linkage
- bounded communication and acknowledgement

## Recommended Workstreams

### Workstream A - Co-ownership structure model

Candidate objects:
- `OwnershipGroup`
- `OwnershipShare`
- `BoardRole`

### Workstream B - Collective decision workflow

Candidate objects:
- `GovernanceDecision`
- `VoteRecord`
- `ResolutionPack`

### Workstream C - Resident operations

Candidate objects:
- `ResidentNotice`
- `AcknowledgementRecord`
- `RestrictionWindow`

## Acceptance Criteria

- SwissBuilding gains a path for collective building governance
- resident-facing and board-facing flows become more credible

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
