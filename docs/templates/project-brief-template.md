# Project Brief Template

Use this template for Claude execution briefs. Keep it concise and fill only task-specific deltas.
For faster hardening/polish waves, compact mode is available in:
- `docs/templates/wave-brief-compact-template.md`

## Mission

- business outcome:
- user/problem context:
- visible consumer window (`<=2 waves`):

## Agent usage

- include one explicit line:
  - `Tu peux utiliser tes agents si pertinent, notamment pour ...`
  - or `Aucun agent n'est necessaire pour cette tache.`

## Scope

- in scope:
- out of scope:

## Target files

- primary file(s):
- satellites (tests/schemas/routes):
- change mode:
  - `new`:
  - `modify`:
- hub-file ownership:
  - `supervisor_merge`:
  - `agent_allowed`:
- do-not-touch (hub files reserved to supervisor merge):

## Non-negotiable constraints

- data/model constraints:
- technical constraints:
- repo conventions to preserve:

## Validation

- validation type:
  - `canonical_integration`:
  - `targeted_unit_api`:
- commands to run:
- required test level:
- acceptance evidence to report:

## Exit criteria

- functional:
- quality/reliability:
- docs/control-plane updates:

## Non-goals

- explicitly not part of this brief:

## Deliverables

- code:
- tests:
- docs:

## Wave closeout (required in ORCHESTRATOR.md)

- clear:
- fuzzy:
- missing:
