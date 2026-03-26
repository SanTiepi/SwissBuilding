# Insurer and Fiduciary Surfaces Operating Pack

Date de controle: `25 mars 2026`

## Purpose

This pack defines how SwissBuilding should serve insurers, fiduciaries, and
similar bounded external actors without becoming a full insurer or finance
platform.

## Hard rule

These surfaces must remain:

- bounded
- pack-centric
- trust-centric
- evidence-driven

They should not pull the product into claims, underwriting, or accounting
stacks too early.

## Build posture

Build:

- bounded insurer or fiduciary packs
- summary views
- trust and receipt traces
- explicit data redaction and audience logic

Do not build:

- full insurer platform
- full fiduciary back office
- complex external workflow engines before core packs are strong

## Minimum objects

### InsurerReadinessPack

Represents a bounded insurer-facing pack.

Minimum shape:

- `id`
- `building_id`
- `pack_version`
- `scope_summary`
- `risk_sections`
- `proof_refs`

### FiduciaryCompliancePack

Represents a bounded fiduciary-facing pack.

Minimum shape:

- `id`
- `building_id`
- `pack_version`
- `document_scope`
- `fiscal_or_compliance_sections`
- `proof_refs`

### ExternalAudienceRedactionProfile

Represents redaction and exposure rules for external audiences.

Minimum shape:

- `id`
- `audience_type`
- `allowed_sections`
- `blocked_sections`
- `reasoning_notes`

## Existing anchors to reuse

These surfaces should extend:

- pack architecture
- `ProofDelivery`
- exchange contracts
- authority and buyer packaging presets

They should not create:

- a second packaging engine
- a second external sharing model

## First useful outputs

The first valuable outputs are:

- insurer-facing pack preset
- fiduciary-facing pack preset
- explicit audience redaction profile
- trust and receipt trace tied to the pack

## Sequence

### IF1

Pack preset and redaction layer only.

### IF2

Receipt and bounded viewer reinforcement.

### IF3

Later:

- richer lender or transaction variants
- stronger finance-readiness hooks

## Acceptance

This pack is useful when insurers and fiduciaries can consume cleaner, more
trustworthy building packs without dragging SwissBuilding into their full core
systems.
