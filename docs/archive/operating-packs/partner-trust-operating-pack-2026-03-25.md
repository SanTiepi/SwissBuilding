# Partner Trust Operating Pack

Date de controle: `25 mars 2026`

## Purpose

This is the execution-oriented companion to:

- [partner-network-and-contributor-reputation-program.md](./partner-network-and-contributor-reputation-program.md)

The goal is to make `partner trust` operational without falling into
marketplace noise.

## Hard rule

Partner trust is not a public star rating.

It is an internal decision aid grounded in:

- delivered proof quality
- responsiveness
- rework
- acknowledgement quality
- workflow fit

## Minimum signals

### DeliveryReliabilitySignal

Built from:

- `ProofDelivery`
- failure rate
- acknowledgement rate
- resend rate

Question answered:

- does this partner reliably deliver and close the loop

### EvidenceQualitySignal

Built from:

- missing-piece frequency
- rejected pack frequency
- complement-request frequency after partner contribution

Question answered:

- does this partner produce clean, reusable proof

### ResponsivenessSignal

Built from:

- time to first response
- time to complete request
- overdue request rate

Question answered:

- does this partner unblock work quickly or stall it

### WorkflowFitSignal

Built from:

- building type fit
- procedure type fit
- pollutant or domain fit
- canton or commune familiarity

Question answered:

- is this partner a good fit for this specific workflow

## Product outputs

The first useful outputs should be:

- `preferred_for_this_flow`
- `use_with_review`
- `avoid_for_urgent_cases`
- `strong_for_authority_packs`
- `strong_for_pollutant_flows`

These are internal routing hints, not customer-facing rankings.

## Dependencies

Partner trust should be fed by:

- `ProofDelivery`
- future `Authority Flow`
- `DiagnosticPublication`
- pack acceptance or rejection
- rework and missing-piece loops

Without those anchors, trust signals will be too noisy.

## Build sequence

### P1

Schema-only foundation:

- `PartnerTrustProfile`
- `PartnerTrustSignal`
- `WorkflowFitHint`

### P2

Internal score assembly:

- delivery reliability
- responsiveness
- evidence quality

### P3

Routing assist only:

- hints in assignment or recommendation flows
- no public ranking
- no automatic hard gating

## Governance rules

- low-confidence signals stay hidden or review-only
- trust hints must be explainable
- users should be able to see why a hint exists
- no irreversible exclusion based on weak evidence

## Acceptance

The layer is useful when SwissBuilding can route work better without becoming
a shallow marketplace.
