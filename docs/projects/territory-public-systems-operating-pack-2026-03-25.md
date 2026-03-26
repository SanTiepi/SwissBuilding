# Territory and Public Systems Operating Pack

Date de controle: `25 mars 2026`

## Purpose

This is the execution-oriented companion to:

- [territory-public-systems-and-utility-coordination-program.md](./territory-public-systems-and-utility-coordination-program.md)

The goal is to make territory and public-system constraints operational without
breaking the building-centric model.

## Hard rule

Territory logic should enter the product only when it changes one of these:

- building readiness
- procedure path
- evidence requirements
- occupancy or works feasibility

If it does not change workflow quality, it stays reference context.

## Build posture

Build:

- dependency and impact objects
- blocker projection
- route and review hints

Do not build:

- a GIS platform
- a generic asset map product
- territory analytics detached from building decisions

## Minimum objects

### PublicSystemDependency

Represents an external dependency affecting a building.

Minimum shape:

- `id`
- `building_id`
- `dependency_type`
- `provider_code`
- `status`
- `impact_scope`
- `starts_at`
- `ends_at`

### UtilityInterruptionImpact

Represents a utility or infrastructure event that affects operations or works.

Minimum shape:

- `id`
- `building_id`
- `dependency_id`
- `interruption_type`
- `severity`
- `occupancy_impact`
- `works_impact`
- `mitigation_notes`

### TerritoryProcedureContext

Represents contextual territorial constraints tied to procedures.

Minimum shape:

- `id`
- `building_id`
- `context_type`
- `jurisdiction_code`
- `authority_code`
- `status`
- `review_required`

### DistrictConstraint

Represents district or block-level constraints.

Minimum shape:

- `id`
- `building_id`
- `constraint_type`
- `source_id`
- `severity`
- `notes`

## Existing anchors to reuse

Territory logic should feed:

- `permit_tracking`
- `PermitProcedure`
- `SwissRules`
- `ControlTower`
- `authority_pack`

It should not create:

- a second procedure stack
- a second blocker feed
- a standalone geospatial product

## First product outputs

The first useful outputs are:

- territory-based blocker
- utility interruption action
- district constraint review flag
- public-system dependency note in procedure context

## Sequence

### T1

Model dependencies and impacts only.

### T2

Project them into:

- blockers
- obligations
- procedure context

### T3

Later:

- richer map surfaces
- public-owner multi-asset logic
- utility or district event ingestion

## Acceptance

This layer is useful when an external territory or utility event changes what
the building team does next, not just what they can read.
