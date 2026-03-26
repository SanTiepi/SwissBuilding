# Authority Flow Foundation Pack

Date de controle: `25 mars 2026`

## Purpose

`Authority Flow` is not just "send a PDF".

It is the layer that turns authority interactions into a first-class workflow:

- submission
- request for complement
- response
- acknowledgement
- decision
- expiry
- history

This pack defines the product spine before implementation.

## Why it matters

Most tools stop at:

- document generation
- export
- email
- portal manual upload

That is not enough.
SwissBuilding should be the place where a building is:

- procedurally ready
- actually submitted
- traceably answered
- historically understandable

## Core objects

### AuthoritySubmission

Represents one procedural submission to an authority.

Minimum shape:

- `id`
- `building_id`
- `procedure_id`
- `audience_type`
- `authority_code`
- `channel_type`
- `status`
- `submission_reference`
- `submitted_at`
- `acknowledged_at`
- `decision_at`
- `pack_id`
- `submitted_by_org_id`
- `submitted_by_user_id`
- `current_request_count`

Suggested statuses:

- `draft`
- `ready`
- `submitted`
- `acknowledged`
- `complement_requested`
- `responded`
- `approved`
- `rejected`
- `withdrawn`
- `expired`

### AuthorityRequest

Represents an authority-originated request or clarification.

Minimum shape:

- `id`
- `submission_id`
- `procedure_id`
- `request_type`
- `status`
- `subject`
- `body`
- `received_at`
- `due_at`
- `responded_at`
- `response_pack_id`
- `request_reference`

Suggested statuses:

- `open`
- `in_review`
- `ready_to_respond`
- `responded`
- `closed`
- `overdue`

### AuthorityAcknowledgement

Represents proof that a submission or response was received.

Minimum shape:

- `id`
- `submission_id`
- `acknowledgement_type`
- `channel_type`
- `reference`
- `received_at`
- `proof_delivery_id`
- `raw_receipt_document_id`

### AuthorityDecision

Represents the outcome tied to the submission.

Minimum shape:

- `id`
- `submission_id`
- `decision_type`
- `decision_at`
- `effective_from`
- `effective_to`
- `decision_document_id`
- `summary`

## Relationship to existing SwissBuilding anchors

Authority Flow should extend:

- `PermitProcedure`
- `Obligation`
- `ControlTower`
- `authority_pack`
- `ProofDelivery`
- timeline / activity

Authority Flow should not create:

- a second deadline entity
- a second action feed
- a second proof channel
- a second procedure engine

## Product outputs

Authority Flow should make these things visible:

- submitted or not submitted
- what authority owns the next move
- whether an acknowledgement exists
- whether a complement is waiting
- whether the response deadline is at risk
- what version of the pack was sent
- what decision came back

## ControlTower hooks

Authority Flow should emit:

- `submission_ready`
- `submission_not_sent`
- `acknowledgement_missing`
- `complement_requested`
- `complement_overdue`
- `decision_received`
- `permit_expiring`

These should become first-class actions, not buried metadata.

## Proof hooks

Each submission or response should attach to:

- one pack or document version
- one delivery record
- one receipt or acknowledgement when available

This is what makes the authority relation defensible and reusable.

## Build sequence

### A1

Model the spine:

- `AuthoritySubmission`
- `AuthorityAcknowledgement`
- `AuthorityDecision`

Reuse the existing `AuthorityRequest` in the procedure layer if already modeled.

### A2

Project authority flow into:

- `ControlTower`
- timeline
- `PermitProcedure`
- `ProofDelivery`

### A3

Add UI:

- current submission state
- complement queue
- acknowledgement state
- decision history

### A4

Only later:

- channel-specific adapters
- portal/API automation
- authority-specific routing plugins

## Acceptance

Authority Flow is valuable when SwissBuilding can answer, for any procedure:

- was it sent
- when
- to whom
- using which pack version
- what came back
- what still blocks it
