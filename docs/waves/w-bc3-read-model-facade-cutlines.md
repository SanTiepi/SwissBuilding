# W-BC3 Read Model & Facade Cutlines

## Mission

- business outcome: Extend existing read-model schemas with new domain sections (ownership, occupancy, financial, insurance) and define adapter interfaces that prove current APIs stay stable behind the BatiConnect canonical architecture.
- user/problem context: Current PassportSnapshot, ReadinessState, PortfolioSummary, and Completeness schemas cover only the pollutant/diagnostic domain. Extending them with optional fields for ownership, lease, contract, insurance, and financial data prepares the projection layer for full BatiConnect intelligence without breaking existing consumers.
- visible consumer window (`<=2 waves`): Extended schemas become immediately consumable by frontend once models and services are wired in future phases. Adapter interfaces document guarantees for existing API stability.

## Agent usage

- `Tu peux utiliser tes agents si pertinent, notamment pour l'extension des schemas et la redaction du document d'interfaces adaptateur.`

## Scope

- in scope:
  - Extend PassportSnapshot schema with ownership, occupancy, financial, and insurance sections
  - Extend ReadinessState schema with new domain readiness checks (lease, contract, insurance, financial)
  - Extend PortfolioSummary schema with new domain aggregates (occupancy, financial, insurance)
  - Extend Completeness schema with new completeness checks for BatiConnect domains
  - Create adapter interface specification document
- out of scope:
  - SQLAlchemy model changes
  - Alembic migrations
  - FastAPI route changes
  - Service implementation changes
  - Frontend changes
  - Hub-file wiring

## Target files

- primary file(s):
  - `backend/app/schemas/passport.py` (modify -- add optional ownership/occupancy/financial/insurance sections)
  - `backend/app/schemas/readiness.py` (modify -- add optional new domain checks)
  - `backend/app/schemas/portfolio_summary.py` (modify -- add optional new domain aggregates)
  - `backend/app/schemas/completeness.py` (modify -- add optional new completeness checks)
  - `docs/blueprints/baticonnect-adapter-interfaces.md` (new)
- satellites:
  - none
- change mode:
  - `new`: `docs/blueprints/baticonnect-adapter-interfaces.md`
  - `modify`: `backend/app/schemas/passport.py`, `backend/app/schemas/readiness.py`, `backend/app/schemas/portfolio_summary.py`, `backend/app/schemas/completeness.py`
- hub-file ownership:
  - `supervisor_merge`: `backend/app/schemas/__init__.py`
  - `agent_allowed`: all files listed in primary
- do-not-touch:
  - `backend/app/schemas/__init__.py`
  - `backend/app/models/__init__.py`
  - `backend/app/api/router.py`

## Non-negotiable constraints

- data/model constraints:
  - all new fields on existing schemas must be Optional with None default (backward-compatible)
  - no removal or type change of existing fields
  - read models remain derived projections -- no write-side truth in projection schemas
  - adapter interfaces must prove zero breaking changes to existing API contracts
- technical constraints:
  - Pydantic v2 BaseModel
  - existing tests must continue to pass unchanged
  - new fields use types from W-BC1 and W-BC2 schema contracts
- repo conventions to preserve:
  - ruff check + ruff format must pass
  - no hub-file modifications
  - additive-only schema changes

## Validation

- validation type:
  - `canonical_integration`: extended schemas must be backward-compatible with existing tests
  - `targeted_unit_api`: new fields validate correctly
- commands to run:
  - `cd backend && ruff check app/schemas/passport.py app/schemas/readiness.py app/schemas/portfolio_summary.py app/schemas/completeness.py`
  - `cd backend && ruff format --check app/schemas/passport.py app/schemas/readiness.py app/schemas/portfolio_summary.py app/schemas/completeness.py`
  - `cd backend && python -m pytest tests/ -q`
  - `python scripts/brief_lint.py --strict-diff docs/waves/w-bc3-read-model-facade-cutlines.md`
- required test level:
  - all existing backend tests pass (4563+ tests)
  - ruff clean on modified files
- acceptance evidence to report:
  - ruff check 0 errors
  - full backend test suite passes with 0 failures
  - adapter interface document complete
  - no breaking API changes documented

## Exit criteria

- functional:
  - 4 extended schema modules (passport, readiness, portfolio_summary, completeness)
  - 1 adapter interface specification document
- quality/reliability:
  - ruff check + format clean
  - all existing tests pass
  - brief_lint passes
- docs/control-plane updates:
  - update W-BC3 status in ORCHESTRATOR.md

## Non-goals

- explicitly not part of this brief:
  - SQLAlchemy model changes
  - service implementation changes
  - FastAPI route changes
  - frontend changes
  - projection computation implementation

## Deliverables

- code:
  - `backend/app/schemas/passport.py` (extended)
  - `backend/app/schemas/readiness.py` (extended)
  - `backend/app/schemas/portfolio_summary.py` (extended)
  - `backend/app/schemas/completeness.py` (extended)
- tests: none (additive-only schema extensions, existing tests must pass)
- docs:
  - `docs/blueprints/baticonnect-adapter-interfaces.md`

## Dependencies

- W-BC1 completed (backbone schema contracts referenced by new fields)
- W-BC2 completed (property management schema contracts referenced by new fields)

## Wave closeout (required in ORCHESTRATOR.md)

- clear:
- fuzzy:
- missing:
