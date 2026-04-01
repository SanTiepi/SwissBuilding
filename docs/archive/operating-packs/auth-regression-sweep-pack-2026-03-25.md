# Auth Regression Sweep Pack

Date de controle: `25 mars 2026`

## Problem

Le cluster backend actuel n'est pas un bug produit diffus.

Le motif principal est:

- l'auth non authentifiee renvoie `401`
- plusieurs tests `unauthenticated / no_auth / requires_auth` attendent encore `403`

Source of truth:

- [dependencies.py](/C:/PROJET%20IA/SwissBuilding/backend/app/dependencies.py)
- `HTTPBearer(auto_error=False)`
- `get_current_user()` construit une `credentials_exception` en `401`

## Hard Rule

Use:

- `401` for missing, invalid, expired, malformed, or nonexistent-user credentials
- `403` for authenticated but forbidden access

Examples that stay `403`:

- inactive user
- wrong role
- forbidden resource
- cross-org or cross-user access
- permission denied after authentication

## Sweep Strategy

1. scan the cluster
2. rewrite only obvious `unauthenticated 403 -> 401` assertions
3. rerun only affected files
4. rerun auth/security confidence cluster
5. run one full suite only at the end

Do not:

- rerun `python -m pytest tests/ -q` before the cluster is closed
- rewrite role/permission tests that still belong to `403`

## Tooling

Script:

- [run_auth_regression_sweep.py](/C:/PROJET%20IA/SwissBuilding/backend/scripts/run_auth_regression_sweep.py)

Commands:

```bash
cd backend
python scripts/run_auth_regression_sweep.py scan
python scripts/run_auth_regression_sweep.py rewrite
python scripts/run_auth_regression_sweep.py pytest
```

Useful variants:

```bash
cd backend
python scripts/run_auth_regression_sweep.py scan --files-only
python scripts/run_auth_regression_sweep.py scan tests/test_search.py tests/test_security.py
python scripts/run_auth_regression_sweep.py pytest tests/test_search.py tests/test_security.py
```

## Minimal Validation Loop

After the rewrite sweep:

```bash
cd backend
python scripts/run_auth_regression_sweep.py pytest
python -m pytest tests/test_security.py tests/test_search.py tests/test_access_control.py -q --tb=line
python scripts/run_local_test_loop.py confidence
```

Only then:

```bash
cd backend
python -m pytest tests/ -q
```

## Decision Table

| Situation | Expected status |
|---|---|
| no auth header | `401` |
| invalid token | `401` |
| expired token | `401` |
| token with nonexistent user | `401` |
| token missing `sub` | `401` |
| inactive user | `403` |
| valid user, wrong role | `403` |
| valid user, forbidden resource | `403` |

## Current Priority Files

These are the first places to recheck when the cluster reappears:

- `tests/test_security.py`
- `tests/test_search.py`
- `tests/test_access_control.py`
- `tests/test_portfolio.py`
- `tests/test_reporting_metrics.py`
- `tests/test_ui_simulation.py`
- any file with test names containing:
  - `unauth`
  - `unauthorized`
  - `requires_auth`
  - `no_auth`
  - `without_auth`
  - `missing_auth`

## Acceptance

- no obvious unauthenticated tests still expect `403`
- role and permission tests still use `403`
- targeted auth/security cluster is green
- confidence loop is green
- one final full backend run confirms the cluster is gone
