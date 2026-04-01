# Killer Demo Operating Pack

Date de controle: `25 mars 2026`

## Purpose

This is the execution-oriented companion to:

- [killer-demo-and-wow-surfaces-program.md](./killer-demo-and-wow-surfaces-program.md)
- [demo-and-sales-enablement-program.md](./demo-and-sales-enablement-program.md)

The goal is to make demos repeatable, buyer-legible, and grounded in real
product truth.

Use:

- [must-win-workflow-map-2026-03-25.md](./must-win-workflow-map-2026-03-25.md)
- [proof-reuse-scenario-library-2026-03-25.md](./proof-reuse-scenario-library-2026-03-25.md)

## Hard rule

A demo surface is only valid if it is:

- seeded reproducibly
- tied to real objects
- explainable in one sentence
- still useful outside the demo

No isolated demo hacks.

## Build posture

Build:

- seeded canonical scenarios
- operator shortcuts
- wow surfaces tied to proof, readiness, or memory
- persona-aware reveal moments

Do not build:

- fake front-end magic
- one-off presentation branches
- features that exist only in demos

## Minimum objects

### DemoScenario

Represents one canonical demo narrative.

Minimum shape:

- `id`
- `scenario_code`
- `persona_target`
- `starting_state`
- `reveal_surfaces`
- `proof_moment`
- `action_moment`

### DemoRunbook

Represents the operator path for a scenario.

Minimum shape:

- `id`
- `scenario_code`
- `step_order`
- `expected_ui_state`
- `fallback_notes`

### OperatorDemoState

Represents a known-good seeded UI state for live demo use.

Minimum shape:

- `id`
- `scenario_code`
- `seed_key`
- `reset_ready`
- `notes`

## Existing anchors to reuse

Demo flows should reuse:

- demo seed data
- `ControlTower`
- packs
- readiness surfaces
- diagnostics and proof links
- timeline and authority surfaces

They should not create:

- demo-only data models
- demo-only UI branches

## First useful outputs

The first strong demo outputs are:

- one clean property-manager flow
- one authority-ready packaging flow
- one proof or readiness reveal moment
- one before or after memory moment

## Sequence

### D1

Canonical scenario and runbook layer only.

### D2

Operator shortcuts and known-good seeded states.

### D3

Later:

- richer wow surfaces
- persona switching
- executive summary mode

## Acceptance

This pack is succeeding when a demo can be repeated cleanly and still reflects
real product behavior.
