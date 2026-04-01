# Release Safety and Progressive Exposure Pack

Date de controle: `25 mars 2026`

## Purpose

SwissBuilding should ship real slices without exposing half-wired behavior.

This pack defines how new capabilities become visible safely.

## Rule

Progressive exposure beats partial exposure.

## Exposure levels

### Internal only

Use when:

- semantics are still moving
- confidence is not stable
- the surface is mainly for operator validation

### Bounded pilot

Use when:

- one wedge
- one workflow
- one persona set
- explicit fallback exists

### General visible

Use when:

- workflow value is proven
- confidence and review paths are explicit
- validation loops are credible

## Product rule

Do not expose a surface just because the model exists.

Expose it only when:

- the user can understand it
- the next action is clear
- the fallback path is safe

## Acceptance

The pack is succeeding when new slices enter the product without:

- fake completeness
- hidden blockers
- ambiguous ownership
- broken trust in the main workspace
