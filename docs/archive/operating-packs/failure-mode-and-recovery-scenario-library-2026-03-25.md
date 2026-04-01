# Failure Mode and Recovery Scenario Library

Date de controle: `25 mars 2026`

## Purpose

SwissBuilding should not only be strong on ideal flows.

It should also be clear and trustworthy when things go wrong.

This library defines the failure modes that matter most and what recovery
should look like.

## Rule

A failure mode matters when it changes:

- user trust
- canonical truth
- next action clarity
- proof defensibility

## Failure mode 1 - wrong or ambiguous building match

Risk:

- proof lands on the wrong building

Recovery expectation:

- confidence drops
- review becomes explicit
- no silent merge

## Failure mode 2 - stale or superseded proof reused by mistake

Risk:

- wrong pack or authority submission

Recovery expectation:

- freshness warning is visible
- newer version is shown
- reuse path is blocked or caveated

## Failure mode 3 - authority request not handled in time

Risk:

- late response
- procedure delay

Recovery expectation:

- overdue state becomes explicit
- route to responsible actor is visible
- resend or response trace remains visible

## Failure mode 4 - import or intake creates duplicate truth

Risk:

- same building or document represented twice

Recovery expectation:

- duplication is reviewable
- provenance is preserved
- repair path is visible

## Failure mode 5 - local rule cannot be safely automated

Risk:

- false certainty

Recovery expectation:

- review_required state
- no fake deterministic route

## Failure mode 6 - cross-product publication does not match or arrives incomplete

Risk:

- Batiscan output loses operational value in SwissBuilding

Recovery expectation:

- matching issue is visible
- publication remains traceable
- operator sees what blocks reuse

## Acceptance

This library is succeeding when the product can fail in a way that is still
understandable and recoverable.
