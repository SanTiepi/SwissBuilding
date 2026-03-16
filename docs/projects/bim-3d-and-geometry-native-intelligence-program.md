# BIM, 3D, and Geometry-Native Intelligence Program

## Mission

Push SwissBuildingOS from document-linked geometry toward geometry-native building intelligence, where plans, sections, models, issues, proof, and interventions can all be navigated spatially.

## Why This Matters

SwissBuilding now has:
- plans
- zones
- elements
- materials
- interventions
- proof links

The next leap is to make geometry operational:
- 2D and 3D spatial context
- plan-linked and model-linked issues
- spatial contradictions and unknowns
- geometry-aware post-works truth
- future openBIM interoperability grounded in product value

Without this layer, geometry stays an attachment surface instead of becoming part of the intelligence model.

## Strategic Outcomes

- geometry becomes a working intelligence layer
- proof, unknowns, and contradictions can be spatialized
- plan and model surfaces become future-ready without requiring full BIM authoring
- SwissBuilding gains a credible bridge into BIM-heavy enterprise contexts

## Product Scope

This program should produce:
- geometry anchors and spatial references
- geometry-aware issue/proof semantics
- a credible IFC / 3D path
- plan-vs-reality comparison foundations

It should not try to become:
- a full BIM authoring system
- a CAD replacement
- an all-purpose model viewer disconnected from dossier truth

## Recommended Workstreams

### Workstream A - Geometry anchor model

Create a stable way to attach product truth to geometry.

Expected capabilities:
- anchor zones, elements, materials, issues, evidence, and observations to:
  - 2D plan coordinates
  - 3D references later
- support versioned geometry references

Candidate objects:
- `GeometryAnchor`
- `GeometryReferenceFrame`

### Workstream B - Spatial issues and proof

Make geometry actionable.

Expected capabilities:
- bind contradictions, unknowns, hazards, and interventions to geometry
- navigate from a spatial point to:
  - evidence
  - materials
  - interventions
  - readiness gaps

Candidate objects:
- `SpatialIssue`
- `SpatialProofLink`

### Workstream C - Model snapshots and BIM references

Prepare the path from plans to models.

Expected direction:
- model snapshot registry
- IFC reference support
- selective import/export
- BCF-like issue bridging later

Candidate objects:
- `ModelSnapshot`
- `IfcGeometryReference`
- `BcfIssueReference`

### Workstream D - Plan versus reality comparison

Support comparison between:
- expected plan state
- observed field state
- post-works truth

Expected outputs:
- visual diff direction
- expected-vs-observed semantics
- before/after comparison foundations

Candidate objects:
- `PlanRealityDiff`
- `ExpectedStateAnchor`
- `ObservedStateAnchor`

### Workstream E - Geometry-native UX surfaces

Turn geometry into an actual working surface, not just a storage layer.

Examples:
- proof heatmap on plans
- unknowns on plan
- intervention scope overlay
- readiness / restriction overlays

## Candidate Improvements

- `GeometryAnchor`
- `GeometryReferenceFrame`
- `SpatialIssue`
- `SpatialProofLink`
- `ModelSnapshot`
- `IfcGeometryReference`
- `BcfIssueReference`
- `PlanRealityDiff`
- `ExpectedStateAnchor`
- `ObservedStateAnchor`

## Acceptance Criteria

- geometry is treated as a first-class product layer
- proof and issue models can meaningfully attach to geometry
- there is a credible path from 2D plans to 3D/BIM-aware workflows
- post-works truth and contradiction workflows are easier to spatialize later

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
