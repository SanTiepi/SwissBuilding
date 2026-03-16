# W78-C Safe-to-Start Gate Proof Refresh

## Mission

- business outcome: refresh external gate proof after W76-W78 feature additions.
- user/problem context: new trigger/PFAS/eco-clause surfaces must be proven in real e2e and evidence bundle.
- visible consumer window (`<=2 waves`): immediate external milestone and demo usage.

## Agent usage

- `Aucun agent n'est necessaire pour cette tache.`

## Scope

- in scope:
  - run gate bot in execution mode
  - capture/refresh real screenshot audit evidence
  - generate proof bundle artifact
  - summarize PASS/FAIL with failed checks if any
- out of scope:
  - feature implementation
  - broad refactors

## Target files

- primary file(s):
  - `tmp/safe_to_start_gate_result.json` (generate)
- satellites (tests/schemas/routes):
  - `tmp/safe_to_start_gate_logs/*` (generate)
  - `artifacts/gates/safe-to-start/<timestamp>/*` (generate)
  - `ORCHESTRATOR.md` (modify only for wave status + debrief)
- change mode:
  - `new`:
    - generated artifacts only
  - `modify`:
    - `ORCHESTRATOR.md` status/debrief lines only
- hub-file ownership:
  - `supervisor_merge`:
    - not applicable
  - `agent_allowed`:
    - command execution and artifact generation
- do-not-touch (hub files reserved to supervisor merge):
  - `backend/app/api/router.py`
  - `backend/app/models/__init__.py`
  - `backend/app/schemas/__init__.py`
  - `frontend/src/i18n/en.ts`
  - `frontend/src/i18n/fr.ts`
  - `frontend/src/i18n/de.ts`
  - `frontend/src/i18n/it.ts`

## Non-negotiable constraints

- data/model constraints:
  - evidence must be from real e2e path, not mocked e2e
- technical constraints:
  - preflight must pass before real e2e execution
  - bundle generation must reference latest gate JSON
- repo conventions to preserve:
  - clearly separate real vs mock validation claims

## Validation

- validation type:
  - `canonical_integration`: gate bot run with real command execution
  - `targeted_unit_api`: not applicable
- commands to run:
  - `npm run gate:safe-to-start`
  - `npm run gate:safe-to-start:bundle -- --strict-pass`
- required test level:
  - real e2e/preflight path included in gate execution
- acceptance evidence to report:
  - gate verdict JSON path
  - proof bundle directory path
  - failed checks list if verdict is not PASS

## Exit criteria

- functional:
  - fresh gate report + bundle artifacts are generated
- quality/reliability:
  - PASS verdict, or explicit FAIL with actionable failed checks
- docs/control-plane updates:
  - W78-C status and debrief in `ORCHESTRATOR.md`

## Non-goals

- explicitly not part of this brief:
  - feature development
  - redesign of gate scripts

## Deliverables

- code:
  - none
- tests:
  - real gate run evidence
- docs:
  - control-plane status/debrief update only

## Wave closeout (required in ORCHESTRATOR.md)

- clear:
- fuzzy:
- missing:

