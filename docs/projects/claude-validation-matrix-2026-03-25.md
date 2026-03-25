# Claude Validation Matrix

Date de controle: `25 mars 2026`

Core rule:

- do not run full suites by reflex
- use the smallest loop that produces reliable signal
- clear homogeneous regression clusters before any full rerun

## Matrix by change type

### Model / schema

| Level | Command | When |
|---|---|---|
| Minimal | `cd backend && ruff check app/ tests/` | every edit |
| Targeted | `cd backend && python -m pytest tests/test_<surface>.py -q` | after model logic change |
| Confidence | `cd backend && python scripts/run_local_test_loop.py changed` | before done |
| Full | `cd backend && python -m pytest tests/ -q` | only if schema touches many surfaces |

Evidence:

- ruff clean
- targeted tests green

### Service / API

| Level | Command | When |
|---|---|---|
| Minimal | `cd backend && ruff check app/ tests/` | every edit |
| Targeted | `cd backend && python -m pytest tests/test_<surface>.py -q` | after logic change |
| Confidence | `cd backend && python scripts/run_local_test_loop.py changed` | before done |
| Full | `cd backend && python -m pytest tests/ -q` | only if cross-cutting service |

Evidence:

- targeted service or endpoint tests green
- no new warnings

### Frontend component

| Level | Command | When |
|---|---|---|
| Minimal | `cd frontend && npm run typecheck` | every edit |
| Targeted | `cd frontend && npm run test:changed` | after component logic change |
| Confidence | `cd frontend && npm run test:changed:strict` | before done |
| Full | `cd frontend && npm test` | only if shared component contract changed |

Evidence:

- typecheck clean
- related vitest tests green

### Page flow

| Level | Command | When |
|---|---|---|
| Minimal | `cd frontend && npm run typecheck` | every edit |
| Targeted | `cd frontend && npm run test:changed` | after page edit |
| Confidence | `cd frontend && npm run test:changed:strict` | before done |
| Full | `cd frontend && npm run test:e2e:smoke` | only if navigation or flow changed |

Evidence:

- typecheck clean
- targeted component/page tests green

### Seed / demo

| Level | Command | When |
|---|---|---|
| Minimal | `cd backend && ruff check app/ tests/` | every edit |
| Targeted | `cd backend && python -c "from app.seeds.seed_data import *"` | import smoke |
| Confidence | `cd backend && python -m app.seeds.seed_verify` | before done |
| Full | `cd backend && python -m pytest tests/ -q` | only if seed schema changed widely |

Evidence:

- import smoke passes
- seed verify passes

### Integration contract

| Level | Command | When |
|---|---|---|
| Minimal | `cd backend && ruff check app/ tests/` + `cd frontend && npm run typecheck` | every edit |
| Targeted | `cd backend && python -m pytest tests/test_<surface>.py -q` | after contract change |
| Confidence | `cd backend && python scripts/run_local_test_loop.py confidence` + `cd frontend && npm run test:changed:strict` | before done |
| Full | full backend + `cd frontend && npm test` | only if breaking rename or broad contract shift |

Evidence:

- backend and frontend agree on contract
- both loops green

### Real e2e touch

| Level | Command | When |
|---|---|---|
| Minimal | `cd frontend && npm run test:e2e:real:preflight` | before any real e2e |
| Targeted | `cd frontend && npx playwright test <spec-file> --config playwright.real.config.ts` | after flow change |
| Confidence | `cd frontend && npm run test:e2e:smoke` | before done |
| Full | `cd frontend && npm run test:e2e:real` | only for final proof |

Evidence:

- preflight passes
- changed spec green

### Regression cluster

Use this when failures are homogeneous:

1. identify the common pattern
2. sweep the cluster
3. rerun only the affected files
4. rerun confidence
5. run one full suite at the end

Current example:

- `unauthenticated` assertions expecting `403` while auth layer returns `401`
- sweep aid: `cd backend && python scripts/run_auth_regression_sweep.py scan`
- rewrite obvious cases: `cd backend && python scripts/run_auth_regression_sweep.py rewrite`
- rerun only flagged files: `cd backend && python scripts/run_auth_regression_sweep.py pytest`

Reference:

- [auth-regression-sweep-pack-2026-03-25.md](./auth-regression-sweep-pack-2026-03-25.md)

## Anti-patterns

- running `python -m pytest tests/ -q` after a single file edit
- running `npm test` when `vitest related` covers the change
- running `npm run test:e2e:real` for type-only or schema-only work
- stacking full validation after every micro-edit
- rerunning full suites before a homogeneous failure cluster is closed
