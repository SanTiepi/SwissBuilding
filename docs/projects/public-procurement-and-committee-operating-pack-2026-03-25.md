# Public Procurement and Committee Operating Pack

Date de controle: `25 mars 2026`

## Purpose

This pack complements the public-owner path with a focused execution layer for:

- committee circulation
- review readiness
- procurement-facing pack structure
- reusable decision artifacts

It does not try to become a full procurement suite.

## Hard rule

Public procurement or committee features must reinforce:

- dossier clarity
- review traceability
- reusable decision artifacts

If they drift into generic procurement administration, they leave the wedge.

## Build posture

Build:

- committee-ready packs
- procurement clause bundles
- decision traceability
- reusable review artifacts

Do not build:

- full tender management suite
- generic procurement ERP
- broad vendor administration unrelated to building truth

## Minimum objects

### CommitteeDecisionPack

Represents a pack prepared for committee or review circulation.

Minimum shape:

- `id`
- `building_id`
- `pack_version`
- `decision_scope`
- `committee_target`
- `summary_sections`

### ProcurementClauseBundle

Represents reusable clause language tied to building or intervention truth.

Minimum shape:

- `id`
- `building_id`
- `bundle_scope`
- `intervention_type`
- `clause_refs`
- `generated_at`

### ReviewDecisionTrace

Represents a trace of committee or procurement-oriented review decisions.

Minimum shape:

- `id`
- `pack_id`
- `review_status`
- `decision_summary`
- `decided_at`
- `notes`

## Existing anchors to reuse

This pack should extend:

- public owner operating mode
- municipality review packs
- ecobau or procurement clause logic
- proof delivery
- authority and buyer packaging

It should not create:

- a second pack engine
- a second governance core

## First useful outputs

The first valuable outputs are:

- committee-ready review pack
- procurement-facing clause bundle
- review decision trace
- stronger public-owner meeting or approval story

## Sequence

### PPC1

Committee pack and clause bundle layer only.

### PPC2

Decision trace layer.

### PPC3

Later:

- richer procurement execution memory
- stronger vendor or SLA linkage

## Acceptance

This pack is useful when public-owner and municipal review flows become easier
to package, circulate, and defend without turning SwissBuilding into a generic
procurement system.
