# W86-B Skip Link And Main Landmark

## Task

- outcome: implement skip-to-content path with valid focus target in app shell.
- visible consumer window (`<=2 waves`): immediate, fixes W85-A findings `H3/L1`.
- done definition (one line): keyboard user can skip header/sidebar directly to main content.

## Agent usage

- `Tu peux utiliser tes agents si pertinent, notamment pour Layout skip-link + tests e2e/accessibilite.`

## Scope

- in scope:
  - add visible-on-focus skip link in shell
  - ensure `main` has stable skip target (`id` + focusability as needed)
  - add focused e2e checks
- out of scope:
  - navigation structure redesign

## Target files

- primary file(s):
  - `frontend/src/components/Layout.tsx`
- satellites:
  - `frontend/e2e/navigation.spec.ts`
  - `frontend/e2e/pages.spec.ts`
- change mode:
  - `new`:
    - none required
  - `modify`:
    - files above only
- do-not-touch:
  - `frontend/src/i18n/en.ts`
  - `frontend/src/i18n/fr.ts`
  - `frontend/src/i18n/de.ts`
  - `frontend/src/i18n/it.ts`

## Hard constraints

- skip link must be keyboard-discoverable (focus-visible)
- do not break existing layout responsiveness
- no route-level behavioral changes

## Validate loop

- run -> fix -> rerun until clean:
  - yes
- commands:
  - `cd frontend && npm run validate`
  - `cd frontend && npm run test:e2e -- navigation.spec.ts pages.spec.ts`
- acceptance evidence:
  - short proof that Tab from top reaches skip link and focuses main target

## Exit

- functional:
  - skip link works on key flows with deterministic focus transfer
- validation:
  - commands green
- orchestrator updates:
  - set W86-B status + debrief lines

