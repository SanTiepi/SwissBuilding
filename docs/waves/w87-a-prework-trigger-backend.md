# W87-A Prework Trigger Backend Contract

## Task

- outcome: expose deterministic `prework_trigger` contract in readiness payload.
- visible consumer window (`<=2 waves`): immediate consumer in W87-B UI card.
- done definition (one line): readiness API returns additive trigger fields with rationale/legal basis.

## Agent usage

- `Tu peux utiliser tes agents si pertinent, notamment pour readiness_reasoner + schemas + tests backend.`

## Scope

- in scope:
  - extend readiness reasoner output with additive trigger contract
  - update readiness schema/api wiring if needed
  - add targeted backend tests
- out of scope:
  - router hub file edits

## Target files

- primary file(s):
  - `backend/app/services/readiness_reasoner.py`
- satellites:
  - `backend/app/schemas/readiness.py`
  - `backend/app/api/readiness.py`
  - `backend/tests/test_readiness_reasoner.py`
  - `backend/tests/test_readiness.py`
- change mode:
  - `new`:
    - none required
  - `modify`:
    - files above only
- do-not-touch:
  - `backend/app/api/router.py`
  - `backend/app/schemas/__init__.py`
  - `backend/app/models/__init__.py`

## Hard constraints

- additive backward-compatible contract only
- preserve identifier integrity (`egid`/`egrid`/`official_id`)
- no legal-guarantee wording

## Validate loop

- run -> fix -> rerun until clean:
  - yes
- commands:
  - `cd backend && ruff check app/ tests/`
  - `cd backend && ruff format --check app/ tests/`
  - `cd backend && python -m pytest tests/test_readiness_reasoner.py tests/test_readiness.py -q`
- acceptance evidence:
  - example payload snippet containing `prework_trigger`

## Exit

- functional:
  - readiness payload includes deterministic prework trigger info
- validation:
  - commands green
- orchestrator updates:
  - set W87-A status + debrief lines

