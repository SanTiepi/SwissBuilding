# W76-C Eco Clause Template Backend Generator

## Mission

- business outcome: generate procurement-ready eco/compliance clause blocks from intervention context.
- user/problem context: readiness insight must become actionable tender language.
- visible consumer window (`<=2 waves`): W78-B pack integration consumes generated clause payloads.

## Agent usage

- `Tu peux utiliser tes agents si pertinent, notamment pour le service backend et ses tests.`

## Scope

- in scope:
  - create eco clause template service
  - define structured clause payload contract consumable by pack services
  - add focused backend tests
- out of scope:
  - route registration in `router.py`
  - direct UI integration

## Target files

- primary file(s):
  - `backend/app/services/eco_clause_template_service.py` (new)
- satellites (tests/schemas/routes):
  - `backend/app/services/authority_pack_service.py` (modify only if type wiring needed, no behavior change yet)
  - `backend/tests/test_eco_clause_template_service.py` (new)
- change mode:
  - `new`:
    - `backend/app/services/eco_clause_template_service.py`
    - `backend/tests/test_eco_clause_template_service.py`
  - `modify`:
    - optional minimal type wiring in `authority_pack_service.py`
- hub-file ownership:
  - `supervisor_merge`:
    - `backend/app/api/router.py`
    - `backend/app/schemas/__init__.py`
  - `agent_allowed`:
    - files listed in scope
- do-not-touch (hub files reserved to supervisor merge):
  - `backend/app/api/router.py`
  - `backend/app/schemas/__init__.py`
  - `backend/app/models/__init__.py`

## Non-negotiable constraints

- data/model constraints:
  - clause payload must include explicit evidence/provenance expectations
- technical constraints:
  - deterministic templates from input context
  - no external scraping/data fetching
- repo conventions to preserve:
  - compact service, high-signal tests

## Validation

- validation type:
  - `canonical_integration`: template payload consumable by pack services
  - `targeted_unit_api`: clause selection/rendering tests
- commands to run:
  - `cd backend && ruff check app/ tests/`
  - `cd backend && ruff format --check app/ tests/`
  - `cd backend && python -m pytest tests/test_eco_clause_template_service.py -q`
- required test level:
  - dedicated backend test file green
- acceptance evidence to report:
  - example generated clause payload for at least 2 intervention contexts

## Exit criteria

- functional:
  - eco clause template generator exists and returns structured payload
- quality/reliability:
  - deterministic output + green targeted tests
- docs/control-plane updates:
  - update W76-C status in `ORCHESTRATOR.md`

## Non-goals

- explicitly not part of this brief:
  - authority pack export rendering changes
  - frontend display

## Deliverables

- code:
  - new backend clause template service
- tests:
  - focused unit/integration tests for template generation
- docs:
  - none mandatory

## Wave closeout (required in ORCHESTRATOR.md)

- clear:
- fuzzy:
- missing:

