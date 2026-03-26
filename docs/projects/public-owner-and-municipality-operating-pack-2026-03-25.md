# Public Owner and Municipality Operating Pack

Date de controle: `25 mars 2026`

## Purpose

This pack translates the public-owner and municipality opportunity into an
execution frame that stays consistent with the wedge.

The goal is not to become a public-sector ERP.
The goal is to make SwissBuilding especially strong where communes and public
owners suffer from:

- long-lived building memory loss
- procedural discontinuity
- fragmented proof
- repeated external coordination

## Hard rule

Public-owner work should still reinforce the canonical building workspace.

If a feature only makes SwissBuilding look like a generic public administration
tool, it is off-wedge.

## Build posture

Build:

- public-owner workflow boundaries
- municipality-ready dossier continuity
- multi-asset governance hooks
- committee or review pack surfaces

Do not build:

- procurement suite
- generic council workflow software
- public finance ERP

## Minimum objects

### PublicOwnerOperatingMode

Represents a building or portfolio operating mode specific to public owners.

Minimum shape:

- `id`
- `org_id`
- `mode_code`
- `governance_requirements`
- `review_layers`

### MunicipalityReviewPack

Represents a bounded pack for municipal review or committee circulation.

Minimum shape:

- `id`
- `building_id`
- `pack_scope`
- `committee_target`
- `generated_at`
- `pack_version`

### PublicAssetGovernanceSignal

Represents a governance or continuity signal across public assets.

Minimum shape:

- `id`
- `portfolio_scope`
- `signal_type`
- `severity`
- `notes`

## Existing anchors to reuse

This pack should extend:

- canonical building workspace
- `PermitProcedure`
- `Authority Flow`
- packs and proof delivery
- territory and public-system context

It should not create:

- a second portfolio core
- a generic municipal software layer

## First useful outputs

The first valuable outputs are:

- municipality-ready review pack
- public-owner continuity mode
- cross-asset governance signal
- stronger committee or review circulation story

## Sequence

### PO1

Operating mode and review pack layer only.

### PO2

Governance signal layer.

### PO3

Later:

- public-owner multi-asset rollout patterns
- stronger territory and utility coordination

## Acceptance

This pack is useful when SwissBuilding becomes easier to justify and reuse
inside communes and public-owner organizations without losing its building
focus.
