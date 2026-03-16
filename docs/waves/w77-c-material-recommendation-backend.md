# W77-C Material Recommendation Evidence Shelf Backend

## Mission

- business outcome: expose evidence-aware material recommendations for intervention planning.
- user/problem context: recommendations must include required evidence hints, not just generic options.
- visible consumer window (`<=2 waves`): W78-A UI shelf consumes this endpoint directly.

## Agent usage

- `Tu peux utiliser tes agents si pertinent, notamment pour service/schemas/api backend et tests.`

## Scope

- in scope:
  - add material recommendation service with evidence requirements
  - expose endpoint under existing interventions API module
  - add focused tests
- out of scope:
  - router hub registration in `backend/app/api/router.py`
  - frontend rendering

## Target files

- primary file(s):
  - `backend/app/services/material_recommendation_service.py` (new)
- satellites (tests/schemas/routes):
  - `backend/app/api/interventions.py` (modify, add endpoint in existing router module)
  - `backend/app/schemas/material_inventory.py` (modify/add response schema if needed)
  - `backend/tests/test_material_recommendation_service.py` (new)
  - `backend/tests/test_interventions.py` (modify/add endpoint coverage)
- change mode:
  - `new`:
    - `backend/app/services/material_recommendation_service.py`
    - `backend/tests/test_material_recommendation_service.py`
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
  - recommendation payload must include explicit evidence expectations and provenance-friendly fields
- technical constraints:
  - endpoint additive under existing interventions API
  - deterministic output for same input context
- repo conventions to preserve:
  - clear separation between recommendation logic and API wiring

## Validation

- validation type:
  - `canonical_integration`: interventions endpoint returns recommendation shelf payload
  - `targeted_unit_api`: service and endpoint tests
- commands to run:
  - `cd backend && ruff check app/ tests/`
  - `cd backend && ruff format --check app/ tests/`
  - `cd backend && python -m pytest tests/test_material_recommendation_service.py tests/test_interventions.py -q`
- required test level:
  - dedicated service tests + endpoint assertions
- acceptance evidence to report:
  - sample recommendation payload with evidence fields

## Exit criteria

- functional:
  - backend endpoint provides evidence-aware material recommendations
- quality/reliability:
  - deterministic responses + green targeted tests
- docs/control-plane updates:
  - update W77-C status in `ORCHESTRATOR.md`

## Non-goals

- explicitly not part of this brief:
  - UI cards/shelf rendering
  - pack export integration

## Deliverables

- code:
  - new service + endpoint wiring in existing API module
- tests:
  - service/endpoint coverage
- docs:
  - none mandatory

## Wave closeout (required in ORCHESTRATOR.md)

- clear:
- fuzzy:
- missing:

