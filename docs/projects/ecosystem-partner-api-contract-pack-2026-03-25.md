# Ecosystem Partner API Contract Pack

Date de controle: `25 mars 2026`

## Purpose

SwissBuilding should become easier to integrate into the ecosystem without
turning every integration into a custom project.

This pack defines the contract posture for partners.

## Rule

Partner API contracts should expose bounded value, not the whole internal
system.

## Contract families

### Publication contracts

Examples:

- diagnostic publication
- passport publication
- proof or pack publication

### Import contracts

Examples:

- mission order
- intake
- bounded metadata import

### Viewer contracts

Examples:

- bounded pack viewer
- embedded building summary

## Contract rules

- versioned
- bounded
- idempotent
- source-aware
- audience-safe

## Acceptance

This pack is succeeding when partner integration becomes a productized contract
instead of custom glue.
