# Embedded Channels Operating Pack

Date de controle: `25 mars 2026`

## Purpose

This is the execution-oriented companion to:

- [distribution-and-embedded-channels-program.md](./distribution-and-embedded-channels-program.md)

The goal is to make SwissBuilding easier to insert into adjacent workflows
without requiring full migration into the product.

## Hard rule

An embedded or distributed surface must do one of these:

- reduce switching cost
- increase account spread
- expose bounded proof or readiness value

If it only mirrors the app without adding adoption leverage, it is not worth
the surface cost.

## Build posture

Build:

- bounded summary surfaces
- external viewer semantics
- embed tokens and capability boundaries
- account expansion signals

Do not build:

- full white-label complexity
- unbounded external app clones
- broad API sprawl with no distribution story

## Minimum objects

### BoundedEmbedToken

Represents a bounded embed or external-view capability.

Minimum shape:

- `id`
- `token_scope`
- `audience_type`
- `building_id`
- `org_id`
- `expires_at`
- `revoked_at`

### ExternalViewerProfile

Represents an external viewing surface profile.

Minimum shape:

- `id`
- `profile_code`
- `audience_type`
- `allowed_sections`
- `redaction_rules`

### PartnerSummaryEndpoint

Represents a stable summary artifact for external consumption.

Minimum shape:

- `id`
- `endpoint_code`
- `audience_type`
- `payload_type`
- `contract_version`

### AccountExpansionTrigger

Represents a signal that one successful building or workflow is likely to
spread inside an account.

Minimum shape:

- `id`
- `trigger_type`
- `building_id`
- `org_id`
- `confidence`
- `notes`

## Existing anchors to reuse

Embedded channels should extend:

- pack and passport outputs
- `ProofDelivery`
- future partner trust
- future enterprise rollout grants

They should not create:

- a second app shell
- a second sharing system detached from the building file

## First useful outputs

The first valuable outputs are:

- bounded passport summary embed
- readiness or trust summary widget
- partner-safe viewer
- executive snapshot surface

## Sequence

### EC1

Bounded embed token and viewer semantics only.

### EC2

Stable summary artifact and expansion signal layer.

### EC3

Later:

- richer embedded widgets
- deeper incumbent-system connectors

## Acceptance

This pack is useful when SwissBuilding can spread through an account without
requiring every actor to live in the full app.
