# Confidence Ladder and Manual Review Pack

Date de controle: `25 mars 2026`

## Purpose

SwissBuilding should not pretend that every rule, route, or proof state is
machine-certain.

This pack defines a single confidence ladder so the product can:

- automate where safe
- surface uncertainty where needed
- route ambiguous cases into explicit review
- learn from resolved reviews later

## Hard rule

Visible uncertainty is better than hidden false certainty.

If the system cannot explain why it is confident, it should not auto-commit a
workflow branch.

## Confidence ladder

### Level 1 - `auto_safe`

Meaning:

- source is strong
- projection is stable
- workflow effect is low-risk or well-bounded

Allowed behavior:

- auto-project into canonical surfaces

### Level 2 - `auto_with_notice`

Meaning:

- likely correct
- still worth showing provenance or caveat

Allowed behavior:

- auto-project
- show explanation and caveat

### Level 3 - `review_required`

Meaning:

- ambiguity is material
- local rule or route may differ
- human confirmation is needed

Allowed behavior:

- create review action
- do not silently pick one branch

### Level 4 - `blocked`

Meaning:

- missing source
- contradictory source
- high-stakes ambiguity

Allowed behavior:

- block downstream automation
- require explicit human resolution

## Where this ladder must apply

- `SwissRules` applicability
- pilot communes
- authority routing
- proof reuse when freshness or caveat matters
- partner trust signals
- agent-generated recommendations
- document classification when downstream effect is high-stakes

## Product surfaces

The ladder should be visible in:

- building-level blocker summary
- procedure view
- ControlTower
- authority pack caveats
- proof reuse surfaces
- admin review queue

## Minimal visible outputs

- confidence level
- short explanation
- source link or provenance
- reason for review or block
- who should review
- what can resume after review

## Review loop

1. system emits `review_required` or `blocked`
2. human resolves the ambiguity
3. outcome is captured
4. outcome can later inform rules, adapters, or agent prompts

## Product rule

Do not hide review-required states inside logs or admin-only tables.

If a review changes what the user should do next, it belongs in the product
workflow.

## Acceptance

This pack is succeeding when users can tell the difference between:

- safe automation
- likely but caveated output
- cases needing review
- cases that must stop the flow
