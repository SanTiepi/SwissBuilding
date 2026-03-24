# BatiConnect Build Order

> Locked implementation sequence for BatiConnect canonical architecture.
> Each layer builds on the previous. Current codebase (46 models, 4563 tests) stays stable throughout.

---

## Implementation Doctrine

- All new FKs on existing tables: `nullable=True`, no breaking changes
- All new tables created with `CREATE TABLE` migrations, no drops
- Current Building-centric APIs stay stable behind adapter facades
- Test strategy: existing 4563 tests must pass at every layer
- RBAC: new resources added incrementally per layer
- Naming: write-side entities singular (`Contact`, `Lease`), files snake_case (`contact.py`, `lease.py`)
- All UUIDs, all timestamps UTC, all monetary values `_chf` suffix

---

## Layer 0: Foundation

**Objective**: Migration infrastructure + adapter pattern foundation.

### Deliverables
| Item | Type | Path |
|------|------|------|
| ProvenanceMixin | mixin | `backend/app/models/mixins.py` |
| AssetAdapter interface | module | `backend/app/adapters/asset_adapter.py` |
| Adapter base | module | `backend/app/adapters/__init__.py` |
| Migration: empty scaffold | migration | `backend/alembic/versions/005_baticonnect_foundation.py` |

### ProvenanceMixin Implementation
```python
class ProvenanceMixin:
    source_type = Column(String(30), nullable=True)    # import|manual|ai|inferred|official
    confidence = Column(String(20), nullable=True)     # verified|declared|inferred|unknown
    source_ref = Column(String(255), nullable=True)    # external reference
```
Applied to all new L1-L3 models via `class Contact(ProvenanceMixin, Base):`.

### AssetAdapter Pattern
```python
class AssetAdapter:
    """Wraps Building to provide canonical Asset interface."""
    def __init__(self, building: Building): ...
    def to_asset_view(self) -> AssetView: ...
    def with_ownership(self, records: list[OwnershipRecord]) -> AssetView: ...
    def with_leases(self, leases: list[Lease]) -> AssetView: ...
    def with_contracts(self, contracts: list[Contract]) -> AssetView: ...
    def with_financials(self, entries: list[FinancialEntry]) -> AssetView: ...
```

### Gate
- Migration runs clean on existing DB (upgrade + downgrade)
- All 4563 backend tests pass unchanged
- `ruff check app/ tests/` and `ruff format --check app/ tests/` clean
- Mixin importable, adapter instantiable

---

## Layer 1: Canonical Backbone

**Objective**: Party identity, portfolio grouping, ownership records, commercial units.

### New Models (7 tables)

#### Contact (= Party)
- **File**: `backend/app/models/contact.py`
- **Table**: `contacts`
- **Columns**: id (UUID PK), organization_id (FK organizations, nullable), contact_type (String 30, NOT NULL), name (String 255, NOT NULL), company_name (String 255), email (String 255), phone (String 50), address (String 500), postal_code (String 10), city (String 100), canton (String 2), external_ref (String 100), linked_user_id (FK users, nullable), notes (Text), is_active (Boolean default true), source_type (String 30), confidence (String 20), source_ref (String 255), created_by (FK users), created_at, updated_at
- **Constraints**: UNIQUE(email, organization_id) WHERE email IS NOT NULL; UNIQUE(external_ref, organization_id) WHERE external_ref IS NOT NULL

#### PartyRoleAssignment
- **File**: `backend/app/models/party_role_assignment.py`
- **Table**: `party_role_assignments`
- **Columns**: id (UUID PK), party_type (String 30, NOT NULL), party_id (UUID, NOT NULL), entity_type (String 30, NOT NULL), entity_id (UUID, NOT NULL), role (String 50, NOT NULL), share_pct (Float), valid_from (Date), valid_until (Date), is_primary (Boolean default false), notes (Text), created_by (FK users), created_at, updated_at
- **Constraints**: UNIQUE(party_type, party_id, entity_type, entity_id, role)
- **Indexes**: (entity_type, entity_id), (party_type, party_id), (role)

#### Portfolio
- **File**: `backend/app/models/portfolio.py`
- **Table**: `portfolios`
- **Columns**: id (UUID PK), organization_id (FK organizations, NOT NULL), name (String 255, NOT NULL), description (Text), portfolio_type (String 30), is_default (Boolean default false), created_by (FK users), created_at, updated_at
- **Constraints**: UNIQUE(name, organization_id)

#### BuildingPortfolio
- **File**: `backend/app/models/portfolio.py` (same file)
- **Table**: `building_portfolios`
- **Columns**: id (UUID PK), building_id (FK buildings, NOT NULL), portfolio_id (FK portfolios, NOT NULL), added_at (DateTime default now), added_by (FK users)
- **Constraints**: UNIQUE(building_id, portfolio_id)

#### Unit
- **File**: `backend/app/models/unit.py`
- **Table**: `units`
- **Columns**: id (UUID PK), building_id (FK buildings, NOT NULL), unit_type (String 30, NOT NULL), reference_code (String 50, NOT NULL), name (String 255), floor (Integer), surface_m2 (Float), rooms (Float), status (String 20, default 'active'), notes (Text), created_by (FK users), created_at, updated_at
- **Constraints**: UNIQUE(reference_code, building_id)

#### UnitZone
- **File**: `backend/app/models/unit.py` (same file)
- **Table**: `unit_zones`
- **Columns**: id (UUID PK), unit_id (FK units, NOT NULL), zone_id (FK zones, NOT NULL)
- **Constraints**: UNIQUE(unit_id, zone_id)

#### OwnershipRecord
- **File**: `backend/app/models/ownership_record.py`
- **Table**: `ownership_records`
- **Columns**: id (UUID PK), building_id (FK buildings, NOT NULL), owner_type (String 30, NOT NULL), owner_id (UUID, NOT NULL), share_pct (Float), ownership_type (String 30, NOT NULL), acquisition_type (String 30), acquisition_date (Date), disposal_date (Date), acquisition_price_chf (Float), land_register_ref (String 100), status (String 20, default 'active'), document_id (FK documents), notes (Text), source_type (String 30), confidence (String 20), source_ref (String 255), created_by (FK users), created_at, updated_at
- **Indexes**: (building_id), (owner_type, owner_id), (status)

### Existing Model Changes

NOTE: DocumentLink is deferred to Layer 2 (requires Lease/Contract/Insurance consumers).
ORM changes below MUST match migration 006 columns — migration without ORM = broken queries.
| Model | Change | Migration |
|-------|--------|-----------|
| Building | Add `organization_id` UUID FK(organizations.id) NULLABLE | 006 |
| Organization | Add `contact_person_id` UUID FK(contacts.id) NULLABLE | 006 |
| User | Add `linked_contact_id` UUID FK(contacts.id) NULLABLE | 006 |
| Document | Add `content_hash` String(64) NULLABLE | 006 |

### Migrations
- `005_add_backbone_tables.py` -- CREATE TABLE for contacts, party_role_assignments, portfolios, building_portfolios, units, unit_zones, ownership_records
- `006_add_backbone_fks.py` -- ALTER TABLE buildings ADD organization_id, organizations ADD contact_person_id, users ADD linked_contact_id

### New Schemas (Pydantic v2)
| Schema | File |
|--------|------|
| ContactCreate/Read/Update/List | `backend/app/schemas/contact.py` |
| PartyRoleCreate/Read/List | `backend/app/schemas/party_role.py` |
| PortfolioCreate/Read/Update/List | `backend/app/schemas/portfolio.py` |
| UnitCreate/Read/Update/List | `backend/app/schemas/unit.py` |
| OwnershipCreate/Read/Update/List | `backend/app/schemas/ownership.py` |
| PortfolioMetrics (existing) | `backend/app/schemas/portfolio.py` (already exists — add CRUD alongside) |

### New RBAC Resources
| Resource | admin | owner | diagnostician | architect | authority | contractor |
|----------|-------|-------|---------------|-----------|-----------|------------|
| contacts | CRUD+list | R+list(own) | R+list | R+list | R+list | - |
| portfolios | CRUD+list | CRUD+list(own) | R+list | R+list | R+list | - |
| ownership | CRUD+list | R+list(own) | R+list | R+list | R+list | - |
| units | CRUD+list | R+list(own) | R+list | R+list | R+list | - |
| party_roles | CRUD+list | R+list(own) | R+list | R+list | R+list | - |

### New API Routes (5 modules)
| Module | Prefix | Operations |
|--------|--------|------------|
| `backend/app/api/contacts.py` | `/api/v1/contacts` | CRUD + list + search |
| `backend/app/api/party_roles.py` | `/api/v1/party-roles` | CRUD + list by entity + list by party |
| `backend/app/api/portfolios.py` | `/api/v1/portfolios` | CRUD + list + add/remove buildings |
| `backend/app/api/units.py` | `/api/v1/buildings/{id}/units` | CRUD + list + link zones |
| `backend/app/api/ownership.py` | `/api/v1/buildings/{id}/ownership` | CRUD + list |

### Seed Data Extension
- Add 5 demo contacts (owner, tenant, insurer, notary, syndic)
- Add 2 portfolios (Regie Romande portfolio, Demo portfolio)
- Add ownership records for existing demo buildings
- Add 3 units to one demo building
- Maintain idempotent upsert pattern

### Gate
- All 6 new model files exist with correct columns
- CRUD tests for each new entity (minimum 10 tests per entity)
- Compatibility tests proving Building API returns unchanged
- `python -m pytest tests/ -q` passes (existing 4563 + new tests)
- `ruff check app/ tests/` clean
- Seed data runs idempotently

---

## Layer 2: Property Management Core

**Objective**: Lease, contract, insurance, financial, tax, and inventory management.

### New Models (8 tables)

#### Lease
- **File**: `backend/app/models/lease.py`
- **Table**: `leases`
- **Columns**: id (UUID PK), building_id (FK buildings, NOT NULL), unit_id (FK units), zone_id (FK zones), lease_type (String 30, NOT NULL), reference_code (String 50, NOT NULL), tenant_type (String 30, NOT NULL), tenant_id (UUID, NOT NULL), date_start (Date, NOT NULL), date_end (Date), notice_period_months (Integer), rent_monthly_chf (Float), charges_monthly_chf (Float), deposit_chf (Float), surface_m2 (Float), rooms (Float), status (String 20, default 'active'), notes (Text), source_type (String 30), confidence (String 20), source_ref (String 255), created_by (FK users), created_at, updated_at
- **Constraints**: UNIQUE(reference_code, building_id)

#### LeaseEvent
- **File**: `backend/app/models/lease.py` (same file)
- **Table**: `lease_events`
- **Columns**: id (UUID PK), lease_id (FK leases, NOT NULL), event_type (String 30, NOT NULL), event_date (Date, NOT NULL), description (Text), old_value_json (JSON), new_value_json (JSON), document_id (FK documents), created_by (FK users), created_at

#### Contract
- **File**: `backend/app/models/contract.py`
- **Table**: `contracts`
- **Columns**: id (UUID PK), building_id (FK buildings, NOT NULL), contract_type (String 30, NOT NULL), reference_code (String 50, NOT NULL), title (String 500, NOT NULL), counterparty_type (String 30, NOT NULL), counterparty_id (UUID, NOT NULL), date_start (Date, NOT NULL), date_end (Date), annual_cost_chf (Float), payment_frequency (String 20), auto_renewal (Boolean default false), notice_period_months (Integer), status (String 20, default 'active'), notes (Text), source_type (String 30), confidence (String 20), source_ref (String 255), created_by (FK users), created_at, updated_at
- **Constraints**: UNIQUE(reference_code, building_id)

#### InsurancePolicy
- **File**: `backend/app/models/insurance_policy.py`
- **Table**: `insurance_policies`
- **Columns**: id (UUID PK), building_id (FK buildings, NOT NULL), contract_id (FK contracts), policy_type (String 30, NOT NULL), policy_number (String 100, NOT NULL, UNIQUE), insurer_name (String 255, NOT NULL), insurer_contact_id (FK contacts), insured_value_chf (Float), premium_annual_chf (Float), deductible_chf (Float), coverage_details_json (JSON), date_start (Date, NOT NULL), date_end (Date), status (String 20, default 'active'), notes (Text), source_type (String 30), confidence (String 20), source_ref (String 255), created_by (FK users), created_at, updated_at

#### Claim
- **File**: `backend/app/models/claim.py`
- **Table**: `claims`
- **Columns**: id (UUID PK), insurance_policy_id (FK insurance_policies, NOT NULL), building_id (FK buildings, NOT NULL), claim_type (String 30, NOT NULL), reference_number (String 100), status (String 20, NOT NULL, default 'open'), incident_date (Date, NOT NULL), description (Text), claimed_amount_chf (Float), approved_amount_chf (Float), paid_amount_chf (Float), zone_id (FK zones), intervention_id (FK interventions), notes (Text), created_by (FK users), created_at, updated_at

#### FinancialEntry
- **File**: `backend/app/models/financial_entry.py`
- **Table**: `financial_entries`
- **Columns**: id (UUID PK), building_id (FK buildings, NOT NULL), entry_type (String 10, NOT NULL), category (String 50, NOT NULL), amount_chf (Float, NOT NULL), entry_date (Date, NOT NULL), period_start (Date), period_end (Date), fiscal_year (Integer), description (String 500), contract_id (FK contracts), lease_id (FK leases), intervention_id (FK interventions), insurance_policy_id (FK insurance_policies), document_id (FK documents), external_ref (String 100), status (String 20, default 'recorded'), source_type (String 30), confidence (String 20), source_ref (String 255), created_by (FK users), created_at, updated_at
- **Indexes**: (building_id, fiscal_year), (building_id, category), (entry_date)

#### TaxContext
- **File**: `backend/app/models/tax_context.py`
- **Table**: `tax_contexts`
- **Columns**: id (UUID PK), building_id (FK buildings, NOT NULL), tax_type (String 30, NOT NULL), fiscal_year (Integer, NOT NULL), official_value_chf (Float), taxable_value_chf (Float), tax_amount_chf (Float), canton (String 2, NOT NULL), municipality (String 100), status (String 20, default 'estimated'), assessment_date (Date), document_id (FK documents), notes (Text), source_type (String 30), confidence (String 20), source_ref (String 255), created_by (FK users), created_at, updated_at
- **Constraints**: UNIQUE(building_id, tax_type, fiscal_year)

#### InventoryItem
- **File**: `backend/app/models/inventory_item.py`
- **Table**: `inventory_items`
- **Columns**: id (UUID PK), building_id (FK buildings, NOT NULL), zone_id (FK zones), item_type (String 50, NOT NULL), name (String 255, NOT NULL), manufacturer (String 255), model (String 255), serial_number (String 100), installation_date (Date), warranty_end_date (Date), condition (String 20), purchase_cost_chf (Float), replacement_cost_chf (Float), maintenance_contract_id (FK contracts), notes (Text), source_type (String 30), confidence (String 20), source_ref (String 255), created_by (FK users), created_at, updated_at

#### DocumentLink (moved from L1 — needs Lease/Contract consumers)
- **File**: `backend/app/models/document_link.py`
- **Table**: `document_links`
- **Columns**: id (UUID PK), document_id (FK documents, NOT NULL), entity_type (String 50, NOT NULL), entity_id (UUID, NOT NULL), link_type (String 30, NOT NULL), created_by (FK users), created_at
- **Constraints**: UNIQUE(document_id, entity_type, entity_id, link_type)

### Existing Model Changes
| Model | Change | Migration |
|-------|--------|-----------|
| Intervention | Add `contract_id` UUID FK(contracts.id) NULLABLE | 009 |
| Zone | Add `usage_type` String(30) NULLABLE | 009 |
| Document | Add `content_hash` String(64) NULLABLE | 009 |

### Migrations
- `008_add_property_management_tables.py` -- CREATE TABLE for leases, lease_events, contracts, insurance_policies, claims, financial_entries, tax_contexts, inventory_items, document_links
- `009_add_property_management_fks.py` -- ALTER TABLE interventions ADD contract_id, zones ADD usage_type, documents ADD content_hash

### New Schemas (Pydantic v2)
| Schema | File |
|--------|------|
| LeaseCreate/Read/Update/List + LeaseEventCreate/Read | `backend/app/schemas/lease.py` |
| ContractCreate/Read/Update/List | `backend/app/schemas/contract.py` |
| InsurancePolicyCreate/Read/Update/List | `backend/app/schemas/insurance_policy.py` |
| ClaimCreate/Read/Update/List | `backend/app/schemas/claim.py` |
| FinancialEntryCreate/Read/Update/List | `backend/app/schemas/financial_entry.py` |
| TaxContextCreate/Read/Update/List | `backend/app/schemas/tax_context.py` |
| InventoryItemCreate/Read/Update/List | `backend/app/schemas/inventory_item.py` |

### New RBAC Resources
| Resource | admin | owner | diagnostician | architect | authority | contractor |
|----------|-------|-------|---------------|-----------|-----------|------------|
| leases | CRUD+list | CRUD+list(own) | R+list | R+list | R+list(compliance) | - |
| contracts | CRUD+list | CRUD+list(own) | R+list | R+list | R+list(compliance) | R+list(assigned) |
| insurance_policies | CRUD+list | CRUD+list(own) | R+list | R+list | R+list(compliance) | - |
| insurance_claims | CRUD+list | CRUD+list(own) | R+list | R+list | R+list | - |
| financial_entries | CRUD+list | CRUD+list(own) | - | R+list | - | - |
| tax_records | CRUD+list | CRUD+list(own) | - | R+list | R+list | - |
| inventory_items | CRUD+list | CRUD+list(own) | R+list | R+list | R+list | R+list(assigned) |

### New API Routes (7 modules)
| Module | Prefix |
|--------|--------|
| `backend/app/api/leases.py` | `/api/v1/buildings/{id}/leases` |
| `backend/app/api/contracts.py` | `/api/v1/buildings/{id}/contracts` |
| `backend/app/api/insurance_policies.py` | `/api/v1/buildings/{id}/insurance-policies` |
| `backend/app/api/claims.py` | `/api/v1/insurance-policies/{id}/claims` |
| `backend/app/api/financial_entries.py` | `/api/v1/buildings/{id}/financial-entries` |
| `backend/app/api/tax_contexts.py` | `/api/v1/buildings/{id}/tax` |
| `backend/app/api/inventory_items.py` | `/api/v1/buildings/{id}/inventory` |

### Seed Data Extension
- Add 3 demo leases (residential, commercial, parking)
- Add 4 demo contracts (maintenance, cleaning, management, elevator)
- Add 2 demo insurance policies (ECA, RC)
- Add 1 demo claim
- Add 10 demo financial entries (mix of expenses and income)
- Add 2 demo tax contexts
- Add 5 demo inventory items (boiler, elevator, fire system, solar panel, HVAC)

### Gate
- Cross-domain queries work (asset + leases + contracts + financials)
- Seed data extended with demo data, runs idempotently
- All existing 4563+ tests pass
- `ruff check app/ tests/` clean

---

## Layer 3: Orchestration Layer

**Objective**: Obligation tracking, communication threads, AI entities, incident management.

### New Models (7 tables)

#### Obligation
- **File**: `backend/app/models/obligation.py`
- **Table**: `obligations`
- **Columns**: id (UUID PK), building_id (FK buildings, NOT NULL), obligation_type (String 30, NOT NULL), source_type (String 30, NOT NULL), source_id (UUID), title (String 500, NOT NULL), description (Text), due_date (Date, NOT NULL), warning_date (Date), recurrence (String 20), status (String 20, default 'pending'), priority (String 20, default 'medium'), assigned_to_type (String 30), assigned_to_id (UUID), legal_reference (String 255), penalty_description (Text), completed_at (DateTime), completed_by (FK users), created_by (FK users), created_at, updated_at
- **Indexes**: (building_id, due_date), (status), (obligation_type)

#### CommunicationThread
- **File**: `backend/app/models/communication.py`
- **Table**: `communication_threads`
- **Columns**: id (UUID PK), entity_type (String 50, NOT NULL), entity_id (UUID, NOT NULL), subject (String 500, NOT NULL), status (String 20, default 'open'), created_by (FK users), created_at, updated_at
- **Indexes**: (entity_type, entity_id)

#### CommunicationMessage
- **File**: `backend/app/models/communication.py` (same file)
- **Table**: `communication_messages`
- **Columns**: id (UUID PK), thread_id (FK communication_threads, NOT NULL), message_type (String 20, NOT NULL), direction (String 10), sender_name (String 255), sender_email (String 255), recipient_name (String 255), recipient_email (String 255), body (Text, NOT NULL), document_ids_json (JSON), created_by (FK users), created_at

#### Incident
- **File**: `backend/app/models/incident.py`
- **Table**: `incidents`
- **Columns**: id (UUID PK), building_id (FK buildings, NOT NULL), incident_type (String 30, NOT NULL), title (String 500, NOT NULL), description (Text), severity (String 20, NOT NULL), status (String 20, default 'reported'), incident_date (DateTime, NOT NULL), zone_id (FK zones), reported_by (FK users), claim_id (FK claims), intervention_id (FK interventions), notes (Text), created_at, updated_at

#### Recommendation
- **File**: `backend/app/models/recommendation.py`
- **Table**: `recommendations`
- **Columns**: id (UUID PK), building_id (FK buildings, NOT NULL), recommendation_type (String 50, NOT NULL), entity_type (String 50), entity_id (UUID), title (String 500, NOT NULL), rationale (Text, NOT NULL), priority (String 20, default 'medium'), status (String 20, default 'active'), confidence (Float), expires_at (DateTime), accepted_by (FK users), accepted_at (DateTime), created_at

#### AIAnalysis
- **File**: `backend/app/models/ai_analysis.py`
- **Table**: `ai_analyses`
- **Columns**: id (UUID PK), building_id (FK buildings), analysis_type (String 50, NOT NULL), entity_type (String 50), entity_id (UUID), input_snapshot_json (JSON), output_json (JSON), model_version (String 50), confidence (Float), status (String 20, default 'completed'), error_message (Text), created_by (FK users), created_at

#### MemorySignal
- **File**: `backend/app/models/memory_signal.py`
- **Table**: `memory_signals`
- **Columns**: id (UUID PK), building_id (FK buildings), organization_id (FK organizations), signal_type (String 50, NOT NULL), entity_type (String 50), entity_id (UUID), pattern_json (JSON, NOT NULL), frequency (Integer, default 1), last_seen_at (DateTime, NOT NULL), status (String 20, default 'active'), created_at

### Existing Model Changes
| Model | Change | Migration |
|-------|--------|-----------|
| ActionItem | Add `obligation_id` UUID FK(obligations.id) NULLABLE | 010 |

### New Models (Evidence evolution, 2 tables)

#### EvidenceItem
- **File**: `backend/app/models/evidence_item.py`
- **Table**: `evidence_items`
- **Columns**: id (UUID PK), building_id (FK buildings, NOT NULL), evidence_type (String 50, NOT NULL), title (String 500, NOT NULL), description (Text), confidence (Float), source_type (String 30, NOT NULL), source_ref (String 255), legal_reference (String 255), valid_from (DateTime), valid_until (DateTime), created_by (FK users), created_at, updated_at

#### EvidenceRelation
- **File**: `backend/app/models/evidence_item.py` (same file)
- **Table**: `evidence_relations`
- **Columns**: id (UUID PK), evidence_item_id (FK evidence_items, NOT NULL), entity_type (String 50, NOT NULL), entity_id (UUID, NOT NULL), relationship (String 30, NOT NULL), explanation (Text), created_at
- **Constraints**: UNIQUE(evidence_item_id, entity_type, entity_id, relationship)

### Migrations
- `009_add_orchestration_tables.py` -- CREATE TABLE for obligations, communication_threads, communication_messages, incidents, recommendations, ai_analyses, memory_signals, evidence_items, evidence_relations
- `010_add_orchestration_fks.py` -- ALTER TABLE action_items ADD obligation_id

### New Services
| Service | File | Purpose |
|---------|------|---------|
| ObligationAutoGenerator | `backend/app/services/obligation_auto_generator.py` | Generate obligations from contracts (renewal dates, payment deadlines), leases (notice periods, rent reviews), insurance policies (renewal, premium due), regulatory packs (inspection intervals) |
| EvidenceItemAdapter | `backend/app/services/evidence_item_adapter.py` | Bridge between existing EvidenceLink and new EvidenceItem/EvidenceRelation. Read from both, write to new. |

### New RBAC Resources
| Resource | admin | owner | diagnostician | architect | authority | contractor |
|----------|-------|-------|---------------|-----------|-----------|------------|
| obligations | CRUD+list | CRUD+list(own) | R+list | R+list | R+list | R+list(assigned) |
| communications | CRUD+list | CRUD+list(own) | CR+list | R+list | R+list | R+list(assigned) |
| incidents | CRUD+list | CRUD+list(own) | CR+list | R+list | R+list | R+list(assigned) |
| recommendations | CRUD+list | R+list(own) | R+list | R+list | R+list | R+list |
| evidence_items | CRUD+list | CR+list | CR+list | R+list | R+list | R+list |

### Gate
- Obligation calendar populated from seed contracts/leases/insurance
- Communication threads linked to demo building
- ObligationAutoGenerator tested with idempotent upsert
- EvidenceItemAdapter reads both old EvidenceLink and new EvidenceItem seamlessly
- All existing tests pass

---

## Layer 4: Read Models & Projections

**Objective**: Extend existing projections with data from new canonical entities. No new DB tables.

### Extended Schemas (Pydantic only)
| Schema | Change |
|--------|--------|
| PassportSnapshot | Add ownership_summary, occupancy_summary, financial_summary, insurance_summary, inventory_summary sections |
| ReadinessState | Add obligation_check (are all obligations current?), contract_check (all contracts active?), insurance_check (all policies current?) |
| PortfolioSummary | Add aggregate financials (total_income, total_expense, net_yield), aggregate readiness distribution, avg_trust |
| CompletionWorkspace | Add property management completeness checks (has_ownership, has_lease_if_occupied, has_insurance, has_contracts) |

### Extended Services
| Service | Change |
|---------|--------|
| passport_service.py | Include ownership/occupancy/financial data in passport computation |
| completeness_engine.py | Add 8 new completeness checks for property management domains |
| readiness_reasoner.py | Add obligation/contract/insurance checks to readiness evaluation |
| trust_score_calculator.py | Factor in provenance quality from new entities (ownership verified vs declared, lease documented vs stated) |

### BuildingSnapshot Extension
Add 3 nullable JSON columns to `building_snapshots`:
- `ownership_summary_json` -- ownership state at capture time
- `occupancy_summary_json` -- lease/tenant state at capture time
- `financial_summary_json` -- financial position at capture time

Migration: `011_extend_building_snapshot.py`

### Gate
- Read models compute correctly from canonical backbone (not legacy shortcuts)
- Extended passport includes ownership/occupancy/financial when data exists
- Graceful degradation: if no L1-L2 data exists, projections return same as before
- All existing tests pass

---

## Layer 5: Ops Surfaces (Frontend)

**Objective**: Internal professional pages for the new canonical entities.

### New Pages
| Page | Route | Scope |
|------|-------|-------|
| Asset Registry | `/assets` | Portfolio-scoped building list with grouping, filters |
| Party Manager | `/contacts` | Contact CRUD, search, role assignments |
| Ownership Registry | `/buildings/:id/ownership` | Ownership records per building, timeline view |
| Lease Management | `/buildings/:id/leases` | Lease CRUD, event timeline, rent tracker |
| Contract Management | `/buildings/:id/contracts` | Contract CRUD, renewal calendar |
| Insurance Overview | `/buildings/:id/insurance` | Policy list, claims, coverage gaps |
| Financial Workspace | `/buildings/:id/financials` | Ledger view, category breakdown, fiscal year filter |
| Obligation Calendar | `/obligations` | Cross-building calendar view, status tracking |
| Communication Inbox | `/communications` | Thread list, message composer, entity linking |
| Inventory Register | `/buildings/:id/inventory` | Equipment list with maintenance tracking |
| Incident Log | `/buildings/:id/incidents` | Incident CRUD, linked claims/interventions |

### Navigation Changes
- Building detail: add Ownership, Leases, Contracts, Insurance, Financials, Inventory tabs (lazy-loaded)
- Top nav: add Contacts, Portfolios, Obligations, Communications links
- Portfolio selector in header (switch portfolio context)

### Component Library
| Component | Purpose |
|-----------|---------|
| PartyPicker | Autocomplete contact/user/org selector |
| DateRangeFilter | Fiscal year / date range selector for financials |
| ObligationTimeline | Visual timeline of upcoming deadlines |
| FinancialSummaryCard | Income/expense/net summary card |
| CommunicationComposer | Thread message input with document attachment |

### Gate
- Key Ops workflows end-to-end on seeded data
- `npm run validate` clean
- `npm run build` clean
- Building detail pages render new tabs correctly
- No regressions in existing pages

---

## Layer 6: Workspace Surfaces (Frontend)

**Objective**: Client/partner-facing views with audience-scoped content.

### New Pages
| Page | Route | Audience |
|------|-------|----------|
| Owner Dashboard | `/workspace/owner` | Property owners: portfolio overview, financials, obligations, documents |
| Tenant Portal | `/workspace/tenant` | Tenants: lease info, notices, maintenance requests |
| Authority Portal | `/workspace/authority` | Authorities: compliance status, submitted artefacts, diagnostics |
| Regie Dashboard | `/workspace/regie` | Property managers: multi-building overview, obligations, pending actions |
| Insurer View | `/workspace/insurer` | Insurers: risk profile, claims, coverage status |

### Shared Infrastructure
| Item | Purpose |
|------|---------|
| Enhanced SharedView | Audience-scoped section filtering via SharedLink.allowed_sections |
| Workspace Auth | Optional token-based access (SharedLink token) OR authenticated user with workspace role |
| Workspace Layout | Simplified header, no admin nav, audience-branded |

### Gate
- Audience-scoped views render correctly per role
- SharedLink token grants read-only access to allowed sections
- `npm run build` clean
- No admin features visible in workspace surfaces

---

## Layer 7: AI Copilots

**Objective**: Extend AI capabilities to leverage the full canonical entity graph.

### Extended Services
| Service | Change |
|---------|--------|
| dossier_completion_agent | Add property management domain checks (ownership documented?, insurance current?, contracts valid?) |
| campaign_recommender | Factor in obligation deadlines and contract renewals for campaign recommendations |
| recommendation service (new) | Generate recommendations from financial anomalies, expiring contracts, approaching obligations |
| anomaly_detector (new) | Detect unusual patterns in financial entries, lease terms, insurance coverage gaps |

### New AI Capabilities
| Capability | Description |
|-----------|-------------|
| Financial Health Score | Compute financial health from income/expense ratio, reserve adequacy, yield metrics |
| Obligation Compliance Score | Score based on overdue/upcoming obligation ratio |
| Portfolio Intelligence | Cross-building pattern detection (common issues, benchmark comparisons) |
| Predictive Maintenance | Use inventory age/condition + maintenance history to predict replacement timing |

### Gate
- AI references canonical entities (not legacy shortcuts)
- Integration tests for recommendation generation
- All existing tests pass
- Recommendations traceable to source data via EvidenceRelation

---

## Adapter Strategy

### Building -> Asset Adapter

**Current**: `GET /api/v1/buildings/{id}` returns BuildingRead schema.
**New**: `GET /api/v1/assets/{id}` returns AssetView schema wrapping BuildingRead + canonical relations.

```
AssetView = {
    ...BuildingRead fields,
    ownership: list[OwnershipRead],
    leases: list[LeaseRead],
    contracts: list[ContractRead],
    insurance_policies: list[InsurancePolicyRead],
    financial_summary: FinancialSummaryRead,
    portfolio_ids: list[UUID],
    party_roles: list[PartyRoleRead],
}
```

**No data duplication**: same DB row (`buildings` table), different API projection. The adapter fetches related entities via their FKs and composes the view.

**Facade lifecycle**:
1. L0: AssetAdapter interface defined (abstract)
2. L1: AssetAdapter implemented for backbone (ownership, portfolio, party roles)
3. L2: AssetAdapter extended with property management (leases, contracts, financials)
4. L4: AssetView schema includes projection summaries

### User -> Party Bridge
- Users who are also external contacts: `users.linked_contact_id` -> `contacts.id`
- Organizations that are also contacts: `organizations.contact_person_id` -> `contacts.id`
- PartyRoleAssignment accepts `party_type = 'user'` with `party_id = users.id` for backward compat
- No forced migration: existing Assignment model stays for building/diagnostic scopes

---

## Migration Doctrine

### Rules
- Never DROP existing columns or tables
- All new FKs: `nullable=True` with `SET NULL` on delete
- Data backfills in separate migrations (idempotent, safe to re-run)
- Each migration: `upgrade()` + `downgrade()`
- Test: existing SQLite test infrastructure auto-discovers new tables via `Base.metadata`
- Migration IDs: sequential 005, 006, 007... continuing from existing 004

### Migration Sequence
| ID | Name | Layer | Action |
|----|------|-------|--------|
| 005 | baticonnect_foundation | L0 | Create mixins module, adapter module |
| 006 | add_backbone_tables | L1 | CREATE TABLE: contacts, party_role_assignments, portfolios, building_portfolios, units, unit_zones, ownership_records |
| 007 | add_backbone_fks | L1 | ALTER TABLE: buildings.organization_id, organizations.contact_person_id, users.linked_contact_id |
| 008 | add_property_management_tables | L2 | CREATE TABLE: leases, lease_events, contracts, insurance_policies, claims, financial_entries, tax_contexts, inventory_items, document_links |
| 009 | add_property_management_fks | L2 | ALTER TABLE: interventions.contract_id, zones.usage_type, documents.content_hash |
| 010 | add_orchestration_tables | L3 | CREATE TABLE: obligations, communication_threads, communication_messages, incidents, recommendations, ai_analyses, memory_signals, evidence_items, evidence_relations |
| 011 | add_orchestration_fks | L3 | ALTER TABLE: action_items.obligation_id |
| 012 | extend_building_snapshot | L4 | ALTER TABLE: building_snapshots + 3 nullable JSON columns |

---

## RBAC Extension Plan

### Complete Matrix (New Resources by Layer)

| Layer | Resource | admin | owner | diagnostician | architect | authority | contractor |
|-------|----------|-------|-------|---------------|-----------|-----------|------------|
| L1 | contacts | CRUD+list | R+list(own) | R+list | R+list | R+list | - |
| L1 | portfolios | CRUD+list | CRUD+list(own) | R+list | R+list | R+list | - |
| L1 | ownership | CRUD+list | R+list(own) | R+list | R+list | R+list | - |
| L1 | units | CRUD+list | R+list(own) | R+list | R+list | R+list | - |
| L1 | party_roles | CRUD+list | R+list(own) | R+list | R+list | R+list | - |
| L2 | document_links | CRUD+list | CR+list(own) | CR+list | R+list | R+list | R+list |
| L2 | leases | CRUD+list | CRUD+list(own) | R+list | R+list | R+list(compliance) | - |
| L2 | contracts | CRUD+list | CRUD+list(own) | R+list | R+list | R+list(compliance) | R+list(assigned) |
| L2 | insurance_policies | CRUD+list | CRUD+list(own) | R+list | R+list | R+list(compliance) | - |
| L2 | insurance_claims | CRUD+list | CRUD+list(own) | R+list | R+list | R+list | - |
| L2 | financial_entries | CRUD+list | CRUD+list(own) | - | R+list | - | - |
| L2 | tax_records | CRUD+list | CRUD+list(own) | - | R+list | R+list | - |
| L2 | inventory_items | CRUD+list | CRUD+list(own) | R+list | R+list | R+list | R+list(assigned) |
| L3 | obligations | CRUD+list | CRUD+list(own) | R+list | R+list | R+list | R+list(assigned) |
| L3 | communications | CRUD+list | CRUD+list(own) | CR+list | R+list | R+list | R+list(assigned) |
| L3 | incidents | CRUD+list | CRUD+list(own) | CR+list | R+list | R+list | R+list(assigned) |
| L3 | recommendations | CRUD+list | R+list(own) | R+list | R+list | R+list | R+list |
| L3 | evidence_items | CRUD+list | CR+list | CR+list | R+list | R+list | R+list |

### RBAC Implementation Pattern
Follow existing `dependencies.py` pattern:
```python
PERMISSIONS["admin"]["contacts"] = ["create", "read", "update", "delete", "list"]
PERMISSIONS["owner"]["contacts"] = ["read", "list"]
# ... etc
```
Add new resources incrementally per layer. Never remove existing permissions.

---

## Entity Count Summary

| Category | Existing | New (L1) | New (L2) | New (L3) | Total |
|----------|----------|----------|----------|----------|-------|
| Tables | 46 | 8 | 8 | 9 | 71 |
| RBAC resources | 29 | 6 | 7 | 5 | 47 |
| API route modules | 50 | 6 | 7 | 5 | 68 |

### New Tables Per Layer
- **L1 (7)**: contacts, party_role_assignments, portfolios, building_portfolios, units, unit_zones, ownership_records
- **L2 (9)**: leases, lease_events, contracts, insurance_policies, claims, financial_entries, tax_contexts, inventory_items, document_links
- **L3 (9)**: obligations, communication_threads, communication_messages, incidents, recommendations, ai_analyses, memory_signals, evidence_items, evidence_relations

---

## Risk Register

| Risk | Mitigation |
|------|-----------|
| Party/User migration breaks auth | Adapter pattern: Contact coexists with User; bridge service handles dual-write; Assignment stays for backward compat |
| Read-model extensions break existing tests | All new fields Optional/nullable; existing tests unaffected |
| Migration conflicts with active development | Sequential IDs, each with upgrade()+downgrade(); SQLite test infra auto-discovers |
| RBAC matrix explosion | Incremental addition per layer; owner gets CRUD(own) for property management, read-only for others |
| Financial data sensitivity | Financial entries and tax contexts restricted to admin + owner + architect(read); no contractor/diagnostician access |
| Scope creep into premature frontend work | Build order enforces backend-first: L0-L3 (backend) before L5-L6 (frontend) |
| ObligationAutoGenerator creates noise | Idempotent upsert; auto-resolve when source entity changes; configurable generation thresholds |
| EvidenceLink/EvidenceItem dual-write complexity | Adapter pattern; new writes go to EvidenceItem; reads merge both via adapter; eventual migration of old data |
