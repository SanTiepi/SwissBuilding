# Warranty, Defects, and Service Obligations Program

## Mission

Extend SwissBuildingOS into the post-delivery and operational obligations layer: warranties, defects, service obligations, and recurring compliance or maintenance duties.

## Why This Matters

After works, the story is not finished.
Buildings continue to generate:
- defects
- warranty claims
- service obligations
- maintenance windows
- compliance renewals

This layer makes SwissBuilding useful after the initial dossier and intervention cycle.

## Strategic Outcomes

- stronger post-works lifecycle value
- better linkage between interventions and downstream obligations
- more durable operating memory

## Product Scope

This program should produce:
- warranty and defect tracking
- service obligation records
- renewal / expiry awareness
- linkage to packs, plans, systems, and interventions

## Recommended Workstreams

### Workstream A - Warranty model

Candidate objects:
- `WarrantyRecord`
- `WarrantyCoverage`
- `WarrantyExpirySignal`

### Workstream B - Defect lifecycle

Candidate objects:
- `DefectRecord`
- `DefectSeverity`
- `DefectResolutionStep`

### Workstream C - Service and renewal obligations

Candidate objects:
- `ServiceObligation`
- `MaintenanceWindow`
- `RenewalSignal`

## Acceptance Criteria

- SwissBuilding gains a path into post-delivery value
- warranties, defects, and recurring obligations become linkable to building truth

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
