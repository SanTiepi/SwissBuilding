# Occupant Safety and Communication Program

## Mission

Extend SwissBuildingOS from renovation-readiness and proof into a stronger occupant-facing safety layer.

This program should help the product answer:

- are occupants currently exposed to unresolved building risk or documentation gaps?
- what must be communicated before, during, and after interventions?
- what evidence and reservations should be visible to residents, tenants, or on-site non-expert actors?

## Why This Matters

SwissBuildingOS is strong on:
- pre-work proof
- intervention preparation
- post-work truth

But one major adjacent use is still underdeveloped:
- occupant safety communication
- limited, bounded sharing of what people need to know
- traceable notice and acknowledgement in sensitive contexts

This matters for:
- owners
- managers
- public building operators
- schools / institutional buildings later
- high-trust market positioning

## Core Outcomes

### 1. Occupancy safety becomes explicit

Expected:
- surface whether a building or zone has unresolved occupant-facing safety/documentation gaps
- distinguish operational readiness from occupant safety readiness

### 2. Communication becomes productized

Expected:
- bounded communication packs or notices
- audience-appropriate wording
- acknowledgement workflows where appropriate

### 3. Evidence and communication stay linked

Expected:
- occupant-facing communication is still backed by dossier truth
- warnings, restrictions, and notices are not detached from proof

## Recommended Workstreams

### Workstream A — Occupancy safety state

- introduce or derive an `OccupancySafetyReadiness` state
- building- and zone-level where appropriate
- link it to unknowns, contradictions, post-works truth, and active interventions

### Workstream B — Bounded occupant notices

- communication templates for:
  - access restrictions
  - pending verification
  - intervention impacts
  - post-works residual precautions
- keep them productized, not ad hoc PDFs

### Workstream C — Acknowledgement and delivery tracking

- when useful, support:
  - issued
  - delivered
  - acknowledged
  - expired / superseded

### Workstream D — Occupant-safe pack logic

- generate a lighter-weight, bounded pack for residents/occupants/non-expert actors
- do not leak full sensitive dossier content

## Candidate Improvements

- `OccupancySafetyReadiness`
- `OccupantNotice`
- `NoticeDelivery`
- `ZoneRestriction`
- `OccupantPack`

## Acceptance Criteria

- occupancy-facing risk/readiness becomes clearer
- the product can issue bounded occupant-safe communication artifacts
- communication stays linked to proof and intervention state
- this creates a stronger trust and operations story without bloating the product

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

## Notes

This is not a tenant portal program.
It is a bounded occupant-safety and communication layer.

Prefer:
- clear limited communication surfaces
- evidence-linked notices
- zone-aware safety states

Avoid:
- generic messaging systems
- broad public-facing exposure
