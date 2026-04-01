# Geometry Intelligence Operating Pack

Date de controle: `25 mars 2026`

## Purpose

This is the execution-oriented companion to:

- [bim-3d-and-geometry-native-intelligence-program.md](./bim-3d-and-geometry-native-intelligence-program.md)
- [spatial-truth-and-field-operations-program.md](./spatial-truth-and-field-operations-program.md)

The goal is to keep geometry useful and product-native without drifting into
CAD or BIM authoring.

## Hard rule

Geometry must improve workflow truth.

If a geometry feature does not improve at least one of these, it is probably
too early:

- proof readability
- blocker readability
- field understanding
- intervention scope clarity

## Build posture

Build narrow:

- anchors
- overlays
- issue and proof semantics

Integrate broad:

- IFC processing
- heavy model handling
- advanced viewers

Do not build:

- BIM authoring
- CAD editing
- model-centric product identity

## Minimum objects

### GeometryReferenceFrame

Defines the coordinate context for a plan or model snapshot.

Minimum shape:

- `id`
- `building_id`
- `plan_id` or `model_snapshot_id`
- `frame_type`
- `version_label`
- `is_current`

### GeometryAnchor

The canonical link from product truth to a spatial location.

Minimum shape:

- `id`
- `building_id`
- `reference_frame_id`
- `anchor_type`
- `zone_id`
- `element_id`
- `material_id`
- `x`
- `y`
- `z`
- `notes`

### SpatialProofLink

Links evidence or proof to geometry.

Minimum shape:

- `id`
- `anchor_id`
- `document_id` or `evidence_id`
- `proof_kind`
- `confidence`

### SpatialIssue

Represents an unknown, contradiction, or hazard anchored in geometry.

Minimum shape:

- `id`
- `anchor_id`
- `issue_type`
- `severity`
- `status`
- `related_obligation_id`
- `related_action_code`

## Existing anchors to reuse

Geometry intelligence should extend:

- zones
- elements
- plans
- field observations
- evidence links
- `ControlTower`

It should not create:

- a second building graph
- a second issue tracker detached from the building file

## First product outputs

The first valuable surfaces are:

- proof heatmap on plan
- unknowns or contradictions on plan
- intervention scope overlay
- plan-linked field observations

These should make the building easier to understand, not just prettier.

## Sequence

### G1

Anchor layer only:

- `GeometryReferenceFrame`
- `GeometryAnchor`
- `SpatialProofLink`

### G2

Issue layer:

- `SpatialIssue`
- relation to blockers or actions

### G3

UI layer:

- one useful overlay surface in plan explorer

### G4

Later:

- IFC references
- BCF-like bridges
- 3D model snapshots

## Acceptance

Geometry intelligence is succeeding when a user can understand a risky or
under-proven area faster on a plan than in a document list.
