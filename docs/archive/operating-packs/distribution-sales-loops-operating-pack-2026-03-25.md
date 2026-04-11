# Distribution and Sales Loops Operating Pack

Date de controle: `25 mars 2026`

## Purpose

This pack turns the broad `distribution and embedded channels` idea into
concrete land-and-expand loops that SwissBuilding can productize.

The goal is not "marketing automation".
The goal is to make successful product use spread more naturally through:

- adjacent buildings
- adjacent teams
- adjacent organizations
- adjacent contributors

## Hard rule

A distribution loop is valuable only if it follows real product success:

- a pack was used
- a proof flow closed cleanly
- an authority or partner interaction was easier
- another building or team now has a reason to adopt

No synthetic growth mechanics detached from workflow value.

## Minimum objects

### DistributionLoopSignal

Represents a signal that product success may spread.

Minimum shape:

- `id`
- `signal_type`
- `building_id`
- `org_id`
- `adjacent_scope`
- `confidence`

### ExpansionOpportunity

Represents a concrete land-and-expand opportunity.

Minimum shape:

- `id`
- `source_signal_id`
- `target_scope`
- `opportunity_type`
- `recommended_next_step`
- `status`

### EmbeddedAdoptionEvidence

Represents evidence that a bounded external surface created pull.

Minimum shape:

- `id`
- `channel_type`
- `audience_type`
- `building_id`
- `interaction_summary`
- `observed_at`

## Existing anchors to reuse

This pack should extend:

- embedded channels
- buyer packaging
- `ProofDelivery`
- partner trust
- public owner and authority flows

It should not create:

- CRM replacement behavior
- standalone sales pipeline logic

## First useful outputs

The first valuable outputs are:

- adjacent-building expansion hint
- external-view adoption evidence
- cross-team opportunity signal
- recommended next spread path

## Sequence

### DSL1

Signal layer only.

### DSL2

Opportunity layer with recommended next step.

### DSL3

Later:

- stronger account-spread heuristics
- embedded-to-rollout conversion loops

## Acceptance

This pack is useful when SwissBuilding can detect and support real
account-expansion paths from actual workflow success.
