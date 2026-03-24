# W-BC2 Ingestion & Projection Contracts

## Mission

- business outcome: Establish Pydantic schema contracts for property management entities and define the ingestion pipeline contract, enabling downstream model/service implementation for lease, contract, insurance, and financial workflows.
- user/problem context: The codebase has no first-class Lease, Contract, InsurancePolicy, FinancialEntry, or TaxContext entities. These schemas define the contract that models, services, and routes will implement. The ingestion contract defines how external data (mail, ERP exports, scanned documents) enters the canonical model.
- visible consumer window (`<=2 waves`): W-BC3 read-model extensions consume these schemas. Frontend lease/contract/financial pages will consume them once models are wired.

## Agent usage

- `Tu peux utiliser tes agents si pertinent, notamment pour la creation des schemas Pydantic et le document de contrat d'ingestion.`

## Scope

- in scope:
  - Lease + LeaseEvent schemas (Create/Read/Update/List variants)
  - Contract schema (Create/Read/Update/List variants)
  - InsurancePolicy schema (Create/Read/Update/List variants)
  - InsuranceClaim schema (Create/Read/Update/List variants)
  - FinancialEntry schema (Create/Read/Update/List variants)
  - TaxRecord schema (Create/Read/Update/List variants)
  - InventoryItem schema (Create/Read/Update/List variants)
  - Ingestion pipeline contract document
- out of scope:
  - SQLAlchemy models
  - Alembic migrations
  - FastAPI route modules
  - Hub-file wiring
  - Frontend changes
  - Ingestion pipeline implementation

## Target files

- primary file(s):
  - `backend/app/schemas/lease.py` (new)
  - `backend/app/schemas/contract.py` (new)
  - `backend/app/schemas/insurance_policy.py` (new)
  - `backend/app/schemas/insurance_claim.py` (new)
  - `backend/app/schemas/financial_entry.py` (new)
  - `backend/app/schemas/tax_record.py` (new)
  - `backend/app/schemas/inventory_item.py` (new)
  - `docs/blueprints/baticonnect-ingestion-contract.md` (new)
- satellites:
  - none
- change mode:
  - `new`: all 8 files above
  - `modify`: none
- hub-file ownership:
  - `supervisor_merge`: `backend/app/schemas/__init__.py`
  - `agent_allowed`: all files listed in primary
- do-not-touch:
  - `backend/app/schemas/__init__.py`
  - `backend/app/models/__init__.py`
  - `backend/app/api/router.py`

## Non-negotiable constraints

- data/model constraints:
  - all schemas use UUID primary keys
  - all fields from domain blueprint (`docs/blueprints/baticonnect-domain-blueprint.md`)
  - Lease.lease_type: residential | commercial | mixed | parking | storage
  - Lease.status: active | terminated | pending
  - Contract.contract_type: maintenance | renovation | management_mandate | cleaning | security | energy | elevator | other
  - InsurancePolicy.policy_type: building_rc | natural_hazard | construction | liability | rent_loss | legal_protection
  - Claim.status: open | under_review | approved | rejected | settled | closed
  - FinancialEntry.entry_type: charge | payment | investment | subsidy | tax | fee | penalty
  - source_document_id: UUID | None on all evidenceable entities
- technical constraints:
  - Pydantic v2 BaseModel
  - follow existing schema patterns and W-BC1 conventions
  - monetary values as Decimal with _chf suffix
  - ingestion contract defines interface specs, not implementation
- repo conventions to preserve:
  - snake_case file names
  - ruff check + ruff format must pass
  - no hub-file modifications

## Validation

- validation type:
  - `targeted_unit_api`: schema validation only
- commands to run:
  - `cd backend && ruff check app/schemas/lease.py app/schemas/contract.py app/schemas/insurance_policy.py app/schemas/insurance_claim.py app/schemas/financial_entry.py app/schemas/tax_record.py app/schemas/inventory_item.py`
  - `cd backend && ruff format --check app/schemas/lease.py app/schemas/contract.py app/schemas/insurance_policy.py app/schemas/insurance_claim.py app/schemas/financial_entry.py app/schemas/tax_record.py app/schemas/inventory_item.py`
  - `python scripts/brief_lint.py --strict-diff docs/waves/w-bc2-ingestion-projection-contracts.md`
- required test level:
  - ruff clean on all new schema files
- acceptance evidence to report:
  - ruff check 0 errors
  - schema files contain all fields from domain blueprint
  - ingestion contract document complete

## Exit criteria

- functional:
  - 7 new schema modules with Create/Read/Update/List variants
  - 1 ingestion pipeline contract document
- quality/reliability:
  - ruff check + format clean
  - brief_lint passes
- docs/control-plane updates:
  - update W-BC2 status in ORCHESTRATOR.md

## Non-goals

- explicitly not part of this brief:
  - SQLAlchemy model creation
  - Alembic migrations
  - FastAPI route wiring
  - ingestion pipeline implementation
  - frontend components

## Deliverables

- code:
  - `backend/app/schemas/lease.py`
  - `backend/app/schemas/contract.py`
  - `backend/app/schemas/insurance_policy.py`
  - `backend/app/schemas/insurance_claim.py`
  - `backend/app/schemas/financial_entry.py`
  - `backend/app/schemas/tax_record.py`
  - `backend/app/schemas/inventory_item.py`
- tests: none (schema-only wave)
- docs:
  - `docs/blueprints/baticonnect-ingestion-contract.md`

## Dependencies

- W-BC1 completed (backbone schemas exist as reference for foreign key patterns)

## Wave closeout (required in ORCHESTRATOR.md)

- clear:
- fuzzy:
- missing:
