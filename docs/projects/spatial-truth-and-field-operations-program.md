# Spatial Truth and Field Operations Program

## Mission

Turn SwissBuildingOS from:

- a dossier-centered building platform

into:

- a spatially navigable operational system where plans, zones, field evidence, and on-site work all reinforce the same building truth

## Why Now

The repo already has:

- zones
- elements
- materials
- plans
- interventions
- evidence links

What is still missing is the operational layer that makes the building usable as a physical object in the field.

## Core Outcomes

### 1. Plan Annotation becomes first-class

Expected:

- annotate plans with zones, elements, materials, and evidence
- allow evidence and observations to live directly on a plan context
- make plan navigation useful, not just visual

### 2. Field Capture becomes real

Expected:

- lightweight mobile-friendly capture
- photo, note, voice, checklist, zone attachment
- sync to dossier without requiring a native mobile app first

### 3. Proof Heatmap on Plans

Expected:

- show where proof is strong
- show where proof is weak
- show where unknowns or contradictions exist

### 4. Sampling Planner foundations

Expected:

- suggest where more sampling is needed based on unknowns and contradictions
- connect plan, zone, material, and evidence

### 5. Contractor acknowledgment / field execution hooks

Expected:

- execution-side acknowledgment of risks or reservations
- support future contractor packs and tender readiness

## Recommended Workstreams

### Workstream A — Plan annotation primitives

- spatial annotations tied to zones/elements/materials/evidence
- backend model or metadata approach, whichever best fits current architecture

### Workstream B — Field observation objects

- field observations / captures
- zone / plan binding
- attachment support where low-regret

### Workstream C — Explorer and plans UI uplift

- plan-native navigation
- proof / unknown / contradiction overlays where feasible

### Workstream D — Sampling planner foundations

- identify under-proven zones/materials
- suggest next best evidence actions

## Acceptance Criteria

- plans are no longer passive files only
- field observations become first-class building truth
- at least one spatial overlay is operational
- the system becomes more useful on and around the building, not only in the dossier

## Validation

Backend:

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
