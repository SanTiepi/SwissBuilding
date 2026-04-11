# Communal Adapter Projection Map

Date de controle: `25 mars 2026`

## Purpose

This map explains how communal research should project into existing
SwissBuilding product anchors.

It exists to prevent two common mistakes:

- storing communal knowledge as dead metadata only
- creating a parallel communal workflow engine

## Projection rule

A communal adapter should project into existing product anchors only:

- `SwissRules`
- `permit_tracking`
- future `PermitProcedure`
- `Obligation`
- `ControlTower`
- `authority_pack`
- future `ProofDelivery`

It should not create:

- a second permit engine
- a second action inbox
- a second deadline entity
- a commune-only document model

## Canonical projection chain

1. official communal source
2. `CommunalAdapterProfile`
3. `CommunalRuleOverride` and or `CommunalProcedureVariant`
4. `ApplicabilityEvaluation` update in `SwissRules`
5. projection into one or more product effects

## Product effects

### Permit need effect

Use when the communal rule changes whether a permit or a declaration path is
required.

Project into:

- `permit_tracking`
- manual-review flag when confidence is low

### Procedure routing effect

Use when the commune changes who reviews, preavis-es, or receives part of the
dossier.

Project into:

- future `PermitProcedure`
- authority assignment or routing
- `ControlTower` if a route-specific step is missing

### Proof requirement effect

Use when the commune adds a local plan, form, notice, or review piece.

Project into:

- `authority_pack`
- future `ProofDelivery`
- `ControlTower` missing-proof action when needed

### Blocker effect

Use when the commune adds a condition that blocks forward motion.

Project into:

- `ControlTower`
- `Obligation` only if there is a due date or response date
- future `PermitProcedure` blocker state

### Manual-review effect

Use when the communal source is too local, too vague, or too document-shaped
for safe automation.

Project into:

- `manual_review_required`
- `ControlTower` review action
- no false deterministic workflow branch

## Commune examples

### Nyon

Likely first projections:

- public inquiry timing -> `PermitProcedure` timing note or blocker context
- official surveyor plan requirement -> `authority_pack` proof requirement
- commune permit framing -> `permit_tracking` explanation enrichment

### Meyrin

Likely first projections:

- commune and canton split -> `PermitProcedure` route or authority assignment
- public-domain occupation dependency -> `ControlTower` blocker
- local review branch -> `manual_review_required` when the case is ambiguous

### Lausanne

Likely first projections:

- permit-exempt vs permit-required branch -> `permit_tracking`
- work declaration form requirement -> `authority_pack` proof requirement
- heritage or urban preavis signal -> `PermitProcedure` local review step or
  manual review

### Ville de Fribourg

Likely first projections:

- commune vs prefecture or canton split -> `PermitProcedure` routing
- urban or heritage review body -> local review step
- `FRIAC` filing context -> authority-pack variant and route explanation

## Implementation pattern

### Adapter profile

Use `CommunalAdapterProfile` to state:

- commune identity
- canton identity
- current support level
- source set
- fallback mode

### Override

Use `CommunalRuleOverride` only when the commune adds a real delta over the
cantonal or federal default.

### Procedure variant

Use `CommunalProcedureVariant` only when the workflow itself changes.

If the commune changes only required proof, do not model a fake new procedure.

## Confidence rule

If the product cannot explain:

- which source triggered the communal branch
- what workflow or proof changed
- whether the case still needs manual review

then the adapter is not ready to automate.

## Acceptance

A communal adapter is useful when it creates one of these visible wins:

- clearer route to the right authority
- earlier blocker visibility
- earlier proof completeness visibility
- explicit manual-review flag instead of silent ambiguity
