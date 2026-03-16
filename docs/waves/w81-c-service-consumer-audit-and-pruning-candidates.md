# W81-C Service Consumer Audit and Pruning Candidates

## Mission

- business outcome: keep backend breadth under control by refreshing service-consumer visibility and pruning candidates.
- user/problem context: after broad feature/productization sweeps, orphan or low-consumer services can accumulate structural debt.
- visible consumer window (`<=2 waves`): immediate; this is rank #3 in current Next 10 and gates future backend expansion.

## Agent usage

- `Tu peux utiliser tes agents si pertinent, notamment pour l'inventaire service-consumer et le rapport de pruning candidates.`

## Scope

- in scope:
  - refresh service-consumer inventory outputs
  - produce explicit pruning candidate list with evidence links
  - flag high-risk hub or duplicate service families for supervisor triage
- out of scope:
  - direct deletion/refactor of production services
  - API behavior changes

## Target files

- primary file(s):
  - `backend/scripts/service_consumer_inventory.py` (modify)
- satellites (tests/schemas/routes):
  - `docs/service-consumer-map.md` (modify/generated)
  - `docs/service-consumer-map.json` (modify/generated)
  - `docs/service-consumer-pruning-candidates.md` (new)
- change mode:
  - `new`:
    - `docs/service-consumer-pruning-candidates.md`
  - `modify`:
    - files listed above only
- hub-file ownership:
  - `supervisor_merge`:
    - `backend/app/api/router.py`
    - `backend/app/models/__init__.py`
    - `backend/app/schemas/__init__.py`
  - `agent_allowed`:
    - files listed in scope
- do-not-touch (hub files reserved to supervisor merge):
  - `backend/app/api/router.py`
  - `backend/app/models/__init__.py`
  - `backend/app/schemas/__init__.py`

## Non-negotiable constraints

- data/model constraints:
  - classify candidates by consumer count and consumer type (API/UI/test/background)
- technical constraints:
  - inventory must be reproducible by command; avoid manual-only conclusions
  - report must separate safe prune candidates vs needs-manual-review candidates
- repo conventions to preserve:
  - no destructive code edits in this audit brief

## Validation

- validation type:
  - `canonical_integration`: inventory command regenerates map artifacts
  - `targeted_unit_api`: n/a unless script tests are added
- commands to run:
  - `python backend/scripts/service_consumer_inventory.py`
  - `cd backend && ruff check scripts/service_consumer_inventory.py`
- required test level:
  - command reproducibility proof
- acceptance evidence to report:
  - updated map file paths
  - count summary (`total_services`, `single_consumer`, `zero_consumer`)
  - pruning candidates grouped by risk

## Exit criteria

- functional:
  - updated inventory + explicit pruning candidate report are committed
- quality/reliability:
  - classification is reproducible and traceable to map artifacts
- docs/control-plane updates:
  - mark W81-C status in `ORCHESTRATOR.md` and add debrief lines

## Non-goals

- explicitly not part of this brief:
  - service removals
  - broad architecture refactors

## Deliverables

- code:
  - refreshed inventory script/output contract (if needed)
- tests:
  - reproducible command run evidence
- docs:
  - pruning candidate report

## Wave closeout (required in ORCHESTRATOR.md)

- clear:
- fuzzy:
- missing:
