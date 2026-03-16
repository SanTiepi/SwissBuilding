# W76-A Polludoc Trigger Backend Contract

## Mission

- business outcome: expose deterministic pre-work diagnostic trigger signals in readiness payloads.
- user/problem context: managers need clear escalation guidance before works, not only generic readiness status.
- visible consumer window (`<=2 waves`): W76-B trigger card UI consumes this contract immediately.

## Agent usage

- `Tu peux utiliser tes agents si pertinent, notamment pour le service, schemas, et tests backend.`

## Scope

- in scope:
  - extend readiness reasoning output with `prework_trigger` contract
  - include trigger rationale and legal-basis references
  - cover behavior with targeted backend tests
- out of scope:
  - new routes in `backend/app/api/router.py`
  - PFAS-specific logic (reserved for W77-A)

## Target files

- primary file(s):
  - `backend/app/services/readiness_reasoner.py` (modify)
- satellites (tests/schemas/routes):
  - `backend/app/schemas/readiness.py` (modify)
  - `backend/app/api/readiness.py` (modify only if schema wiring needs update)
  - `backend/tests/test_readiness_reasoner.py` (modify)
  - `backend/tests/test_readiness.py` (modify/add targeted assertions)
- change mode:
  - `new`:
    - none required
  - `modify`:
    - files above only
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
  - keep legal-liability discipline (readiness support, no guarantee semantics)
  - keep identifier hygiene (`egid`/`egrid`/`official_id`)
- technical constraints:
  - no breaking change on existing readiness endpoint shape beyond additive fields
  - additive contract must be backward-compatible
- repo conventions to preserve:
  - compact service logic + explicit tests for trigger outcomes

## Validation

- validation type:
  - `canonical_integration`: readiness endpoint response includes trigger contract
  - `targeted_unit_api`: trigger helper behavior and payload assertions
- commands to run:
  - `cd backend && ruff check app/ tests/`
  - `cd backend && ruff format --check app/ tests/`
  - `cd backend && python -m pytest tests/test_readiness_reasoner.py tests/test_readiness.py -q`
- required test level:
  - targeted backend tests must be green
- acceptance evidence to report:
  - sample response payload with `prework_trigger`
  - tests added/updated and pass counts

## Exit criteria

- functional:
  - readiness payload exposes deterministic pre-work trigger summary
- quality/reliability:
  - additive, non-breaking schema update + green targeted tests
- docs/control-plane updates:
  - update W76-A row status in `ORCHESTRATOR.md`

## Non-goals

- explicitly not part of this brief:
  - PFAS pollutant extension
  - frontend rendering

## Deliverables

- code:
  - updated reasoner + schema contract
- tests:
  - focused readiness trigger coverage
- docs:
  - none mandatory

## Wave closeout (required in ORCHESTRATOR.md)

- clear:
- fuzzy:
- missing:

