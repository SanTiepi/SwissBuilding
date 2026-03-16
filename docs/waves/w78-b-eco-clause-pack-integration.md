# W78-B Eco Clause Pack Integration

## Mission

- business outcome: include eco clause blocks in authority/contractor pack outputs.
- user/problem context: generated clauses must be operationalized in exports, not remain backend-only.
- visible consumer window (`<=2 waves`): external pack/dossier surfaces consume this in current milestone flow.

## Agent usage

- `Tu peux utiliser tes agents si pertinent, notamment pour l'integration backend dans les services de pack et tests.`

## Scope

- in scope:
  - integrate W76-C eco clause payload into authority/contractor pack generation
  - ensure output includes clause blocks and evidence requirements
  - add/update tests for pack output sections
- out of scope:
  - router hub changes
  - frontend page redesign

## Target files

- primary file(s):
  - `backend/app/services/authority_pack_service.py` (modify)
- satellites (tests/schemas/routes):
  - `backend/app/services/dossier_service.py` (modify if pack payload composition needs shared wiring)
  - `backend/tests/test_authority_packs.py` (modify/add)
  - `backend/tests/test_dossier.py` or `test_dossier_v2.py` (modify only if output contract touched)
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
  - keep claim-discipline wording in outputs (no legal guarantee language)
- technical constraints:
  - integration must be additive and backward-compatible
  - no new external data dependencies
- repo conventions to preserve:
  - pack generation remains deterministic and traceable

## Validation

- validation type:
  - `canonical_integration`: generated authority/contractor packs include eco clause section
  - `targeted_unit_api`: pack service tests
- commands to run:
  - `cd backend && ruff check app/ tests/`
  - `cd backend && ruff format --check app/ tests/`
  - `cd backend && python -m pytest tests/test_authority_packs.py tests/test_dossier.py -q`
- required test level:
  - targeted pack tests green
- acceptance evidence to report:
  - sample pack payload excerpt containing eco clause block

## Exit criteria

- functional:
  - eco clause blocks appear in generated pack outputs
- quality/reliability:
  - existing pack sections unaffected
- docs/control-plane updates:
  - update W78-B status in `ORCHESTRATOR.md`

## Non-goals

- explicitly not part of this brief:
  - full frontend clause editing UX
  - multilingual clause copy review

## Deliverables

- code:
  - pack service integration with eco clause payload
- tests:
  - pack output assertions
- docs:
  - none mandatory

## Wave closeout (required in ORCHESTRATOR.md)

- clear:
- fuzzy:
- missing:

