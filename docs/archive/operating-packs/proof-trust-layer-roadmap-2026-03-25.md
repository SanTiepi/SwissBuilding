# Proof and Trust Layer Roadmap

Date de controle: `25 mars 2026`

## Purpose

`ProofDelivery` is only the first visible slice.

The bigger target is a trust layer that makes building evidence:

- versioned
- attributable
- deliverable
- receipted
- reusable
- defensible

This roadmap defines the climb from simple delivery logs to an actual trust
layer.

Reference:

- [proof-reuse-scenario-library-2026-03-25.md](./proof-reuse-scenario-library-2026-03-25.md)

## Stage 1 - Delivery visibility

Primary object:

- `ProofDelivery`

What it should answer:

- who received what
- when
- by which method
- which version or hash
- whether it was viewed or acknowledged

This is the minimum needed to beat email chaos.

## Stage 2 - Receipt and acknowledgement

Add:

- delivery receipts
- authority acknowledgements
- response linkage
- resend history

What it should answer:

- did the recipient really receive it
- is there a traceable acknowledgement
- did we resend or replace it

## Stage 3 - Evidence custody

Add:

- immutable evidence version references
- custody events
- replacement chains
- superseded markers

What it should answer:

- which version was the active one at send time
- what replaced it later
- whether an old version was still used downstream

## Stage 4 - Trust vault

Add:

- stronger integrity metadata
- signature hooks
- retention policy hooks
- legal hold or archive markers

What it should answer:

- can this proof be defended later
- can we show a clear chain from source to delivered artifact

## Stage 5 - Exchange trust

Add:

- cross-system publication receipts
- trust metadata in exchange contracts
- acceptance or rejection traces

What it should answer:

- can another system safely consume this evidence
- can both sides agree on the version and provenance

## Product rules

The trust layer should always stay attached to real user value:

- fewer repeated uploads
- less ambiguity
- clearer accountability
- reusable proof across audiences
- safer authority and partner interactions

It must not become an abstract compliance subsystem detached from workflow.

## Existing anchors to extend

- packs
- `ProofDelivery`
- `Authority Flow`
- `DiagnosticPublication`
- timeline / activity
- exchange contracts

## Not now

Do not start with:

- heavy PKI ambitions as the first milestone
- marketplace identity schemes
- overengineered legal archiving before delivery visibility exists

## Acceptance

The layer is succeeding when SwissBuilding can show:

- what proof exists
- which version is current
- who received which version
- what acknowledgement exists
- whether a later procedure reused the same evidence
