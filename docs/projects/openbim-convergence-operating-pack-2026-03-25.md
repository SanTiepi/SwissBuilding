# openBIM Convergence Operating Pack

Date de controle: `25 mars 2026`

## Purpose

This is the execution-oriented companion to:

- [openbim-digital-logbook-and-passport-convergence-program.md](./openbim-digital-logbook-and-passport-convergence-program.md)

The goal is to make SwissBuilding standards-aware in a product-useful way,
without pretending to become a BIM authoring platform.

## Hard rule

Interoperability must improve one of these:

- exchange usefulness
- requirement validation
- issue or contradiction portability
- building record longevity

If a standards adapter does not improve a real workflow, it is too early.

## Build posture

Build:

- mapping profiles
- requirement profiles
- export manifests
- issue bridges

Do not build:

- full IFC editing
- giant standards surface area with no user pull
- symbolic standard support without product use

## Minimum objects

### IFCMappingProfile

Defines how SwissBuilding concepts map to IFC-relevant structures.

Minimum shape:

- `id`
- `profile_code`
- `version`
- `scope`
- `supported_entity_kinds`

### BCFIssueBridge

Represents an issue or contradiction bridge to BCF-like semantics.

Minimum shape:

- `id`
- `issue_id`
- `bridge_status`
- `bcf_topic_ref`
- `related_geometry_anchor_id`

### IDSRequirementProfile

Represents a machine-readable requirement profile mindset.

Minimum shape:

- `id`
- `profile_code`
- `audience_type`
- `required_information_kinds`
- `validation_mode`

### DigitalBuildingLogbookMapping

Represents the mapping from SwissBuilding record layers toward a digital
building logbook or passport.

Minimum shape:

- `id`
- `mapping_code`
- `version`
- `covered_sections`
- `exportable_layers`

## Existing anchors to reuse

openBIM convergence should extend:

- geometry intelligence
- passport exchange
- proof and requirement layers
- issue and contradiction models

It should not create:

- a second building record model
- a BIM-first product identity

## First useful outputs

The first valuable outputs are:

- machine-readable passport manifest
- exportable issue or contradiction bundle
- requirement completeness profile
- IFC-aware mapping direction

## Sequence

### OB1

Mapping and requirement profiles only.

### OB2

Export and issue bridge layer.

### OB3

Later:

- richer IFC references
- selective IDS validation
- broader digital logbook interoperability

## Acceptance

This layer is useful when SwissBuilding records become easier to exchange,
validate, and keep future-proof.
