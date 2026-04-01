# Must-Win Workflow Map

Date de controle: `25 mars 2026`

## Purpose

This map defines the workflows SwissBuilding must beat decisively.

The goal is not to list every possible feature path.

The goal is to identify the few workflows where `10x better` changes adoption:

- clearer
- faster
- less fragile
- more reusable
- more defensible

## Rule

A workflow is `must-win` only if all are true:

- it happens often enough to shape user habits
- it currently causes rework, delay, or ambiguity
- SwissBuilding can reduce the need for email, PDF chasing, or re-explaining
- success strengthens canonical building truth

## Workflow 1 - Understand the building in under five minutes

Primary user:

- property manager
- owner
- incoming employee

Old market pattern:

- open drive
- search emails
- guess which PDF is current
- call someone to understand context

SwissBuilding win condition:

- building opens with current state, blockers, deadlines, proof, and key history
- no reconstruction required

Core surfaces:

- building overview
- timeline
- diagnostics
- obligations
- ControlTower

Visible win:

- `minutes or hours -> under five minutes`

## Workflow 2 - Know what blocks progress before starting work

Primary user:

- property manager
- project lead
- contractor coordinator

Old market pattern:

- documents appear complete
- hidden permit or proof gap appears late
- project is delayed by local review, missing plan, or authority request

SwissBuilding win condition:

- blockers are visible early
- route to authority is clear
- proof requirement is explicit
- manual-review ambiguity is visible instead of hidden

Core surfaces:

- `permit_tracking`
- future `PermitProcedure`
- `SwissRules`
- ControlTower

Visible win:

- `surprise blocker -> early explicit blocker`

## Workflow 3 - Produce the right dossier for the right audience once

Primary user:

- property manager
- owner representative
- diagnostic or compliance coordinator

Old market pattern:

- rebuild package for authority
- rebuild package for insurer
- rebuild package for buyer
- rebuild package for fiduciary

SwissBuilding win condition:

- one canonical evidence base
- audience-specific pack view
- explicit inclusion and exclusion
- trust and delivery trace

Core surfaces:

- authority pack
- transfer package
- passport exchange
- ProofDelivery

Visible win:

- `rebuild every time -> generate, review, send`

## Workflow 4 - Handle complement requests without chaos

Primary user:

- property manager
- public owner
- permit coordinator

Old market pattern:

- authority asks by email
- response deadline gets buried
- nobody knows what was sent back or acknowledged

SwissBuilding win condition:

- request is attached to the procedure
- response deadline is tracked
- missing proof is explicit
- acknowledgement or resend trace is visible

Core surfaces:

- Authority Flow
- Obligation
- ControlTower
- ProofDelivery

Visible win:

- `email thread chaos -> procedural loop with trace`

## Workflow 5 - Reuse diagnostic proof across later procedures

Primary user:

- owner
- property manager
- diagnostician

Old market pattern:

- diagnostic exists
- later permit or transaction asks for overlapping proof
- same material is re-explained or re-sent manually

SwissBuilding win condition:

- diagnostic publication becomes part of building memory
- later packs and procedures reuse it explicitly
- caveats and freshness remain visible

Core surfaces:

- diagnostic publications
- passport
- authority pack
- transfer package
- ProofDelivery

Visible win:

- `one-off report -> reusable proof asset`

## Workflow 6 - Run a portfolio from one action queue

Primary user:

- gerance
- public owner team
- asset manager

Old market pattern:

- building-by-building status hunting
- deadlines in multiple systems
- blockers found too late

SwissBuilding win condition:

- one portfolio action queue
- per-building drilldown from one priority list
- procedural blockers, obligations, inbox items, and unmatched publications in
  one operating surface

Core surfaces:

- ControlTower
- portfolio views
- obligations
- document inbox
- procedure state

Visible win:

- `status hunting -> one daily operating queue`

## Workflow 7 - Transfer the building without losing memory

Primary user:

- owner
- buyer
- asset transition lead

Old market pattern:

- partial archive export
- undocumented oral handover
- proof and caveats disappear during transition

SwissBuilding win condition:

- handoff pack is explicit
- history and caveats stay attached
- next actor inherits truth, not folder chaos

Core surfaces:

- transfer package
- passport exchange
- timeline
- proof and trust layer

Visible win:

- `handover by folder dump -> structured memory transfer`

## Ranking

Highest near-term value:

1. understand the building
2. know blockers before starting work
3. produce the right dossier once
4. handle complement requests cleanly
5. portfolio action queue

Higher-future moat:

6. reuse diagnostic proof across procedures
7. transfer the building without losing memory

## Product rule

If a feature does not strengthen at least one must-win workflow, it should be:

- deferred
- integrated instead of built
- or reduced to a schema or projection only
