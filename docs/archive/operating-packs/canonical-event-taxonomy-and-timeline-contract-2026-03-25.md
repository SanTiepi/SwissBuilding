# Canonical Event Taxonomy and Timeline Contract

Date de controle: `25 mars 2026`

## Purpose

The timeline should become one of the strongest truth surfaces in the product.

That only works if event semantics are consistent across:

- procedures
- proof
- diagnostics
- obligations
- handoffs
- reviews
- agents

## Rule

If an event changes what the user should know, prove, or do next, it belongs in
the canonical timeline.

## Event families

### Building memory events

Examples:

- building_created
- building_identity_updated
- ownership_changed
- manager_changed

Purpose:

- preserve long-term continuity

### Diagnostic events

Examples:

- diagnostic_mission_ordered
- diagnostic_publication_received
- diagnostic_publication_matched
- diagnostic_publication_version_added

Purpose:

- make diagnostic proof visible as part of building memory

### Procedure events

Examples:

- procedure_created
- procedure_submitted
- procedure_step_completed
- authority_request_opened
- authority_request_responded
- procedure_approved
- procedure_rejected
- procedure_withdrawn

Purpose:

- make procedural progress and blockers legible

### Obligation events

Examples:

- obligation_created
- obligation_due_soon
- obligation_overdue
- obligation_completed

Purpose:

- turn deadlines into visible history, not just current badges

### Proof events

Examples:

- proof_pack_generated
- proof_delivery_sent
- proof_delivery_viewed
- proof_delivery_acknowledged
- proof_replaced

Purpose:

- show evidence flow and downstream traceability

### Review and confidence events

Examples:

- review_required_opened
- review_resolved
- confidence_blocked
- confidence_upgraded

Purpose:

- make ambiguity and resolution visible instead of implicit

### Agent events

Examples:

- agent_recommendation_created
- agent_recommendation_accepted
- agent_recommendation_rejected
- knowledge_correction_recorded

Purpose:

- keep automation inspectable and auditable

## Event contract

Every canonical event should preserve:

- `event_type`
- `building_id`
- `occurred_at`
- `actor_kind`
- `actor_label`
- `source_object_type`
- `source_object_id`
- `summary`
- `detail_state`
- `confidence_level` when relevant
- `next_action_hint` when relevant

## Rendering rules

- timeline should show a human-readable summary first
- important proof or procedure events should expose drilldown
- noise events should collapse
- event family should be visually recognizable

## Product rule

Do not let each subsystem invent unrelated timeline semantics.

A shared event taxonomy is worth more than local convenience.

## Acceptance

The contract is succeeding when the timeline can answer:

- what changed
- why it matters
- what proof exists
- what is blocked
- what happened last
- what should happen next
