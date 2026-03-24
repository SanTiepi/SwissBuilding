# W-BC1 Canonical Backbone — Schemas + Models + Migration + Adapter

## Mission

- business outcome: Implement the canonical backbone (Party, Portfolio, Unit, Ownership) as runnable SQLAlchemy models with migration, Pydantic schemas, and Building→Asset adapter — so downstream waves can build on real tables, not paper contracts.
- user/problem context: The current codebase has 46 building/pollutant-focused models but lacks Party, Portfolio, Unit, and Ownership as first-class entities. This wave delivers the physical backbone that all BatiConnect extensions plug into.
- visible consumer window (`<=2 waves`): W-BC2 (Lease, Contract, Insurance, Financial models) depends on these tables existing. Frontend ownership/party views consume schemas+routes in W-BC2/BC3.

## Agent usage

- `Tu peux utiliser tes agents si pertinent, notamment pour les modeles SQLAlchemy, schemas Pydantic, migration Alembic, et tests backend.`

## Scope

- in scope:
  - Pydantic v2 schemas (Create/Read/Update/List variants) for all backbone entities
  - SQLAlchemy model skeletons for all backbone entities
  - Alembic migration creating all new tables + nullable FK additions to existing models
  - ProvenanceMixin shared mixin
  - Building→Asset adapter hook (AssetView schema composing BuildingRead + new relations)
  - Compatibility mapping document (current API → canonical entity mapping)
  - Backend tests: model CRUD, schema validation, migration up/down
- out of scope:
  - FastAPI route modules (deferred to post-BC1 supervisor wiring)
  - Hub-file wiring (models/__init__.py, schemas/__init__.py, router.py)
  - DocumentLink model/schema (deferred to BC2 — no multi-document consumers until Lease/Contract exist)
  - Frontend changes
  - Seed data changes (deferred to BC2)

## Target files

- primary file(s):
  - `backend/app/schemas/contact.py` (new — Contact/Party schema)
  - `backend/app/schemas/party_role.py` (new — PartyRoleAssignment schema)
  - `backend/app/schemas/portfolio.py` (modify — add Portfolio + BuildingPortfolio CRUD schemas alongside existing PortfolioMetrics)
  - `backend/app/schemas/unit.py` (new — Unit + UnitZone schema)
  - `backend/app/schemas/ownership.py` (new — OwnershipRecord schema)
  - `backend/app/models/contact.py` (new — Contact SQLAlchemy model)
  - `backend/app/models/party_role_assignment.py` (new — PartyRoleAssignment model)
  - `backend/app/models/portfolio.py` (new — Portfolio model)
  - `backend/app/models/building_portfolio.py` (new — BuildingPortfolio junction model)
  - `backend/app/models/unit.py` (new — Unit model)
  - `backend/app/models/unit_zone.py` (new — UnitZone junction model)
  - `backend/app/models/ownership_record.py` (new — OwnershipRecord model)
  - `backend/app/models/mixins.py` (new — ProvenanceMixin)
  - `backend/alembic/versions/005_add_backbone_tables.py` (new — migration)
  - `backend/alembic/versions/006_add_backbone_fks_to_existing.py` (new — FK additions)
- satellites (tests/docs):
  - `backend/tests/test_backbone_models.py` (new — CRUD tests)
  - `backend/tests/test_backbone_schemas.py` (new — schema validation tests)
  - `docs/blueprints/baticonnect-compatibility-mapping.md` (new)
- existing model files modified (add nullable FK columns + relationships to match migration 006):
  - `backend/app/models/building.py` (modify — add `organization_id` Column + relationship)
  - `backend/app/models/organization.py` (modify — add `contact_person_id` Column + relationship)
  - `backend/app/models/user.py` (modify — add `linked_contact_id` Column + relationship)
- change mode:
  - `new`: all new files listed above
  - `modify`: `backend/app/schemas/portfolio.py`, `backend/app/models/building.py`, `backend/app/models/organization.py`, `backend/app/models/user.py`
- hub-file ownership:
  - `supervisor_merge`:
    - `backend/app/models/__init__.py`
    - `backend/app/schemas/__init__.py`
    - `backend/app/api/router.py`
  - `agent_allowed`: all files listed in primary + satellites + existing model files listed in modify
- do-not-touch:
  - `backend/app/models/__init__.py`
  - `backend/app/schemas/__init__.py`
  - `backend/app/api/router.py`
  - `backend/app/seeds/seed_data.py`

## Non-negotiable constraints

STRICT BLUEPRINT ALIGNMENT — all enums, field names, and types below are canonical.

All enums, field names, and types below are canonical and come from `docs/blueprints/baticonnect-domain-blueprint.md`. Do NOT simplify, rename, or narrow.

### Contact (= Party)

- table: `contacts`
- file field name: `contact_type` (NOT `party_type`)
- `contact_type` values: `person | company | authority | notary | insurer | syndic | supplier`
- additional fields: name, company_name, email, phone, address, postal_code, city, canton, external_ref, linked_user_id (FK users), notes, is_active
- ProvenanceMixin: source_type, confidence, source_ref
- identity: `(email, organization_id)` unique when email set; `external_ref` unique per org when set

### PartyRoleAssignment

- table: `party_role_assignments`
- `party_type` values: `contact | user | organization`
- `entity_type` values (NOT `target_type`): `building | unit | portfolio | lease | contract | intervention | diagnostic`
- `role` values: `legal_owner | co_owner | tenant | manager | insurer | contractor | notary | trustee | syndic | architect | diagnostician | reviewer`
- additional fields: share_pct (Float nullable), valid_from (Date), valid_until (Date), is_primary (Boolean), notes
- unique constraint: `(party_type, party_id, entity_type, entity_id, role)`

### Portfolio

- table: `portfolios`
- `portfolio_type` values: `management | ownership | diagnostic | campaign | custom`
- additional fields: name, description, is_default, organization_id (FK), created_by (FK)
- identity: `(name, organization_id)` unique

### BuildingPortfolio (junction)

- table: `building_portfolios`
- fields: building_id (FK), portfolio_id (FK), added_at, added_by (FK)
- unique: `(building_id, portfolio_id)`

### Unit

- table: `units`
- `unit_type` values: `residential | commercial | parking | storage | office | common_area`
- `status` values: `active | vacant | renovating | decommissioned`
- additional fields: reference_code, name, floor, surface_m2, rooms (Float), notes, building_id (FK), created_by (FK)
- identity: `(reference_code, building_id)` unique

### UnitZone (junction)

- table: `unit_zones`
- fields: unit_id (FK), zone_id (FK)
- unique: `(unit_id, zone_id)`

### OwnershipRecord

- table: `ownership_records`
- `owner_type` values: `contact | user | organization`
- `ownership_type` values: `full | co_ownership | usufruct | bare_ownership | ppe_unit`
- `acquisition_type` values: `purchase | inheritance | donation | construction | exchange`
- `status` values: `active | transferred | disputed | archived`
- additional fields: share_pct, acquisition_date, disposal_date, acquisition_price_chf, land_register_ref, document_id (FK documents), notes
- ProvenanceMixin: source_type, confidence, source_ref

### ProvenanceMixin

- shared SQLAlchemy mixin class in `backend/app/models/mixins.py`
- fields: source_type String(30) nullable, confidence String(20) nullable, source_ref String(255) nullable
- `source_type` values: `import | manual | ai | inferred | official`
- `confidence` values: `verified | declared | inferred | unknown`

### Migration 005: backbone tables

- CREATE tables: contacts, party_role_assignments, portfolios, building_portfolios, units, unit_zones, ownership_records
- All with UUID PKs, created_at/updated_at timestamps
- Indexes as specified in blueprint (section 2)
- Unique constraints as specified above

### Migration 006: FK additions to existing models

- `buildings.organization_id` UUID FK(organizations.id) NULLABLE
- `organizations.contact_person_id` UUID FK(contacts.id) NULLABLE
- `users.linked_contact_id` UUID FK(contacts.id) NULLABLE
- All nullable, no data backfill in this migration

IMPORTANT: Each migration column addition MUST have a matching ORM change:
- `backend/app/models/building.py`: add `organization_id = Column(UUID, ForeignKey("organizations.id"), nullable=True)` + `organization = relationship("Organization", ...)`
- `backend/app/models/organization.py`: add `contact_person_id = Column(UUID, ForeignKey("contacts.id"), nullable=True)` + `contact_person = relationship("Contact", ...)`
- `backend/app/models/user.py`: add `linked_contact_id = Column(UUID, ForeignKey("contacts.id"), nullable=True)` + `linked_contact = relationship("Contact", ...)`
Without these ORM changes, SQLAlchemy won't know about the columns and queries will break.

### Building → Asset adapter

- `backend/app/schemas/asset_view.py` (new): AssetView schema composing BuildingRead + ownership_records + units + portfolios
- This is the compatibility hook that lets future canonical consumers read Building as Asset

### Technical constraints

- all models use UUID PKs with `uuid.uuid4` default
- Pydantic v2 BaseModel (not SQLModel)
- follow existing schema patterns (Create/Read/Update/List variants)
- follow existing model patterns (from app.database import Base)
- monetary values as Float with `_chf` suffix (existing convention)
- timestamps as DateTime with `func.now()` defaults
- all FK columns: nullable=True
- ProvenanceMixin: declarative mixin class, NOT inheritance

### Repo conventions

- snake_case file names and table names
- ruff check + ruff format must pass on all new files
- no hub-file modifications by agents

## Validation

- validation type:
  - `targeted_unit_api`: model + schema + migration validation
- commands to run:
  - `cd backend && ruff check app/models/contact.py app/models/party_role_assignment.py app/models/portfolio.py app/models/building_portfolio.py app/models/unit.py app/models/unit_zone.py app/models/ownership_record.py app/models/mixins.py app/schemas/contact.py app/schemas/party_role.py app/schemas/portfolio.py app/schemas/unit.py app/schemas/ownership.py app/schemas/asset_view.py`
  - `cd backend && ruff format --check app/models/contact.py app/models/party_role_assignment.py app/models/portfolio.py app/models/building_portfolio.py app/models/unit.py app/models/unit_zone.py app/models/ownership_record.py app/models/mixins.py app/schemas/contact.py app/schemas/party_role.py app/schemas/portfolio.py app/schemas/unit.py app/schemas/ownership.py app/schemas/asset_view.py`
  - `cd backend && python -m pytest tests/test_backbone_models.py tests/test_backbone_schemas.py -v`
  - `cd backend && python -m pytest tests/ -q` (full suite must still pass — no regressions)
  - `python scripts/brief_lint.py --strict-diff docs/waves/w-bc1-canonical-backbone-contracts.md`
- required test level:
  - ruff clean on all new files
  - backbone tests pass (model CRUD + schema validation)
  - full 4563-test suite passes unchanged
- acceptance evidence to report:
  - ruff check 0 errors
  - new tests pass
  - existing tests pass (no regressions)
  - migration runs up and down cleanly
  - all fields match domain blueprint exactly (auditable via field-by-field comparison)

## Exit criteria

- functional:
  - 7 new SQLAlchemy models + 1 mixin + 5 new schema modules + 1 modified schema module + 1 adapter schema
  - 3 existing models modified (building.py, organization.py, user.py — nullable FK + relationship additions)
  - 2 Alembic migrations (tables + FK additions)
  - backbone CRUD tests + schema validation tests
  - compatibility mapping document
- quality/reliability:
  - ruff check + format clean
  - all new + existing tests pass
  - brief_lint passes
- docs/control-plane updates:
  - update W-BC1 status in ORCHESTRATOR.md
  - compatibility mapping document complete

## Non-goals

- explicitly not part of this brief:
  - FastAPI route creation (supervisor wiring post-wave)
  - Hub-file registration (supervisor merge)
  - DocumentLink model/schema (deferred to W-BC2 — requires Lease/Contract consumers first)
  - EvidenceItem/EvidenceRelation (deferred to W-BC3 — adapter over existing EvidenceLink)
  - Seed data with backbone entities (deferred to W-BC2)
  - Frontend components
  - Data backfill (Building.organization_id backfill deferred to post-merge)

## Deliverables

- code:
  - `backend/app/models/mixins.py` (ProvenanceMixin)
  - `backend/app/models/contact.py`
  - `backend/app/models/party_role_assignment.py`
  - `backend/app/models/portfolio.py`
  - `backend/app/models/building_portfolio.py`
  - `backend/app/models/unit.py`
  - `backend/app/models/unit_zone.py`
  - `backend/app/models/ownership_record.py`
  - `backend/app/schemas/contact.py`
  - `backend/app/schemas/party_role.py`
  - `backend/app/schemas/portfolio.py`
  - `backend/app/schemas/unit.py`
  - `backend/app/schemas/ownership.py`
  - `backend/app/schemas/asset_view.py`
  - `backend/alembic/versions/005_add_backbone_tables.py`
  - `backend/alembic/versions/006_add_backbone_fks_to_existing.py`
- tests:
  - `backend/tests/test_backbone_models.py`
  - `backend/tests/test_backbone_schemas.py`
- docs:
  - `docs/blueprints/baticonnect-compatibility-mapping.md`

## Wave closeout (required in ORCHESTRATOR.md)

- clear: all backbone tables exist, models importable, schemas validated, migration reversible
- fuzzy: adapter pattern may need refinement once routes are wired
- missing: routes, hub-file wiring, seed data (next waves)
