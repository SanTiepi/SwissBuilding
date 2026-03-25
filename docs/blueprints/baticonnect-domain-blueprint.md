# BatiConnect Domain Blueprint

> BatiConnect = l'OS de verite, de preuve, de completude et de decision des actifs immobiliers.
> Two surfaces: **BatiConnect Ops** (internal professionals) + **BatiConnect Workspace** (clients/partners).
> Current SwissBuilding codebase (46 models, 150+ API routes, 4563 tests) is the implementation substrate.
> BatiConnect is the product language in strategic artifacts.

---

## 1. Vision Statement

BatiConnect is the operational system of truth, proof, completeness, and decision for real estate assets. It captures the full lifecycle of a building asset -- from pollutant diagnostics through property management to regulatory compliance -- with an unbroken evidence chain.

**Two surfaces**:
- **BatiConnect Ops**: Internal professional workspace for diagnosticians, architects, property managers, administrators. Full CRUD, evidence workflows, compliance orchestration, AI copilots.
- **BatiConnect Workspace**: Client/partner-facing views for owners, tenants, authorities, insurers, contractors. Audience-scoped, read-heavy, shared-link accessible.

**Core invariants**:
- Every fact has provenance (source_type, confidence, source_ref)
- Every mutation has an audit trail (AuditLog)
- Every derived value traces to canonical truth entities (no orphaned projections)
- No uncontrolled polymorphic blobs (explicit junction tables for all cross-entity relations)

---

## 2. Canonical Write-Side Truth Entities

### 2.1 Organization Backbone

#### Organization
- **Purpose**: Legal entity operating on the platform (diagnostic lab, architecture firm, property management, authority, contractor).
- **Table**: `organizations`
- **Key fields**:
  - `id` UUID PK
  - `name` String(255) NOT NULL
  - `type` String(50) NOT NULL -- `diagnostic_lab | architecture_firm | property_management | authority | contractor`
  - `address` String(500), `postal_code` String(10), `city` String(100), `canton` String(2)
  - `phone` String(20), `email` String(255)
  - `suva_recognized` Boolean default false, `fach_approved` Boolean default false
  - `contact_person_id` UUID FK(contacts.id) NULLABLE -- **NEW L1**: primary contact person
  - `created_at` DateTime
- **Aggregate**: Standalone. Members (Users) reference via FK.

#### User
- **Purpose**: Platform account with authentication and RBAC role.
- **Table**: `users`
- **Key fields**:
  - `id` UUID PK
  - `email` String(255) UNIQUE NOT NULL idx
  - `password_hash` String(255) NOT NULL
  - `first_name` String(100) NOT NULL, `last_name` String(100) NOT NULL
  - `role` String(50) NOT NULL -- `admin | owner | diagnostician | architect | authority | contractor`
  - `organization_id` UUID FK(organizations.id) NULLABLE
  - `language` String(2) default `fr`
  - `is_active` Boolean default true
  - `linked_contact_id` UUID FK(contacts.id) NULLABLE -- **NEW L1**: optional link to Contact/Party
  - `created_at`, `updated_at` DateTime
- **Aggregate**: Standalone. References Organization.

#### Contact (= Party)
- **Purpose**: External person or entity NOT a platform user. Canonical contact model for owners, tenants, notaries, insurers, syndics, suppliers.
- **Table**: `contacts`
- **Key fields**:
  - `id` UUID PK
  - `organization_id` UUID FK(organizations.id) NULLABLE -- scoped to org for uniqueness
  - `contact_type` String(30) NOT NULL -- `person | company | authority | notary | insurer | syndic | supplier`
  - `name` String(255) NOT NULL
  - `company_name` String(255) NULLABLE -- if person within company
  - `email` String(255) NULLABLE
  - `phone` String(50) NULLABLE
  - `address` String(500) NULLABLE
  - `postal_code` String(10) NULLABLE, `city` String(100) NULLABLE, `canton` String(2) NULLABLE
  - `external_ref` String(100) NULLABLE -- ERP/external system link
  - `linked_user_id` UUID FK(users.id) NULLABLE -- optional link to platform user
  - `notes` Text NULLABLE
  - `is_active` Boolean default true
  - `source_type` String(30) NULLABLE -- ProvenanceMixin: `import | manual | ai | inferred | official`
  - `confidence` String(20) NULLABLE -- ProvenanceMixin: `verified | declared | inferred | unknown`
  - `source_ref` String(255) NULLABLE -- ProvenanceMixin
  - `created_by` UUID FK(users.id) NULLABLE
  - `created_at`, `updated_at` DateTime
- **Identity**: `(email, organization_id)` unique when email is set; `external_ref` unique per org when set
- **Aggregate**: Party Aggregate root. PartyRoleAssignments reference this.

#### PartyRoleAssignment
- **Purpose**: Who plays what role on which entity. Unified polymorphic role model with scope and validity windows.
- **Table**: `party_role_assignments`
- **Key fields**:
  - `id` UUID PK
  - `party_type` String(30) NOT NULL -- `contact | user | organization`
  - `party_id` UUID NOT NULL -- references contacts.id, users.id, or organizations.id
  - `entity_type` String(30) NOT NULL -- `building | unit | portfolio | lease | contract | intervention | diagnostic`
  - `entity_id` UUID NOT NULL
  - `role` String(50) NOT NULL -- `legal_owner | co_owner | tenant | manager | insurer | contractor | notary | trustee | syndic | architect | diagnostician | reviewer`
  - `share_pct` Float NULLABLE -- ownership share percentage (for co-ownership)
  - `valid_from` Date NULLABLE
  - `valid_until` Date NULLABLE
  - `is_primary` Boolean default false
  - `notes` Text NULLABLE
  - `created_by` UUID FK(users.id) NULLABLE
  - `created_at`, `updated_at` DateTime
- **Indexes**: `(entity_type, entity_id)`, `(party_type, party_id)`, `(role)`
- **Constraint**: `(party_type, party_id, entity_type, entity_id, role)` UNIQUE
- **Aggregate**: Belongs to Party Aggregate.

### 2.2 Asset Layer

#### Building (= Asset, first concrete shape)
- **Purpose**: Canonical operational root for a physical building. Building IS the Asset via adapter -- NO separate Asset table. Future asset types (parcels, infrastructure) would be separate tables sharing PartyRoleAssignment and Portfolio patterns.
- **Table**: `buildings`
- **Key fields** (existing):
  - `id` UUID PK
  - `egrid` String(14) UNIQUE NULLABLE idx -- parcel identifier (Swiss land registry)
  - `egid` Integer UNIQUE NULLABLE idx -- building identifier (Swiss federal register)
  - `official_id` String(20) NULLABLE -- legacy/cantonal identifier
  - `address` String(500) NOT NULL, `postal_code` String(4) NOT NULL, `city` String(100) NOT NULL
  - `canton` String(2) NOT NULL
  - `municipality_ofs` Integer NULLABLE -- OFS commune code
  - `latitude` Float, `longitude` Float, `geom` Geometry(POINT, 4326)
  - `parcel_number` String(50) NULLABLE
  - `construction_year` Integer NULLABLE, `renovation_year` Integer NULLABLE
  - `building_type` String(50) NOT NULL
  - `floors_above` Integer, `floors_below` Integer
  - `surface_area_m2` Float, `volume_m3` Float
  - `owner_id` UUID FK(users.id) NULLABLE -- legacy; superseded by PartyRoleAssignment for new flows
  - `created_by` UUID FK(users.id) NOT NULL
  - `status` String(20) default `active`
  - `source_dataset` String(50) NULLABLE, `source_imported_at` DateTime NULLABLE, `source_metadata_json` JSON NULLABLE
  - `jurisdiction_id` UUID FK(jurisdictions.id) NULLABLE
  - `created_at`, `updated_at` DateTime
- **New fields (L1)**:
  - `organization_id` UUID FK(organizations.id) NULLABLE -- owning organization
- **Indexes**: canton, postal_code, construction_year, geom (GiST)
- **Aggregate**: Asset Aggregate root. Contains Zones, Units, BuildingElements, Materials, TechnicalPlans, PlanAnnotations, InventoryItems.

#### Portfolio
- **Purpose**: Named collection of assets, organization-scoped.
- **Table**: `portfolios`
- **Key fields**:
  - `id` UUID PK
  - `organization_id` UUID FK(organizations.id) NOT NULL
  - `name` String(255) NOT NULL
  - `description` Text NULLABLE
  - `portfolio_type` String(30) NULLABLE -- `management | ownership | diagnostic | campaign | custom`
  - `is_default` Boolean default false -- one default per org
  - `created_by` UUID FK(users.id) NULLABLE
  - `created_at`, `updated_at` DateTime
- **Identity**: `(name, organization_id)` UNIQUE
- **Aggregate**: Portfolio Aggregate root.

#### BuildingPortfolio (junction)
- **Purpose**: Many-to-many between buildings and portfolios.
- **Table**: `building_portfolios`
- **Key fields**:
  - `id` UUID PK
  - `building_id` UUID FK(buildings.id) NOT NULL
  - `portfolio_id` UUID FK(portfolios.id) NOT NULL
  - `added_at` DateTime default now()
  - `added_by` UUID FK(users.id) NULLABLE
- **Constraint**: `(building_id, portfolio_id)` UNIQUE
- **Aggregate**: Belongs to Portfolio Aggregate.

#### Unit
- **Purpose**: Operational/commercial subdivision of a building (apartment, commercial space, parking). Distinct from Zone (physical/diagnostic). A Unit can reference one or more Zones.
- **Table**: `units`
- **Key fields**:
  - `id` UUID PK
  - `building_id` UUID FK(buildings.id) NOT NULL
  - `unit_type` String(30) NOT NULL -- `residential | commercial | parking | storage | office | common_area`
  - `reference_code` String(50) NOT NULL -- e.g., "Apt 3.1", "P-42"
  - `name` String(255) NULLABLE
  - `floor` Integer NULLABLE
  - `surface_m2` Float NULLABLE
  - `rooms` Float NULLABLE -- e.g., 3.5
  - `status` String(20) default `active` -- `active | vacant | renovating | decommissioned`
  - `notes` Text NULLABLE
  - `created_by` UUID FK(users.id) NULLABLE
  - `created_at`, `updated_at` DateTime
- **Identity**: `(reference_code, building_id)` UNIQUE
- **Aggregate**: Belongs to Asset Aggregate.

#### UnitZone (junction)
- **Purpose**: Links Units to their physical Zones.
- **Table**: `unit_zones`
- **Key fields**:
  - `id` UUID PK
  - `unit_id` UUID FK(units.id) NOT NULL
  - `zone_id` UUID FK(zones.id) NOT NULL
- **Constraint**: `(unit_id, zone_id)` UNIQUE

### 2.3 Physical Structure

#### Zone
- **Purpose**: Physical/diagnostic subdivision of a building (floor, room, facade, etc.). Hierarchical.
- **Table**: `zones`
- **Key fields** (existing):
  - `id` UUID PK
  - `building_id` UUID FK(buildings.id) NOT NULL idx
  - `parent_zone_id` UUID FK(zones.id) NULLABLE -- self-referential hierarchy
  - `zone_type` String(30) NOT NULL -- `floor | room | facade | roof | basement | staircase | technical_room | parking | other`
  - `name` String(255) NOT NULL
  - `description` Text NULLABLE
  - `floor_number` Integer NULLABLE
  - `surface_area_m2` Float NULLABLE
  - `created_by` UUID FK(users.id) NULLABLE
  - `created_at`, `updated_at` DateTime
- **New fields (L2)**:
  - `usage_type` String(30) NULLABLE -- `residential | commercial | storage | parking | technical | common`
- **Aggregate**: Belongs to Asset Aggregate.

#### BuildingElement
- **Purpose**: Structural/functional component within a zone (wall, pipe, window, etc.).
- **Table**: `building_elements`
- **Key fields**:
  - `id` UUID PK
  - `zone_id` UUID FK(zones.id) NOT NULL idx
  - `element_type` String(50) NOT NULL -- `wall | floor | ceiling | pipe | insulation | coating | window | door | duct | structural | other`
  - `name` String(255) NOT NULL
  - `description` Text NULLABLE
  - `condition` String(20) NULLABLE -- `good | fair | poor | critical | unknown`
  - `installation_year` Integer NULLABLE
  - `last_inspected_at` DateTime NULLABLE
  - `created_by` UUID FK(users.id) NULLABLE
  - `created_at`, `updated_at` DateTime
- **Aggregate**: Belongs to Asset Aggregate (via Zone).

#### Material
- **Purpose**: Material applied to or composing a building element, with pollutant tracking.
- **Table**: `materials`
- **Key fields**:
  - `id` UUID PK
  - `element_id` UUID FK(building_elements.id) NOT NULL idx
  - `material_type` String(50) NOT NULL -- 15 types: `concrete | fiber_cement | plaster | paint | adhesive | insulation_material | sealant | flooring | tile | wood | metal | glass | bitumen | mortar | other`
  - `name` String(255) NOT NULL
  - `description` Text NULLABLE
  - `manufacturer` String(255) NULLABLE
  - `installation_year` Integer NULLABLE
  - `contains_pollutant` Boolean default false
  - `pollutant_type` String(50) NULLABLE -- `asbestos | pcb | lead | hap | radon`
  - `pollutant_confirmed` Boolean default false
  - `sample_id` UUID FK(samples.id) NULLABLE
  - `source` String(50) NULLABLE -- `diagnostic | visual_inspection | documentation | owner_declaration | import`
  - `notes` Text NULLABLE
  - `created_by` UUID FK(users.id) NULLABLE
  - `created_at` DateTime
- **Aggregate**: Belongs to Asset Aggregate (via Zone > Element).

#### TechnicalPlan
- **Purpose**: Uploaded plan/drawing associated with a building.
- **Table**: `technical_plans`
- **Key fields**:
  - `id` UUID PK
  - `building_id` UUID FK(buildings.id) NOT NULL idx
  - `plan_type` String(50) NOT NULL -- `floor_plan | cross_section | elevation | technical_schema | site_plan | detail | annotation | other`
  - `title` String(500) NOT NULL, `description` Text NULLABLE
  - `floor_number` Integer NULLABLE, `version` String(50) NULLABLE
  - `file_path` String(500) NOT NULL, `file_name` String(255) NOT NULL
  - `mime_type` String(100) NULLABLE, `file_size_bytes` Integer NULLABLE
  - `zone_id` UUID FK(zones.id) NULLABLE
  - `uploaded_by` UUID FK(users.id) NULLABLE
  - `created_at` DateTime
- **Aggregate**: Belongs to Asset Aggregate.

#### PlanAnnotation
- **Purpose**: Positioned annotation on a technical plan, linking to zones/samples/elements.
- **Table**: `plan_annotations`
- **Key fields**:
  - `id` UUID PK
  - `plan_id` UUID FK(technical_plans.id) NOT NULL idx
  - `building_id` UUID FK(buildings.id) NOT NULL idx
  - `x` Float NOT NULL, `y` Float NOT NULL -- 0.0-1.0 relative position
  - `annotation_type` String(30) NOT NULL -- `marker | zone_reference | sample_location | observation | hazard_zone | measurement_point`
  - `label` String(255) NOT NULL, `description` Text NULLABLE
  - `zone_id` UUID FK(zones.id) NULLABLE, `sample_id` UUID FK(samples.id) NULLABLE, `element_id` UUID FK(building_elements.id) NULLABLE
  - `color` String(20) NULLABLE, `icon` String(50) NULLABLE
  - `metadata_json` JSON NULLABLE
  - `created_by` UUID FK(users.id) NULLABLE
  - `created_at`, `updated_at` DateTime
- **Aggregate**: Belongs to Asset Aggregate.

#### InventoryItem
- **Purpose**: Trackable equipment/installation within a building (HVAC, elevator, solar panel, etc.).
- **Table**: `inventory_items`
- **Key fields**:
  - `id` UUID PK
  - `building_id` UUID FK(buildings.id) NOT NULL idx
  - `zone_id` UUID FK(zones.id) NULLABLE
  - `item_type` String(50) NOT NULL -- `hvac | boiler | elevator | fire_system | solar_panel | heat_pump | ventilation | electrical_panel | water_heater | garage_door | intercom | alarm | other`
  - `name` String(255) NOT NULL
  - `manufacturer` String(255) NULLABLE, `model` String(255) NULLABLE, `serial_number` String(100) NULLABLE
  - `installation_date` Date NULLABLE, `warranty_end_date` Date NULLABLE
  - `condition` String(20) NULLABLE -- `good | fair | poor | critical | unknown`
  - `purchase_cost_chf` Float NULLABLE, `replacement_cost_chf` Float NULLABLE
  - `maintenance_contract_id` UUID FK(contracts.id) NULLABLE -- wired in L2
  - `notes` Text NULLABLE
  - `source_type` String(30) NULLABLE, `confidence` String(20) NULLABLE, `source_ref` String(255) NULLABLE -- ProvenanceMixin
  - `created_by` UUID FK(users.id) NULLABLE
  - `created_at`, `updated_at` DateTime
- **Aggregate**: Belongs to Asset Aggregate.

### 2.4 Diagnostic & Evidence

#### Diagnostic
- **Purpose**: Pollutant diagnostic performed on a building.
- **Table**: `diagnostics`
- **Key fields**:
  - `id` UUID PK
  - `building_id` UUID FK(buildings.id) NOT NULL idx
  - `diagnostic_type` String(50) NOT NULL -- `asbestos | pcb | lead | hap | radon | full`
  - `diagnostic_context` String(10) default `AvT` -- `AvT | ApT`
  - `status` String(20) default `draft` -- `draft | in_progress | completed | validated`
  - `diagnostician_id` UUID FK(users.id) NULLABLE
  - `laboratory` String(255), `laboratory_report_number` String(100)
  - `date_inspection` Date, `date_report` Date
  - `report_file_path` String(500) NULLABLE
  - `summary` Text, `conclusion` String(50), `methodology` String(100)
  - `suva_notification_required` Boolean, `suva_notification_date` Date, `canton_notification_date` Date
  - `created_at`, `updated_at` DateTime
- **Aggregate**: Diagnostic Aggregate root. Contains Samples, FieldObservations.

#### Sample
- **Purpose**: Laboratory sample taken during a diagnostic, with concentration/threshold data.
- **Table**: `samples`
- **Key fields**:
  - `id` UUID PK
  - `diagnostic_id` UUID FK(diagnostics.id) NOT NULL idx
  - `sample_number` String(50) NOT NULL
  - `location_floor` String(50), `location_room` String(100), `location_detail` String(255)
  - `material_category` String(100), `material_description` String(255), `material_state` String(50)
  - `pollutant_type` String(50), `pollutant_subtype` String(100)
  - `concentration` Float, `unit` String(20) -- canonical units: `percent_weight | fibers_per_m3 | mg_per_kg | ng_per_m3 | ug_per_l | bq_per_m3`
  - `threshold_exceeded` Boolean default false
  - `risk_level` String(20) -- `low | medium | high | critical | unknown`
  - `cfst_work_category` String(20), `action_required` String(50), `waste_disposal_type` String(20)
  - `notes` Text NULLABLE
  - `created_at` DateTime
- **Aggregate**: Belongs to Diagnostic Aggregate.

#### FieldObservation
- **Purpose**: On-site observation recorded during inspection, optionally linked to zone/element.
- **Table**: `field_observations`
- **Key fields**:
  - `id` UUID PK
  - `building_id` UUID FK(buildings.id) NOT NULL idx
  - `zone_id` UUID FK(zones.id) NULLABLE, `element_id` UUID FK(building_elements.id) NULLABLE
  - `observer_id` UUID FK(users.id) NOT NULL
  - `observation_type` String(30) NOT NULL, `severity` String(20) default `info`
  - `title` String(255) NOT NULL, `description` Text, `location_description` String(500)
  - `observed_at` DateTime NOT NULL, `photo_reference` String(500) NULLABLE
  - `verified` Boolean default false, `verified_by_id` UUID FK(users.id) NULLABLE, `verified_at` DateTime
  - `status` String(20) default `draft`, `metadata_json` Text NULLABLE
  - `created_at`, `updated_at` DateTime
- **Aggregate**: Belongs to Diagnostic Aggregate (loosely coupled via building_id).

#### Document
- **Purpose**: Uploaded file associated with a building. Gains explicit many-to-many via DocumentLink.
- **Table**: `documents`
- **Key fields** (existing):
  - `id` UUID PK
  - `building_id` UUID FK(buildings.id) NOT NULL idx -- legacy direct FK; stays for backward compat
  - `file_path` String(500) NOT NULL, `file_name` String(255) NOT NULL
  - `file_size_bytes` Integer, `mime_type` String(100)
  - `document_type` String(50) NULLABLE
  - `description` String(500) NULLABLE
  - `uploaded_by` UUID FK(users.id) NULLABLE
  - `processing_metadata` JSON NULLABLE -- {virus_scan, ocr}
  - `created_at` DateTime
- **New fields (L1)**:
  - `content_hash` String(64) NULLABLE -- SHA-256 for identity/dedup
- **Identity**: `(content_hash, file_path)` unique pair when content_hash is set
- **Aggregate**: Evidence Aggregate root.

#### DocumentLink (junction)
- **Purpose**: Explicit many-to-many relation between documents and any entity, replacing ad-hoc FKs.
- **Table**: `document_links`
- **Key fields**:
  - `id` UUID PK
  - `document_id` UUID FK(documents.id) NOT NULL
  - `entity_type` String(50) NOT NULL -- `building | diagnostic | intervention | lease | contract | insurance_policy | claim | compliance_artefact | evidence_pack`
  - `entity_id` UUID NOT NULL
  - `link_type` String(30) NOT NULL -- `attachment | report | proof | reference | invoice | certificate`
  - `created_by` UUID FK(users.id) NULLABLE
  - `created_at` DateTime
- **Constraint**: `(document_id, entity_type, entity_id, link_type)` UNIQUE
- **Aggregate**: Belongs to Evidence Aggregate.

#### EvidenceLink (existing, stays during transition)
- **Purpose**: Polymorphic source-to-target evidence chain. Current implementation.
- **Table**: `evidence_links`
- **Key fields**:
  - `id` UUID PK
  - `source_type` String(50) NOT NULL -- `sample | diagnostic | document | pollutant_rule | observation | material | intervention | import | manual`
  - `source_id` UUID NOT NULL
  - `target_type` String(50) NOT NULL -- `risk_score | action_item | recommendation | compliance_result`
  - `target_id` UUID NOT NULL
  - `relationship` String(50) NOT NULL -- `proves | supports | contradicts | requires | triggers | supersedes`
  - `confidence` Float NULLABLE
  - `legal_reference` String(255) NULLABLE
  - `explanation` Text NULLABLE
  - `created_by` UUID FK(users.id) NULLABLE
  - `created_at` DateTime
- **Indexes**: `(source_type, source_id)`, `(target_type, target_id)`, `(relationship)`
- **Transition**: Stays operational. New EvidenceItem + EvidenceRelation introduced alongside with adapter.

#### EvidenceItem (evolution of EvidenceLink)
- **Purpose**: First-class evidence entity with explicit many-to-many relations. Replaces uncontrolled polymorphic source/target pattern.
- **Table**: `evidence_items`
- **Key fields**:
  - `id` UUID PK
  - `building_id` UUID FK(buildings.id) NOT NULL idx
  - `evidence_type` String(50) NOT NULL -- `lab_result | inspection_report | photo | official_document | declaration | import_record | ai_inference`
  - `title` String(500) NOT NULL
  - `description` Text NULLABLE
  - `confidence` Float NULLABLE -- 0.0-1.0
  - `source_type` String(30) NOT NULL -- ProvenanceMixin: `import | manual | ai | inferred | official`
  - `source_ref` String(255) NULLABLE -- ProvenanceMixin
  - `legal_reference` String(255) NULLABLE
  - `valid_from` DateTime NULLABLE, `valid_until` DateTime NULLABLE
  - `created_by` UUID FK(users.id) NULLABLE
  - `created_at`, `updated_at` DateTime
- **Aggregate**: Evidence Aggregate root (coexists with Document).

#### EvidenceRelation
- **Purpose**: Explicit many-to-many between EvidenceItem and any entity.
- **Table**: `evidence_relations`
- **Key fields**:
  - `id` UUID PK
  - `evidence_item_id` UUID FK(evidence_items.id) NOT NULL
  - `entity_type` String(50) NOT NULL
  - `entity_id` UUID NOT NULL
  - `relationship` String(30) NOT NULL -- `proves | supports | contradicts | requires | triggers | supersedes`
  - `explanation` Text NULLABLE
  - `created_at` DateTime
- **Constraint**: `(evidence_item_id, entity_type, entity_id, relationship)` UNIQUE
- **Aggregate**: Belongs to Evidence Aggregate.

### 2.5 Ownership & Occupancy

#### OwnershipRecord
- **Purpose**: Legal ownership records for an asset, with share tracking and land registry reference.
- **Table**: `ownership_records`
- **Key fields**:
  - `id` UUID PK
  - `building_id` UUID FK(buildings.id) NOT NULL idx
  - `owner_type` String(30) NOT NULL -- `contact | user | organization`
  - `owner_id` UUID NOT NULL
  - `share_pct` Float NULLABLE -- percentage of ownership
  - `ownership_type` String(30) NOT NULL -- `full | co_ownership | usufruct | bare_ownership | ppe_unit`
  - `acquisition_type` String(30) NULLABLE -- `purchase | inheritance | donation | construction | exchange`
  - `acquisition_date` Date NULLABLE
  - `disposal_date` Date NULLABLE
  - `acquisition_price_chf` Float NULLABLE
  - `land_register_ref` String(100) NULLABLE -- registre foncier reference
  - `status` String(20) default `active` -- `active | transferred | disputed | archived`
  - `document_id` UUID FK(documents.id) NULLABLE -- proof of ownership document
  - `notes` Text NULLABLE
  - `source_type` String(30) NULLABLE, `confidence` String(20) NULLABLE, `source_ref` String(255) NULLABLE -- ProvenanceMixin
  - `created_by` UUID FK(users.id) NULLABLE
  - `created_at`, `updated_at` DateTime
- **Indexes**: `(building_id)`, `(owner_type, owner_id)`, `(status)`
- **Aggregate**: Standalone (references Asset).

#### Lease
- **Purpose**: Rental/occupancy contract for a unit or zone within a building.
- **Table**: `leases`
- **Key fields**:
  - `id` UUID PK
  - `building_id` UUID FK(buildings.id) NOT NULL idx
  - `unit_id` UUID FK(units.id) NULLABLE -- preferred linkage
  - `zone_id` UUID FK(zones.id) NULLABLE -- fallback for unit-less zones
  - `lease_type` String(30) NOT NULL -- `residential | commercial | mixed | parking | storage | short_term`
  - `reference_code` String(50) NOT NULL
  - `tenant_type` String(30) NOT NULL -- `contact | user | organization`
  - `tenant_id` UUID NOT NULL
  - `date_start` Date NOT NULL
  - `date_end` Date NULLABLE -- null = indefinite
  - `notice_period_months` Integer NULLABLE
  - `rent_monthly_chf` Float NULLABLE
  - `charges_monthly_chf` Float NULLABLE
  - `deposit_chf` Float NULLABLE
  - `surface_m2` Float NULLABLE, `rooms` Float NULLABLE
  - `status` String(20) default `active` -- `draft | active | terminated | expired | disputed`
  - `notes` Text NULLABLE
  - `source_type` String(30) NULLABLE, `confidence` String(20) NULLABLE, `source_ref` String(255) NULLABLE -- ProvenanceMixin
  - `created_by` UUID FK(users.id) NULLABLE
  - `created_at`, `updated_at` DateTime
- **Identity**: `(reference_code, building_id)` UNIQUE
- **Aggregate**: Occupancy Aggregate root.

#### LeaseEvent
- **Purpose**: Significant events during a lease lifecycle (rent changes, renewals, notices).
- **Table**: `lease_events`
- **Key fields**:
  - `id` UUID PK
  - `lease_id` UUID FK(leases.id) NOT NULL
  - `event_type` String(30) NOT NULL -- `creation | renewal | rent_adjustment | notice_sent | notice_received | termination | dispute | deposit_return`
  - `event_date` Date NOT NULL
  - `description` Text NULLABLE
  - `old_value_json` JSON NULLABLE, `new_value_json` JSON NULLABLE
  - `document_id` UUID FK(documents.id) NULLABLE
  - `created_by` UUID FK(users.id) NULLABLE
  - `created_at` DateTime
- **Aggregate**: Belongs to Occupancy Aggregate.

### 2.6 Contractual Layer

#### Contract
- **Purpose**: Service/maintenance agreements between the asset owner/manager and third parties.
- **Table**: `contracts`
- **Key fields**:
  - `id` UUID PK
  - `building_id` UUID FK(buildings.id) NOT NULL idx
  - `contract_type` String(30) NOT NULL -- `maintenance | management_mandate | concierge | cleaning | elevator | heating | insurance | security | energy | other`
  - `reference_code` String(50) NOT NULL
  - `title` String(500) NOT NULL
  - `counterparty_type` String(30) NOT NULL -- `contact | user | organization`
  - `counterparty_id` UUID NOT NULL
  - `date_start` Date NOT NULL
  - `date_end` Date NULLABLE
  - `annual_cost_chf` Float NULLABLE
  - `payment_frequency` String(20) NULLABLE -- `monthly | quarterly | semi_annual | annual`
  - `auto_renewal` Boolean default false
  - `notice_period_months` Integer NULLABLE
  - `status` String(20) default `active` -- `draft | active | suspended | terminated | expired`
  - `notes` Text NULLABLE
  - `source_type` String(30) NULLABLE, `confidence` String(20) NULLABLE, `source_ref` String(255) NULLABLE -- ProvenanceMixin
  - `created_by` UUID FK(users.id) NULLABLE
  - `created_at`, `updated_at` DateTime
- **Identity**: `(reference_code, building_id)` UNIQUE
- **Aggregate**: Contractual Aggregate root.

#### InsurancePolicy
- **Purpose**: Specialized contract for building insurance (ECA, RC, natural hazard, etc.).
- **Table**: `insurance_policies`
- **Key fields**:
  - `id` UUID PK
  - `building_id` UUID FK(buildings.id) NOT NULL idx
  - `contract_id` UUID FK(contracts.id) NULLABLE -- optional link to generic contract
  - `policy_type` String(30) NOT NULL -- `building_eca | rc_owner | rc_building | natural_hazard | construction_risk | complementary | contents`
  - `policy_number` String(100) NOT NULL
  - `insurer_name` String(255) NOT NULL
  - `insurer_contact_id` UUID FK(contacts.id) NULLABLE
  - `insured_value_chf` Float NULLABLE
  - `premium_annual_chf` Float NULLABLE
  - `deductible_chf` Float NULLABLE
  - `coverage_details_json` JSON NULLABLE
  - `date_start` Date NOT NULL, `date_end` Date NULLABLE
  - `status` String(20) default `active` -- `draft | active | suspended | expired | cancelled`
  - `notes` Text NULLABLE
  - `source_type` String(30) NULLABLE, `confidence` String(20) NULLABLE, `source_ref` String(255) NULLABLE -- ProvenanceMixin
  - `created_by` UUID FK(users.id) NULLABLE
  - `created_at`, `updated_at` DateTime
- **Identity**: `(policy_number)` UNIQUE
- **Aggregate**: Belongs to Contractual Aggregate.

#### Claim
- **Purpose**: Insurance claim as child flow of InsurancePolicy.
- **Table**: `claims`
- **Key fields**:
  - `id` UUID PK
  - `insurance_policy_id` UUID FK(insurance_policies.id) NOT NULL
  - `building_id` UUID FK(buildings.id) NOT NULL idx
  - `claim_type` String(30) NOT NULL -- `water_damage | fire | natural_hazard | liability | theft | pollutant_related | other`
  - `reference_number` String(100) NULLABLE
  - `status` String(20) NOT NULL default `open` -- `open | in_review | approved | rejected | settled | closed`
  - `incident_date` Date NOT NULL
  - `description` Text NULLABLE
  - `claimed_amount_chf` Float NULLABLE, `approved_amount_chf` Float NULLABLE, `paid_amount_chf` Float NULLABLE
  - `zone_id` UUID FK(zones.id) NULLABLE
  - `intervention_id` UUID FK(interventions.id) NULLABLE
  - `notes` Text NULLABLE
  - `created_by` UUID FK(users.id) NULLABLE
  - `created_at`, `updated_at` DateTime
- **Aggregate**: Belongs to Contractual Aggregate.

### 2.7 Financial Layer

#### FinancialEntry
- **Purpose**: Unified expense/income ledger for an asset. References originating entities via nullable FKs.
- **Table**: `financial_entries`
- **Key fields**:
  - `id` UUID PK
  - `building_id` UUID FK(buildings.id) NOT NULL idx
  - `entry_type` String(10) NOT NULL -- `expense | income`
  - `category` String(50) NOT NULL -- `rent_income | charges_income | maintenance | repair | renovation | insurance_premium | tax | energy | cleaning | elevator | management_fee | concierge | legal | audit | reserve_fund | interest | mortgage | depreciation | capital_gain | other_income | other_expense`
  - `amount_chf` Float NOT NULL
  - `entry_date` Date NOT NULL
  - `period_start` Date NULLABLE, `period_end` Date NULLABLE
  - `fiscal_year` Integer NULLABLE
  - `description` String(500) NULLABLE
  - `contract_id` UUID FK(contracts.id) NULLABLE
  - `lease_id` UUID FK(leases.id) NULLABLE
  - `intervention_id` UUID FK(interventions.id) NULLABLE
  - `insurance_policy_id` UUID FK(insurance_policies.id) NULLABLE
  - `document_id` UUID FK(documents.id) NULLABLE -- invoice/receipt
  - `external_ref` String(100) NULLABLE -- ERP reference
  - `status` String(20) default `recorded` -- `draft | recorded | validated | cancelled`
  - `source_type` String(30) NULLABLE, `confidence` String(20) NULLABLE, `source_ref` String(255) NULLABLE -- ProvenanceMixin
  - `created_by` UUID FK(users.id) NULLABLE
  - `created_at`, `updated_at` DateTime
- **Indexes**: `(building_id, fiscal_year)`, `(building_id, category)`, `(entry_date)`
- **Aggregate**: Financial Aggregate (standalone).

#### TaxContext
- **Purpose**: Tax records per asset per fiscal year (Swiss cantonal property tax).
- **Table**: `tax_contexts`
- **Key fields**:
  - `id` UUID PK
  - `building_id` UUID FK(buildings.id) NOT NULL idx
  - `tax_type` String(30) NOT NULL -- `property_tax | impot_foncier | valeur_locative | tax_estimation`
  - `fiscal_year` Integer NOT NULL
  - `official_value_chf` Float NULLABLE -- valeur fiscale
  - `taxable_value_chf` Float NULLABLE
  - `tax_amount_chf` Float NULLABLE
  - `canton` String(2) NOT NULL
  - `municipality` String(100) NULLABLE
  - `status` String(20) default `estimated` -- `estimated | assessed | contested | final`
  - `assessment_date` Date NULLABLE
  - `document_id` UUID FK(documents.id) NULLABLE
  - `notes` Text NULLABLE
  - `source_type` String(30) NULLABLE, `confidence` String(20) NULLABLE, `source_ref` String(255) NULLABLE -- ProvenanceMixin
  - `created_by` UUID FK(users.id) NULLABLE
  - `created_at`, `updated_at` DateTime
- **Constraint**: `(building_id, tax_type, fiscal_year)` UNIQUE
- **Aggregate**: Financial Aggregate.

### 2.8 Actions & Workflow

#### ActionItem
- **Purpose**: Task/action requiring attention, generated by system or created manually.
- **Table**: `action_items`
- **Key fields** (existing):
  - `id` UUID PK
  - `building_id` UUID FK(buildings.id) NOT NULL idx
  - `diagnostic_id` UUID FK(diagnostics.id) NULLABLE, `sample_id` UUID FK(samples.id) NULLABLE
  - `source_type` String(30) NOT NULL -- `risk | diagnostic | document | compliance | simulation | manual | system | readiness`
  - `action_type` String(50) NOT NULL -- 12 types (see constants.py)
  - `title` String(500) NOT NULL, `description` Text NULLABLE
  - `priority` String(20) default `medium` -- `low | medium | high | critical`
  - `status` String(20) default `open` -- `open | in_progress | blocked | done | dismissed`
  - `due_date` Date NULLABLE
  - `assigned_to` UUID FK(users.id) NULLABLE, `created_by` UUID FK(users.id) NULLABLE
  - `campaign_id` UUID FK(campaigns.id) NULLABLE idx
  - `metadata_json` JSON NULLABLE
  - `created_at`, `updated_at`, `completed_at` DateTime
- **New fields (L3)**:
  - `obligation_id` UUID FK(obligations.id) NULLABLE -- link to regulatory/contractual obligation
- **Aggregate**: Standalone.

#### Campaign
- **Purpose**: Multi-building coordinated action campaign.
- **Table**: `campaigns`
- **Key fields**:
  - `id` UUID PK
  - `title` String(500) NOT NULL, `description` Text NULLABLE
  - `campaign_type` String(50) NOT NULL -- `diagnostic | remediation | inspection | maintenance | documentation | other`
  - `status` String(20) default `draft` -- `draft | active | paused | completed | cancelled`
  - `priority` String(20) default `medium`
  - `organization_id` UUID FK(organizations.id) NULLABLE
  - `building_ids` JSON NULLABLE, `target_count` Integer, `completed_count` Integer
  - `date_start` Date, `date_end` Date
  - `budget_chf` Float, `spent_chf` Float
  - `criteria_json` JSON NULLABLE, `notes` Text
  - `created_by` UUID FK(users.id) NULLABLE
  - `created_at`, `updated_at` DateTime
- **Aggregate**: Standalone.

#### Intervention
- **Purpose**: Physical work performed on a building.
- **Table**: `interventions`
- **Key fields** (existing):
  - `id` UUID PK
  - `building_id` UUID FK(buildings.id) NOT NULL idx
  - `intervention_type` String(50) NOT NULL -- `renovation | maintenance | repair | demolition | installation | inspection | diagnostic | asbestos_removal | decontamination | other`
  - `title` String(500) NOT NULL, `description` Text NULLABLE
  - `status` String(20) default `completed` -- `planned | in_progress | completed | cancelled`
  - `date_start` Date, `date_end` Date
  - `contractor_name` String(255) NULLABLE, `contractor_id` UUID FK(users.id) NULLABLE
  - `cost_chf` Float NULLABLE
  - `zones_affected` JSON NULLABLE, `materials_used` JSON NULLABLE
  - `diagnostic_id` UUID FK(diagnostics.id) NULLABLE
  - `notes` Text, `created_by` UUID FK(users.id) NULLABLE
  - `created_at`, `updated_at` DateTime
- **New fields (L2)**:
  - `contract_id` UUID FK(contracts.id) NULLABLE -- link to service contract
- **Aggregate**: Standalone.

#### Assignment
- **Purpose**: Links a user to a target entity with a specific role. Legacy model for building/diagnostic scopes.
- **Table**: `assignments`
- **Key fields**:
  - `id` UUID PK
  - `target_type` String(30) NOT NULL -- `building | diagnostic`
  - `target_id` UUID NOT NULL
  - `user_id` UUID FK(users.id) NOT NULL
  - `role` String(50) NOT NULL -- `responsible | owner_contact | diagnostician | reviewer | contractor_contact`
  - `created_by` UUID FK(users.id) NOT NULL
  - `created_at` DateTime
- **Note**: Superseded by PartyRoleAssignment for new entity types. Assignment stays for backward compat.

#### Invitation
- **Purpose**: Token-based invitation for new platform users.
- **Table**: `invitations`
- **Key fields**:
  - `id` UUID PK, `email` String(255) NOT NULL, `role` String(50) NOT NULL
  - `organization_id` UUID FK(organizations.id) NULLABLE
  - `status` String(20) default `pending` -- `pending | accepted | expired | revoked`
  - `token` String(255) UNIQUE NOT NULL idx
  - `invited_by` UUID FK(users.id) NOT NULL
  - `expires_at` DateTime NOT NULL, `accepted_at` DateTime NULLABLE
  - `created_at` DateTime

### 2.9 Orchestration Layer

#### Obligation
- **Purpose**: Generalized deadline/obligation from regulatory, contractual, or lease sources.
- **Table**: `obligations`
- **Key fields**:
  - `id` UUID PK
  - `building_id` UUID FK(buildings.id) NOT NULL idx
  - `obligation_type` String(30) NOT NULL -- `regulatory | contractual | lease | insurance | tax | maintenance | inspection | administrative | custom`
  - `source_type` String(30) NOT NULL -- `contract | lease | insurance_policy | regulatory_pack | manual`
  - `source_id` UUID NULLABLE -- FK to originating entity
  - `title` String(500) NOT NULL, `description` Text NULLABLE
  - `due_date` Date NOT NULL
  - `warning_date` Date NULLABLE -- trigger reminder before due
  - `recurrence` String(20) NULLABLE -- `monthly | quarterly | semi_annual | annual | biennial | none`
  - `status` String(20) default `pending` -- `pending | upcoming | overdue | completed | waived | expired`
  - `priority` String(20) default `medium` -- `low | medium | high | critical`
  - `assigned_to_type` String(30) NULLABLE -- `user | contact | organization`
  - `assigned_to_id` UUID NULLABLE
  - `legal_reference` String(255) NULLABLE
  - `penalty_description` Text NULLABLE
  - `completed_at` DateTime NULLABLE, `completed_by` UUID FK(users.id) NULLABLE
  - `created_by` UUID FK(users.id) NULLABLE
  - `created_at`, `updated_at` DateTime
- **Indexes**: `(building_id, due_date)`, `(status)`, `(obligation_type)`
- **Upsert key**: `(building_id, obligation_type, source_type, source_id)` for auto-generated
- **Aggregate**: Standalone.

#### CommunicationThread
- **Purpose**: Conversation thread attached to any entity (building, intervention, claim, etc.).
- **Table**: `communication_threads`
- **Key fields**:
  - `id` UUID PK
  - `entity_type` String(50) NOT NULL -- `building | intervention | claim | lease | contract | diagnostic | obligation`
  - `entity_id` UUID NOT NULL
  - `subject` String(500) NOT NULL
  - `status` String(20) default `open` -- `open | closed | archived`
  - `created_by` UUID FK(users.id) NULLABLE
  - `created_at`, `updated_at` DateTime
- **Indexes**: `(entity_type, entity_id)`
- **Aggregate**: Communication Aggregate root.

#### CommunicationMessage
- **Purpose**: Individual message within a communication thread.
- **Table**: `communication_messages`
- **Key fields**:
  - `id` UUID PK
  - `thread_id` UUID FK(communication_threads.id) NOT NULL
  - `message_type` String(20) NOT NULL -- `internal_note | email_in | email_out | letter | phone_note`
  - `direction` String(10) NULLABLE -- `in | out | internal`
  - `sender_name` String(255) NULLABLE, `sender_email` String(255) NULLABLE
  - `recipient_name` String(255) NULLABLE, `recipient_email` String(255) NULLABLE
  - `body` Text NOT NULL
  - `document_ids_json` JSON NULLABLE -- array of document UUIDs (convenience cache, not source of truth)
  - `created_by` UUID FK(users.id) NULLABLE
  - `created_at` DateTime
- **Aggregate**: Belongs to Communication Aggregate.

#### Incident
- **Purpose**: Events requiring response, linking zones, claims, and interventions.
- **Table**: `incidents`
- **Key fields**:
  - `id` UUID PK
  - `building_id` UUID FK(buildings.id) NOT NULL idx
  - `incident_type` String(30) NOT NULL -- `water_damage | fire | structural | pollutant_exposure | accident | natural_hazard | security | other`
  - `title` String(500) NOT NULL, `description` Text NULLABLE
  - `severity` String(20) NOT NULL -- `low | medium | high | critical`
  - `status` String(20) default `reported` -- `reported | investigating | resolved | closed`
  - `incident_date` DateTime NOT NULL
  - `zone_id` UUID FK(zones.id) NULLABLE
  - `reported_by` UUID FK(users.id) NULLABLE
  - `claim_id` UUID FK(claims.id) NULLABLE
  - `intervention_id` UUID FK(interventions.id) NULLABLE
  - `notes` Text NULLABLE
  - `created_at`, `updated_at` DateTime
- **Aggregate**: Standalone.

### 2.10 AI & Intelligence

#### Recommendation
- **Purpose**: AI-generated next-best-action suggestions.
- **Table**: `recommendations`
- **Key fields**:
  - `id` UUID PK
  - `building_id` UUID FK(buildings.id) NOT NULL idx
  - `recommendation_type` String(50) NOT NULL -- `diagnostic_needed | maintenance_due | risk_mitigation | cost_optimization | compliance_gap | data_quality | evidence_gap`
  - `entity_type` String(50) NULLABLE, `entity_id` UUID NULLABLE
  - `title` String(500) NOT NULL, `rationale` Text NOT NULL
  - `priority` String(20) default `medium`
  - `status` String(20) default `active` -- `active | accepted | dismissed | expired | superseded`
  - `confidence` Float NULLABLE -- 0.0-1.0
  - `expires_at` DateTime NULLABLE
  - `accepted_by` UUID FK(users.id) NULLABLE, `accepted_at` DateTime NULLABLE
  - `created_at` DateTime
- **Aggregate**: Standalone.

#### AIAnalysis
- **Purpose**: Record of AI analysis performed on an entity, with input/output snapshots.
- **Table**: `ai_analyses`
- **Key fields**:
  - `id` UUID PK
  - `building_id` UUID FK(buildings.id) NULLABLE
  - `analysis_type` String(50) NOT NULL -- `risk_assessment | completeness_check | anomaly_detection | cost_estimation | compliance_check | dossier_completion`
  - `entity_type` String(50) NULLABLE, `entity_id` UUID NULLABLE
  - `input_snapshot_json` JSON NULLABLE, `output_json` JSON NULLABLE
  - `model_version` String(50) NULLABLE
  - `confidence` Float NULLABLE
  - `status` String(20) default `completed` -- `running | completed | failed`
  - `error_message` Text NULLABLE
  - `created_by` UUID FK(users.id) NULLABLE
  - `created_at` DateTime
- **Aggregate**: Standalone.

#### MemorySignal
- **Purpose**: Learned patterns/preferences from user behavior or data trends.
- **Table**: `memory_signals`
- **Key fields**:
  - `id` UUID PK
  - `building_id` UUID FK(buildings.id) NULLABLE
  - `organization_id` UUID FK(organizations.id) NULLABLE
  - `signal_type` String(50) NOT NULL -- `user_preference | workflow_pattern | data_trend | anomaly_pattern | seasonal_pattern`
  - `entity_type` String(50) NULLABLE, `entity_id` UUID NULLABLE
  - `pattern_json` JSON NOT NULL
  - `frequency` Integer default 1
  - `last_seen_at` DateTime NOT NULL
  - `status` String(20) default `active` -- `active | expired | superseded`
  - `created_at` DateTime
- **Aggregate**: Standalone.

### 2.11 Compliance & Readiness (Existing, Unchanged)

#### ReadinessAssessment
- **Table**: `readiness_assessments`
- **Key fields**: building_id, readiness_type (8 types: `safe_to_start | safe_to_renovate | safe_to_tender | safe_to_sell | safe_to_insure | safe_to_finance | safe_to_intervene | safe_to_demolish`), status (`ready | not_ready | conditional | unknown`), score Float, checks_json, blockers_json, conditions_json, assessed_at, valid_until, assessed_by, notes
- **Aggregate**: Standalone. Feeds ReadinessState projection.

#### ComplianceArtefact
- **Table**: `compliance_artefacts`
- **Key fields**: building_id, artefact_type, status (`draft | pending | submitted | acknowledged | rejected | expired`), title, description, reference_number, diagnostic_id, intervention_id, document_id (all nullable FKs), authority_name, authority_type, submitted_at, acknowledged_at, expires_at, legal_basis, metadata_json, created_by
- **Aggregate**: Compliance Aggregate root.

#### ContractorAcknowledgment
- **Table**: `contractor_acknowledgments`
- **Key fields**: intervention_id, building_id, contractor_user_id, status (`pending | sent | viewed | acknowledged | refused | expired`), sent_at, viewed_at, acknowledged_at, refused_at, expires_at, safety_requirements (JSON), contractor_notes, refusal_reason, acknowledgment_hash (SHA-256), ip_address, created_by
- **Aggregate**: Belongs to Compliance Aggregate.

### 2.12 Quality, Trust & Signals (Existing, Unchanged)

#### BuildingTrustScore
- **Table**: `building_trust_scores`
- **Key fields**: building_id, overall_score (0.0-1.0), percent_proven/inferred/declared/obsolete/contradictory, total_data_points + counts per category, trend (`improving | stable | declining`), previous_score, assessed_at, assessed_by (`system | manual | agent`)

#### DataQualityIssue
- **Table**: `data_quality_issues`
- **Key fields**: building_id, issue_type (`missing_field | stale_data | inconsistency | duplicate | format_error | unverified`), severity (`low | medium | high | critical`), status (`open | acknowledged | resolved | dismissed`), entity_type/entity_id, field_name, description, suggestion, detected_by (`system | import | manual | agent`), resolved_by/at

#### UnknownIssue
- **Table**: `unknown_issues`
- **Key fields**: building_id, unknown_type (`uninspected_zone | missing_plan | unconfirmed_material | undocumented_intervention | incomplete_diagnostic | missing_sample | unverified_source | accessibility_unknown`), severity, status (`open | acknowledged | resolved | accepted_risk`), entity_type/entity_id, blocks_readiness, readiness_types_affected, detected_by, resolved_by/at

#### ChangeSignal
- **Table**: `change_signals`
- **Key fields**: building_id, signal_type (`regulation_change | source_update | requalification_needed | evidence_stale | new_data_available | threshold_crossed`), severity (`info | warning | action_required`), status (`active | acknowledged | resolved | expired`), source, entity_type/entity_id, metadata_json, detected_at, acknowledged_by/at

### 2.13 Snapshots & Versioning (Existing)

#### BuildingSnapshot
- **Table**: `building_snapshots`
- **Key fields**: building_id, snapshot_type, trigger_event, passport_state_json, trust_state_json, readiness_state_json, evidence_counts_json, passport_grade (A-F), overall_trust, completeness_score, captured_at/by
- **Extended (L4)**: gains `ownership_summary_json`, `occupancy_summary_json`, `financial_summary_json` (all nullable)

#### DossierVersion
- **Table**: `dossier_versions`
- **Key fields**: building_id, version_number (Integer, monotonic), label, snapshot_data (JSON, full state), completeness_score, created_by_id, created_at

#### BuildingPassportState
- **Table**: `building_passport_states`
- **Key fields**: building_id, status (`draft | pending_review | validated | expired | revoked`), previous_status, changed_by_id, reason, metadata (JSON), valid_from/until

#### PostWorksState
- **Table**: `post_works_states`
- **Key fields**: building_id, intervention_id, state_type (`removed | remaining | encapsulated | treated | recheck_needed | unknown_after_works | partially_removed | newly_discovered`), pollutant_type, zone_id, element_id, material_id, verified, evidence_json, recorded_by/at

### 2.14 Safety (Existing, Unchanged)

#### ZoneSafetyStatus
- **Table**: `zone_safety_statuses`
- **Key fields**: zone_id, building_id, safety_level (`safe | restricted | hazardous | closed`), restriction_type (`access_limited | ppe_required | evacuation | no_access`), hazard_types (JSON), assessed_by, valid_from/until, is_current

#### OccupantNotice
- **Table**: `occupant_notices`
- **Key fields**: building_id, zone_id (null = building-wide), notice_type (`safety_alert | access_restriction | work_schedule | clearance`), severity (`info | warning | critical`), title, body, audience (`all_occupants | floor_occupants | zone_occupants | management_only`), status (`draft | published | expired | revoked`), published_at, expires_at, created_by

### 2.15 Simulation & Governance (Existing, Unchanged)

#### SavedSimulation
- **Table**: `saved_simulations`
- **Key fields**: building_id, title, simulation_type (`renovation | remediation | cost_estimate | scenario`), parameters_json, results_json, total_cost_chf, total_duration_weeks, risk_level_before/after, created_by

#### ExpertReview
- **Table**: `expert_reviews`
- **Key fields**: target_type/target_id, building_id, decision, confidence_level, justification, override_value/original_value (JSON), reviewed_by, reviewer_role, organization_id, status, superseded_by

#### DecisionRecord
- **Table**: `decision_records`
- **Key fields**: building_id, decision_type, title, rationale, alternatives_considered, decided_by, decided_at, context_snapshot (JSON), outcome, entity_type/entity_id

### 2.16 Packing & Export (Existing, Unchanged)

#### EvidencePack
- **Table**: `evidence_packs`
- **Key fields**: building_id, pack_type (`authority_pack | contractor_pack | owner_pack`), title, status (`draft | assembling | complete | submitted | expired`), required_sections_json, included_artefacts_json, included_documents_json, recipient_name/type/organization_id, export_job_id, assembled_at/submitted_at/expires_at

#### ExportJob
- **Table**: `export_jobs`
- **Key fields**: type (`building_dossier | handoff_pack | audit_pack`), building_id, organization_id, status (`queued | processing | completed | failed`), requested_by, file_path, error_message

#### SharedLink
- **Table**: `shared_links`
- **Key fields**: token (unique), resource_type/resource_id, created_by, organization_id, audience_type (`buyer | insurer | lender | authority | contractor | tenant`), audience_email, expires_at, max_views, view_count, allowed_sections (JSON), is_active

### 2.17 Regulatory Framework (Existing, Unchanged)

#### Jurisdiction
- **Table**: `jurisdictions`
- **Key fields**: code (unique, e.g. "ch-vd"), name, parent_id (self-ref), level (`supranational | country | region | commune`), country_code, is_active, metadata_json

#### RegulatoryPack
- **Table**: `regulatory_packs`
- **Key fields**: jurisdiction_id, pollutant_type (`asbestos | pcb | lead | hap | radon`), version, is_active, threshold_value/unit/action, risk_year_start/end, base_probability, work_categories_json, waste_classification_json, legal_reference/url, notification_required/authority/delay_days

#### PollutantRule
- **Table**: `pollutant_rules`
- **Key fields**: pollutant, material_category, risk_start_year/end_year, threshold_value/unit, diagnostic_required, legal_reference, action_if_exceeded, waste_disposal_type, cfst_default_category, canton_specific

### 2.18 System (Existing, Unchanged)

#### AuditLog
- **Table**: `audit_logs`
- **Key fields**: user_id, action, entity_type/entity_id, details (JSON), ip_address, timestamp

#### Notification / NotificationPreference / NotificationPreferenceExtended
- Notification: user_id, type (`action | invitation | export | system`), title, body, link, status (`unread | read`)
- Preference: in_app_actions, in_app_invitations, in_app_exports, digest_enabled
- Extended: user_id, preferences_json

#### BackgroundJob
- **Table**: `background_jobs`
- **Key fields**: job_type (`pack_generation | search_sync | signal_generation | dossier_completion`), status (`queued | running | completed | failed | cancelled`), building_id, organization_id, created_by, params_json, result_json, progress_pct

#### Event
- **Table**: `events`
- **Key fields**: building_id, event_type, date, title, description, created_by, metadata_json

#### BuildingRiskScore
- **Table**: `building_risk_scores`
- **Key fields**: building_id (unique), asbestos/pcb/lead/hap/radon_probability, overall_risk_level, confidence, factors_json, data_source

---

## 3. Read-Side Projections (Non-Authoritative)

Projections are computed views, never primary truth. Aggregated from canonical entities and cached/materialized as needed.

### PassportSnapshot
- **Sources**: Building (Asset) + Diagnostics + Samples + EvidenceLinks/EvidenceItems + BuildingTrustScore + ReadinessAssessments + OwnershipRecords + Leases + FinancialEntries + Zones + Materials + InventoryItems
- **Output**: Unified building passport with grade (A-F), knowledge score, readiness status, blindspots, contradictions, evidence summary, ownership/occupancy summary, financial summary

### ReadinessState
- **Sources**: Building + Diagnostics + Obligations + ComplianceArtefacts + UnknownIssues + ReadinessAssessments + ContractorAcknowledgments
- **Output**: Per-readiness-type evaluation (safe_to_start, safe_to_sell, etc.) with blockers, conditions, and action plan

### PortfolioSummary
- **Sources**: Portfolio + all member Buildings' PassportSnapshots + ReadinessStates + FinancialEntries + BuildingTrustScores
- **Output**: Aggregated portfolio-level metrics (avg grade, trust, completeness, financial summary, risk distribution)

### CompletionWorkspace
- **Sources**: Building + UnknownIssues + DataQualityIssues + BuildingTrustScore + ChangeSignals + Recommendations
- **Output**: Interactive workspace showing what's missing, what needs verification, what's stale, with prioritized action list

### DecisionRoom
- **Sources**: Building + DecisionRecords + ExpertReviews + SavedSimulations + Recommendations + AIAnalyses
- **Output**: Decision support view with history, simulations, AI recommendations, expert reviews

### SharedView
- **Sources**: Any of the above, filtered by SharedLink.allowed_sections and audience_type
- **Output**: Audience-scoped read-only slice. E.g., authority sees compliance + diagnostics; buyer sees passport + readiness + financials

### SharedPack
- **Sources**: EvidencePack definition + referenced Documents + ComplianceArtefacts + Diagnostics
- **Output**: Packaged downloadable bundle assembled from truth entities
- **Pack types**: authority_pack (compliance + diagnostics + safety), contractor_pack (safety + zones + materials), owner_pack (passport + financials + readiness), insurer_pack (risk + claims + interventions)

---

## 4. Aggregate Boundaries

Aggregates define consistency boundaries. Operations within an aggregate are transactional. Cross-aggregate references use eventual consistency.

### Asset Aggregate
- **Root**: Building
- **Members**: Zone (hierarchical), Unit, UnitZone, BuildingElement, Material, TechnicalPlan, PlanAnnotation, InventoryItem
- **Invariant**: Zone belongs to exactly one building. Element belongs to exactly one zone. Material belongs to exactly one element.

### Diagnostic Aggregate
- **Root**: Diagnostic
- **Members**: Sample, FieldObservation (loosely coupled via building_id + optional diagnostic_id)
- **Invariant**: Sample belongs to exactly one diagnostic. Diagnostic status transitions are validated.

### Evidence Aggregate
- **Root**: Document or EvidenceItem
- **Members**: DocumentLink, EvidenceRelation
- **Invariant**: DocumentLink entries reference valid document_id. EvidenceRelation entries reference valid evidence_item_id.

### Occupancy Aggregate
- **Root**: Lease
- **Members**: LeaseEvent
- **Invariant**: LeaseEvents are chronologically ordered. Lease reference_code is unique per building.

### Contractual Aggregate
- **Root**: Contract
- **Members**: InsurancePolicy (specialized), Claim
- **Invariant**: Claims belong to a valid InsurancePolicy. Contract reference_code is unique per building.

### Financial Aggregate
- **Root**: FinancialEntry (standalone)
- **Members**: TaxContext
- **Invariant**: FinancialEntry FK references must be valid if set. TaxContext unique per (building, tax_type, fiscal_year).

### Compliance Aggregate
- **Root**: ComplianceArtefact
- **Members**: ContractorAcknowledgment
- **Invariant**: Status transitions follow lifecycle (draft > submitted > acknowledged/rejected).

### Communication Aggregate
- **Root**: CommunicationThread
- **Members**: CommunicationMessage
- **Invariant**: Messages are append-only. Thread status constrains new message creation.

### Portfolio Aggregate
- **Root**: Portfolio
- **Members**: BuildingPortfolio (junction)
- **Invariant**: Portfolio name unique per organization. Building can appear in multiple portfolios.

### Party Aggregate
- **Root**: Contact (Party)
- **Members**: PartyRoleAssignment
- **Invariant**: Contact email unique per organization. PartyRoleAssignment validity windows do not overlap for same (party, entity, role) triple.

---

## 5. Identity Rules

| Entity | Identity Rule |
|--------|--------------|
| Building (Asset) | `egrid` (unique, nullable), `egid` (unique, nullable), `official_id` (legacy). At least one of egrid/egid should be set for Swiss buildings. |
| Contact (Party) | `(email, organization_id)` unique when email is set; `external_ref` unique per org when set |
| Document | `(content_hash, file_path)` unique pair when content_hash is set. SHA-256 of file content. |
| EvidenceLink | `(source_type, source_id, target_type, target_id, relationship)` unique composite |
| EvidenceItem | UUID PK; content identity via evidence_type + building_id + source_ref |
| Lease | `(reference_code, building_id)` unique |
| Contract | `(reference_code, building_id)` unique |
| InsurancePolicy | `(policy_number)` unique |
| Unit | `(reference_code, building_id)` unique |
| Portfolio | `(name, organization_id)` unique |
| TaxContext | `(building_id, tax_type, fiscal_year)` unique |
| Jurisdiction | `code` unique (hierarchical: "eu", "ch", "ch-vd", "ch-ge") |
| User | `email` unique globally |
| Organization | `id` UUID (no natural key enforced; name may repeat across cantons) |

---

## 6. Relation Rules

### Explicit Junction/Relation Tables (NOT JSON arrays of IDs)
- `DocumentLink`: document_id + entity_type + entity_id + link_type -- many-to-many document attachments
- `EvidenceRelation`: evidence_item_id + entity_type + entity_id + relationship -- replaces polymorphic EvidenceLink source/target
- `PartyRoleAssignment`: party_type + party_id + entity_type + entity_id + role -- unified role model
- `BuildingPortfolio`: building_id + portfolio_id -- many-to-many
- `UnitZone`: unit_id + zone_id -- many-to-many

### Direct FK Relations (One-to-Many, stay as FKs)
- Lease -> Building (building_id)
- Contract -> Building (building_id)
- InsurancePolicy -> Building (building_id), -> Contract (contract_id, nullable)
- Claim -> InsurancePolicy (insurance_policy_id), -> Building (building_id)
- FinancialEntry -> Building, Contract, Lease, Intervention, InsurancePolicy, Document (all nullable FKs)
- TaxContext -> Building (building_id)
- InventoryItem -> Building (building_id), -> Contract (maintenance_contract_id, nullable)
- Obligation -> Building (building_id)
- CommunicationThread: entity_type + entity_id (polymorphic context reference)
- Incident -> Building, Zone, Claim, Intervention (all FKs)

### Document Attachment Dual-Path Policy
Entities may reference documents via TWO complementary mechanisms:
- **`document_id` FK (direct)**: Points to the single primary/proof document for that entity. One-to-one convenience. Used when an entity has one canonical supporting document (e.g., OwnershipRecord → acte de vente, TaxContext → tax notice). This is NOT an ad-hoc pattern to eliminate — it is the "primary document" shortcut.
- **`DocumentLink` junction (many-to-many)**: Links any number of documents to any entity via `(document_id, entity_type, entity_id, link_type)`. Used for multi-document attachment, auxiliary documents, and cross-entity document sharing.

Both coexist. `document_id` is the fast path for the main proof document. `DocumentLink` is the full graph for all attachments. Neither replaces the other. This is analogous to `Building.owner_id` (legacy shortcut) coexisting with `PartyRoleAssignment` (canonical role model).

### Forbidden Patterns
- No JSON columns storing arrays of entity UUIDs as primary truth (existing `zones_affected`, `building_ids` on Campaign stay as convenience caches, not authoritative)
- No uncontrolled polymorphic source_type/source_id without accompanying junction table (EvidenceLink stays for backward compat; new code uses EvidenceRelation)
- No cross-aggregate FKs with CASCADE DELETE (use SET NULL or application-level cleanup)

---

## 7. Provenance/Confidence Policy

### ProvenanceMixin
All new truth entities adopt the `ProvenanceMixin` pattern:

```
source_type  String(30) -- import | manual | ai | inferred | official
confidence   String(20) -- verified | declared | inferred | unknown
source_ref   String(255) -- optional external reference (import batch ID, API endpoint, document ref)
```

### Existing Models with Source Tracking
These keep their existing fields as-is:
- `Building`: source_dataset, source_imported_at, source_metadata_json
- `Material`: source (diagnostic/visual_inspection/documentation/owner_declaration/import)
- `EvidenceLink`: confidence (Float), source_type
- `DataQualityIssue`: detected_by (system/import/manual/agent)
- `BuildingTrustScore`: assessed_by (system/manual/agent)

### New Models Adopting the Mixin
All L1-L3 entities carry source_type, confidence, source_ref:
Contact, OwnershipRecord, Lease, Contract, InsurancePolicy, FinancialEntry, TaxContext, InventoryItem, Obligation, EvidenceItem

### Confidence Hierarchy
1. `verified` -- confirmed by official source, lab result, or expert review
2. `declared` -- stated by owner/manager, not independently verified
3. `inferred` -- derived by system/AI from available data
4. `unknown` -- no provenance information available

---

## 8. Audit/Versioning/Idempotence Policy

### AuditLog Extension
- Existing `AuditLog` model extended to all new entities
- Every CRUD operation on canonical entities generates an audit log entry
- AI-generated changes logged with system user context

### Snapshot Strategy
- `BuildingSnapshot` captures point-in-time state (passport, trust, readiness, evidence counts)
- Extended (L4) with: `ownership_summary_json`, `occupancy_summary_json`, `financial_summary_json` (all nullable)
- `DossierVersion` provides immutable labeled snapshots with version_number for audit trail

### Idempotent Upsert Convention
All imports and generators use upsert-on-natural-key:
- ActionItem: `(building_id, source_type, action_type, diagnostic_id/sample_id)` for system-generated
- UnknownIssue: `(building_id, unknown_type, entity_type, entity_id)` for system-detected
- ChangeSignal: `(building_id, signal_type, entity_type, entity_id)` for auto-generated
- PartyRoleAssignment: `(party_type, party_id, entity_type, entity_id, role)` for role assignments
- Obligation: `(building_id, obligation_type, source_type, source_id)` for auto-generated

Auto-resolve pattern: when triggering condition is resolved, issue is automatically marked resolved (used by unknown_generator, contradiction_detector, readiness_action_generator).

### Versioning
- DossierVersion: immutable, sequential version_number per building
- Once created, a version is never modified

---

## 9. Current-to-Target Mapping Table

| Current Model | Canonical Entity | Migration Path | Breaking Changes |
|---|---|---|---|
| Building | Asset (first shape) | Add `organization_id` FK (nullable). Adapter layer. | None |
| Organization | Organization + Contact link | Add `contact_person_id` FK (nullable) | None |
| User | User + Contact link | Add `linked_contact_id` FK (nullable) | None |
| Zone | Zone | Add `usage_type` field (nullable) | None |
| (new) | Unit | New table, references Zones via junction | N/A |
| (new) | Contact (Party) | New table | N/A |
| (new) | PartyRoleAssignment | New table | N/A |
| (new) | Portfolio + BuildingPortfolio | New tables | N/A |
| (new) | OwnershipRecord | New table | N/A |
| Document | Document + DocumentLink | Add `content_hash` (nullable). DocumentLink adds many-to-many alongside existing `document_id` FKs (dual-path, see section 6). | None |
| EvidenceLink | EvidenceItem + EvidenceRelation | Old table stays. New tables alongside. Adapter bridges both. | None |
| ActionItem | ActionItem | Add `obligation_id` FK (nullable) | None |
| Intervention | Intervention | Add `contract_id` FK (nullable) | None |
| (new) | Lease + LeaseEvent | New tables | N/A |
| (new) | Contract | New table | N/A |
| (new) | InsurancePolicy | New table | N/A |
| (new) | Claim | New table | N/A |
| (new) | FinancialEntry | New table | N/A |
| (new) | TaxContext | New table | N/A |
| (new) | InventoryItem | New table | N/A |
| (new) | Obligation | New table | N/A |
| (new) | CommunicationThread + Message | New tables | N/A |
| (new) | Incident | New table | N/A |
| (new) | Recommendation | New table | N/A |
| (new) | AIAnalysis | New table | N/A |
| (new) | MemorySignal | New table | N/A |
| (new) | EvidenceItem + EvidenceRelation | New tables | N/A |
| (new) | DocumentLink | New junction table | N/A |
| (new) | UnitZone | New junction table | N/A |
| BuildingSnapshot | BuildingSnapshot | Gains 3 nullable JSON columns | None |
| ReadinessAssessment | Stays, feeds ReadinessState projection | Unchanged | None |
| BuildingPassportState | Stays, feeds PassportSnapshot projection | Unchanged | None |
| SharedLink | Stays, feeds SharedView projection | Unchanged | None |
| All other existing models | Stay as-is | Unchanged | None |

**Guarantee**: All current API endpoints continue working. Canonical entities add NEW endpoints alongside. No drops, no renames, no breaking FK changes.

---

## Planned -- Remediation Marketplace

> Mise en concurrence encadree for pollutant remediation. Closed verified network, not open directory. Shares BatiConnect infra (auth, docs, audit) but owns its own models and routes.

### New Entities

| Entity | Purpose | Key Fields |
|---|---|---|
| CompanyProfile | Verified remediation company identity | id, organization_id, trade_categories, service_regions, certifications, description, is_verified, verified_at |
| CompanyVerification | Verification lifecycle for a company | id, company_profile_id, status (pending/approved/rejected/suspended), verified_by, evidence_refs, notes |
| CompanySubscription | Subscription/monetization record | id, company_profile_id, plan_type, status (active/cancelled/expired), started_at, expires_at |
| ClientRequest | RFQ issued by a property manager or owner | id, building_id, organization_id, created_by, title, description, pollutant_types, work_category, deadline, status (draft/open/closed/awarded/cancelled) |
| RequestDocument | Document attached to a ClientRequest | id, client_request_id, document_id, label |
| RequestInvitation | Invitation sent to a company for a specific RFQ | id, client_request_id, company_profile_id, status (pending/accepted/declined/expired), sent_at |
| Quote | Company response to an RFQ | id, client_request_id, company_profile_id, amount, currency, validity_days, technical_description, status (draft/submitted/withdrawn/accepted/rejected) |
| AwardConfirmation | Formal award of an RFQ to a company | id, client_request_id, quote_id, company_profile_id, awarded_by, awarded_at, confirmation_hash |
| CompletionConfirmation | Post-works completion confirmation | id, award_confirmation_id, completed_at, confirmed_by_client, confirmed_by_company, completion_hash |
| Review | Verified post-completion rating | id, completion_confirmation_id, reviewer_user_id, company_profile_id, rating, comment, is_verified |

### Invariants

- No recommendation: the platform never ranks or recommend companies to clients
- Payment != ranking: subscription tier does not influence visibility in RFQ results
- Verified contracts only: awards and reviews require completed verification chain (CompanyVerification approved, AwardConfirmation signed, CompletionConfirmation confirmed)
