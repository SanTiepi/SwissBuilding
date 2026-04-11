# Canonical Identity Resolution Pack

Date de controle: `25 mars 2026`

## Purpose

SwissBuilding depends on durable identity resolution.

If identity is weak, then:

- proof lands on the wrong object
- imports create duplicates
- procedures route incorrectly
- trust in the workspace collapses

## Hard rule

Never blur:

- `egid`
- `egrid`
- `official_id`

They are different canonical concepts.

## Identity layers

### Federal building identity

- `egid`

Used for:

- building-level anchoring
- diagnostic publication matching
- public data alignment

### Parcel identity

- `egrid`

Used for:

- land and parcel context
- restrictions and cadastral references

### Legacy or external identity

- `official_id`

Used for:

- imports
- legacy continuity
- source-system traceability

### Product identity

- `building_id`
- `contact_id`
- `document_id`

Used for:

- canonical internal linking

## Matching principles

- exact canonical identifiers beat heuristics
- heuristics should be explicit and reviewable
- unresolved ambiguity should never be silently auto-merged

## High-risk matching cases

- same address, different building
- multi-building sites
- parcel-level source attached to building-level object
- legacy imports with poor identifiers
- diagnostic publication with address but no stable identifier

## Product effects

Identity resolution should influence:

- import confidence
- diagnostic publication matching
- pilot commune routing
- proof reuse
- portfolio aggregation integrity

## Acceptance

This pack is succeeding when the product can say:

- what identifier matched
- why it matched
- when review is required
- what remains linked to source provenance
