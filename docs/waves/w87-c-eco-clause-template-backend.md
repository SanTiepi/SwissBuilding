# W87-C Eco Clause Template Backend

## Task

- outcome: generate deterministic eco clause templates consumable by pack workflows.
- visible consumer window (`<=2 waves`): immediate follow-up in eco-clause pack integration task.
- done definition (one line): backend service returns structured clause blocks with provenance expectations.

## Agent usage

- `Tu peux utiliser tes agents si pertinent, notamment pour service backend + tests cibles.`

## Scope

- in scope:
  - implement eco clause template service
  - define output contract for pack integration
  - add targeted backend tests
- out of scope:
  - router hub edits
  - frontend rendering

## Target files

- primary file(s):
  - `backend/app/services/eco_clause_template_service.py`
- satellites:
  - `backend/app/services/authority_pack_service.py`
  - `backend/tests/test_eco_clause_template_service.py`
- change mode:
  - `new`:
    - `backend/app/services/eco_clause_template_service.py`
    - `backend/tests/test_eco_clause_template_service.py`
  - `modify`:
    - optional minimal wiring in `authority_pack_service.py`
- do-not-touch:
  - `backend/app/api/router.py`
  - `backend/app/schemas/__init__.py`
  - `backend/app/models/__init__.py`

## Hard constraints

- deterministic output for same input context
- include evidence/provenance expectations in clause payload
- no external scraping/fetch dependencies

## Validate loop

- run -> fix -> rerun until clean:
  - yes
- commands:
  - `cd backend && ruff check app/ tests/`
  - `cd backend && ruff format --check app/ tests/`
  - `cd backend && python -m pytest tests/test_eco_clause_template_service.py -q`
- acceptance evidence:
  - example payload for at least two intervention contexts

## Exit

- functional:
  - eco clause template service exists and produces structured contract output
- validation:
  - commands green
- orchestrator updates:
  - set W87-C status + debrief lines

