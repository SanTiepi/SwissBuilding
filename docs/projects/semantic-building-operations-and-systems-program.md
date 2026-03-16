# Semantic Building Operations and Systems Program

## Mission

Extend SwissBuildingOS from structural/proof intelligence into semantic understanding of building systems and operations, so the product can evolve beyond renovation dossiers toward a richer building operations layer.

This program should prepare the platform to model:

- equipment and technical systems
- operational building subsystems
- semantic metadata for systems and points
- future smart-readiness and operational-state use cases

## Why This Matters

Right now SwissBuilding is strongest on:
- building evidence
- pollutants
- readiness
- interventions
- packs and proof

To become a broader building intelligence layer, it will eventually need a stronger semantic model for:
- HVAC and ventilation systems
- electrical systems
- fire safety systems
- water systems
- sensor and telemetry context
- technical rooms and system dependencies

Recent ecosystem direction suggests that machine-readable semantic building-system layers are becoming more important, not less.

## Core Outcomes

### 1. Technical systems stop being opaque attachments

Expected:
- building systems can be modeled as first-class semantic objects
- plans, zones, interventions, and evidence can connect to systems and equipment

### 2. Future smart-readiness use cases become possible

Expected:
- a path toward smart-readiness / operational building intelligence
- richer post-works truth for system changes
- stronger maintenance and safety expansion later

### 3. SwissBuilding gains a bridge to building-operations ecosystems

Expected:
- alignment path toward semantic building metadata standards
- less risk that the product remains renovation-only forever

## Recommended Workstreams

### Workstream A — System and equipment ontology

- define future object shapes for:
  - systems
  - equipment
  - points/signals later
- keep them distinct from current building elements/materials

### Workstream B — Zone / plan / system linkage

- define how technical rooms, ducts, pipes, systems, and plans relate
- allow future traversal from building passport to operating systems

### Workstream C — Semantic mapping strategy

- prepare mapping strategy toward building operations semantic models such as:
  - Brick
  - Haystack
- do not overbuild integrations now; define the product shape and leverage points

### Workstream D — Smart-readiness and operations expansion hooks

- identify low-regret primitives that would later support:
  - technical inspections
  - system replacement
  - ventilation evidence
  - indoor environmental quality logic
  - maintenance and operations packs

## Candidate Improvements

- `BuildingSystem`
- `TechnicalEquipment`
- `SystemRelationship`
- `SystemReadiness`
- `SystemChangeRecord`
- `SemanticMappingProfile`

## Reference Signals

Recent high-signal references for this direction:
- Brick ontology for building systems semantics
- Project Haystack / Haystack 5 for semantic building metadata

These should inspire the model shape and interoperability posture, not force premature implementation.

## Acceptance Criteria

- SwissBuilding has a credible future systems/operations model path
- building structure and future systems semantics are no longer conflated
- roadmap and frontier docs reflect that the product can expand from renovation evidence into semantic building operations

## Validation

If docs only:
- consistency across:
  - `docs/architecture.md`
  - `docs/roadmap-next-batches.md`
  - `docs/product-frontier-map.md`
  - `docs/vision-100x-master-brief.md`

If code is touched:

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

## Notes

Prefer:
- strong semantic foundations
- clean distinction between structure/material truth and operating-system truth

Avoid:
- pretending SwissBuilding is already a full BMS/CMMS platform
- rushing telemetry before semantics
