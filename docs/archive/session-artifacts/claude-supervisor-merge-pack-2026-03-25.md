# Claude Supervisor Merge Pack

Date de controle: `25 mars 2026`

## Hub files reserved by repo rule

These are the only repo-declared hub files reserved to supervisor merge:

```text
backend/app/api/router.py
backend/app/models/__init__.py
backend/app/schemas/__init__.py
frontend/src/i18n/en.ts
frontend/src/i18n/fr.ts
frontend/src/i18n/de.ts
frontend/src/i18n/it.ts
```

Do not expand this list ad hoc.

## High-conflict but agent-allowed files

These are not hub files, but deserve extra review if touched:

- `backend/app/dependencies.py`
- `frontend/src/App.tsx`
- shared API client files
- shared page-level containers

## Merge order

1. model registration
2. schema registration
3. router registration
4. i18n additions
5. high-conflict but non-hub files

Reason:

- imports and schemas must exist before routes expose them
- i18n should land after feature strings are known

## Merge checklist

### `backend/app/models/__init__.py`

- add imports only for shipped models
- keep order stable and readable
- verify `python -c "from app.models import *"` succeeds

### `backend/app/schemas/__init__.py`

- export only stable schema modules
- do not export half-wired schema families

### `backend/app/api/router.py`

- include only routes whose service and tests are ready
- verify prefix and tags do not collide
- keep route registration grouped and stable

### `frontend/src/i18n/*`

- add all keys in `en`, `fr`, `de`, `it`
- during wave work, fallback allowed: `t(key) || 'inline fallback'`
- final supervisor merge should remove avoidable missing-key debt

## Conflict patterns

- stale hub file from parallel agents
- model added without schema export
- router includes endpoint whose tests are not yet green
- frontend feature wired before translations exist
- RBAC or dependency change merged without targeted auth tests

## Escalate instead of merging when

- a hub file has overlapping edits from multiple unfinished branches
- route prefixes or exports conflict
- model or schema registration would expose a partial feature
- auth behavior changed and targeted auth cluster is not green
- a merge would require reverting unknown user changes

## Closeout checks by change type

### API touched

- route ready
- targeted endpoint tests green
- auth behavior verified
- no partial registration

### Models touched

- migration present if needed
- model import registration ready
- schema registration ready
- targeted model tests green

### Frontend surface touched

- i18n fallback or final keys present
- `npm run validate` green
- loading / error / empty handled

### Seed or demo touched

- seed verify or equivalent targeted proof green
- no non-idempotent seed behavior introduced

## Rule

Supervisor merge is not a formatting pass.
It is the final guard against:

- partial wiring
- bad exposure order
- brittle auth changes
- hub-file drift
