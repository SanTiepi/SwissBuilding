# W77-A PFAS Readiness Backend Extension

## Mission

- business outcome: add PFAS-aware readiness checks with explicit blocker/condition semantics.
- user/problem context: pollutant readiness coverage is incomplete without PFAS.
- visible consumer window (`<=2 waves`): W77-B readiness wallet UI consumes PFAS states immediately.

## Agent usage

- `Tu peux utiliser tes agents si pertinent, notamment pour les ajustements readiness/rules et les tests backend.`

## Scope

- in scope:
  - extend readiness reasoner to include PFAS checks
  - map legal basis metadata through existing rules-pack compatible patterns
  - add/adjust backend tests
- out of scope:
  - new standalone PFAS module family
  - frontend rendering

## Target files

- primary file(s):
  - `backend/app/services/readiness_reasoner.py` (modify)
- satellites (tests/schemas/routes):
  - `backend/app/services/rule_resolver.py` (modify if legal basis resolution needed)
  - `backend/app/schemas/readiness.py` (modify if additive fields required)
  - `backend/tests/test_readiness_reasoner.py` (modify/add)
  - `backend/tests/test_readiness.py` (modify/add)
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
  - keep claim discipline (readiness support, no legal guarantee)
  - additive PFAS checks must coexist with current pollutant checks
- technical constraints:
  - no breaking change for existing readiness consumers
- repo conventions to preserve:
  - explicit tests for blocked/conditional/pass PFAS outcomes

## Validation

- validation type:
  - `canonical_integration`: readiness endpoint can emit PFAS-relevant checks
  - `targeted_unit_api`: reasoner PFAS logic coverage
- commands to run:
  - `cd backend && ruff check app/ tests/`
  - `cd backend && ruff format --check app/ tests/`
  - `cd backend && python -m pytest tests/test_readiness_reasoner.py tests/test_readiness.py -q`
- required test level:
  - updated readiness tests green
- acceptance evidence to report:
  - sample readiness payload showing PFAS checks and legal basis

## Exit criteria

- functional:
  - PFAS checks present in readiness output where relevant
- quality/reliability:
  - no regressions on existing readiness checks
- docs/control-plane updates:
  - update W77-A status in `ORCHESTRATOR.md`

## Non-goals

- explicitly not part of this brief:
  - readiness wallet UI changes
  - new PFAS data ingestion pipeline

## Deliverables

- code:
  - PFAS readiness backend extension
- tests:
  - readiness PFAS coverage
- docs:
  - none mandatory

## Wave closeout (required in ORCHESTRATOR.md)

- clear:
- fuzzy:
- missing:

