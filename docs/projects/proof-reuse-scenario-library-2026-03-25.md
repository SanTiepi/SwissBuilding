# Proof Reuse Scenario Library

Date de controle: `25 mars 2026`

## Purpose

This library defines the scenarios where SwissBuilding should prove that one
piece of evidence can create value multiple times.

This is one of the strongest `10x` vectors in the product.

## Rule

A proof-reuse scenario matters only if:

- the same evidence would normally be re-sent, re-explained, or regenerated
- the later audience is different from the first one
- SwissBuilding can keep caveats, freshness, and provenance visible

## Scenario 1 - Diagnostic report reused for authority procedure

Source proof:

- validated diagnostic publication from `Batiscan`

First audience:

- owner or manager

Later audience:

- authority or commune

Reuse value:

- no manual rebuild of the diagnostic explanation
- direct reuse in authority pack
- caveats and version remain visible

Surfaces:

- diagnostics tab
- authority pack
- ProofDelivery
- procedure view

## Scenario 2 - Diagnostic proof reused for transaction pack

Source proof:

- diagnostic publication
- remediation or monitoring follow-up

First audience:

- compliance or operations team

Later audience:

- buyer
- lender
- insurer

Reuse value:

- shared evidence base with audience-specific caveats
- no re-asking for already known proof

Surfaces:

- transfer package
- buyer packaging
- transaction or lender presets

## Scenario 3 - Permit or authority pack reused for committee review

Source proof:

- authority pack and related procedure state

First audience:

- authority

Later audience:

- committee
- procurement circulation
- public owner review

Reuse value:

- same core proof base
- adapted summary layer instead of rebuilt dossier

Surfaces:

- public owner review pack
- committee pack
- review decision trace

## Scenario 4 - One plan or official drawing reused across local requests

Source proof:

- plan
- official surveyor plan
- versioned drawing

First audience:

- permit procedure

Later audience:

- contractor
- authority complement response
- insurer

Reuse value:

- less attachment chaos
- known current version
- explicit replacement chain

Surfaces:

- authority pack
- ProofDelivery
- future geometry intelligence

## Scenario 5 - Compliance evidence reused for portfolio control

Source proof:

- obligation completion
- proof delivery
- acknowledgement

First audience:

- one building team

Later audience:

- portfolio manager
- public owner governance

Reuse value:

- same truth powers local workflow and portfolio oversight
- no second reporting system required

Surfaces:

- ControlTower
- portfolio views
- benchmarking grounded in proof

## Scenario 6 - Public-domain or communal proof reused after local review

Source proof:

- local form
- occupation authorization
- communal preavis

First audience:

- commune

Later audience:

- canton
- contractor
- owner archive

Reuse value:

- local decision stays attached to the building
- later routing and caveats stay legible

Surfaces:

- pilot communes
- PermitProcedure
- timeline
- authority pack

## Scenario 7 - Handover pack reused by the next operator

Source proof:

- transfer package
- timeline
- caveats
- unresolved blockers

First audience:

- outgoing owner or manager

Later audience:

- incoming owner or manager

Reuse value:

- memory transfer instead of folder dump
- unresolved issues stay visible

Surfaces:

- passport exchange
- transfer package
- building overview

## Product requirement

For every proof-reuse scenario the product should preserve:

- source
- current version
- send history
- acknowledgement state when available
- freshness or caveat signal
- audience-specific inclusion and exclusion

## Acceptance

SwissBuilding is winning when a user can say:

- "we already have that proof"
- "we know which version"
- "we know who received it"
- "we can reuse it safely here"
