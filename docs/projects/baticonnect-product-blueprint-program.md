# BatiConnect Product Blueprint Program

## Mission

- business outcome: Officialize BatiConnect as the unified product identity and canonical architecture for building intelligence, property management, and decision support.
- user/problem context: SwissBuilding was built as a pollutant diagnostics platform. BatiConnect repositions it as a full real estate intelligence OS covering ownership, occupancy, contracts, insurance, financials, tax, and portfolio intelligence -- all on a single truth backbone.
- visible consumer window (`<=2 waves`): Blueprint documents enable all future implementation waves to execute from a stable, pre-designed canonical model.

## Agent usage

- `Tu peux utiliser tes agents si pertinent, notamment pour la redaction des blueprints et briefs.`

## Scope

- in scope:
  - 4 blueprint documents (domain, surface, capability, build order)
  - 3 follow-on wave briefs (backbone contracts, ingestion contracts, read-model cut lines)
  - ORCHESTRATOR.md control-plane alignment
- out of scope:
  - Python/TypeScript code changes
  - SQLAlchemy model creation
  - Alembic migrations
  - hub-file wiring
  - repo/package rename (deferred)
  - frontend component changes

## Target files

- primary file(s):
  - `docs/blueprints/baticonnect-domain-blueprint.md` (new)
  - `docs/blueprints/baticonnect-surface-blueprint.md` (new)
  - `docs/blueprints/baticonnect-capability-blueprint.md` (new)
  - `docs/blueprints/baticonnect-build-order.md` (new)
- satellites:
  - `docs/projects/baticonnect-product-blueprint-program.md` (new, this file)
  - `docs/waves/w-bc1-canonical-backbone-contracts.md` (new)
  - `docs/waves/w-bc2-ingestion-projection-contracts.md` (new)
  - `docs/waves/w-bc3-read-model-facade-cutlines.md` (new)
  - `ORCHESTRATOR.md` (modify -- Lead Feed section only)
- change mode:
  - `new`: all docs/blueprints/ files, all docs/waves/w-bc*.md files, this program file
  - `modify`: ORCHESTRATOR.md
- hub-file ownership:
  - `supervisor_merge`: ORCHESTRATOR.md
  - `agent_allowed`: all docs files
- do-not-touch:
  - `backend/app/schemas/__init__.py`
  - `backend/app/models/__init__.py`
  - `backend/app/api/router.py`

## Non-negotiable constraints

- data/model constraints:
  - canonical entities locked as listed in domain blueprint (write-side: Portfolio, Asset, Unit, Party, PartyRoleAssignment, Ownership, Lease, Contract, InsurancePolicy, Claim, Document, EvidenceItem, Communication, Obligation, Incident, Intervention, FinancialEntry, TaxContext, InventoryItem, Recommendation, AIAnalysis, MemorySignal; read-side: PassportSnapshot, ReadinessState, PortfolioSummary, CompletionWorkspace, DecisionRoom, SharedView, SharedPack)
  - read models are projections only -- never primary truth
- technical constraints:
  - no code changes, documentation only
  - BatiConnect = official strategic/product language in new artifacts
  - repo/package renaming deferred to later wave
- repo conventions to preserve:
  - brief_lint.py must pass on all new briefs
  - lead_control_plane_check.py must pass after ORCHESTRATOR.md update

## Validation

- validation type:
  - `canonical_integration`: control-plane coherence across ORCHESTRATOR.md and project/wave briefs
- commands to run:
  - `python scripts/brief_lint.py --strict-diff docs/projects/baticonnect-product-blueprint-program.md`
  - `python scripts/brief_lint.py --strict-diff docs/waves/w-bc1-canonical-backbone-contracts.md docs/waves/w-bc2-ingestion-projection-contracts.md docs/waves/w-bc3-read-model-facade-cutlines.md`
  - `python scripts/lead_control_plane_check.py --strict`
- required test level:
  - no code tests required (documentation only)
- acceptance evidence to report:
  - brief_lint passes on all 4 briefs
  - lead_control_plane_check passes
  - all 8 files created

## Exit criteria

- functional:
  - 4 blueprints created with complete canonical entity definitions
  - 3 wave briefs execution-ready for downstream agents
  - 1 umbrella program brief framing the BatiConnect program
- quality/reliability:
  - brief_lint passes on all briefs
  - lead_control_plane_check passes
- docs/control-plane updates:
  - ORCHESTRATOR.md updated with BatiConnect program in Lead Feed

## Non-goals

- explicitly not part of this brief:
  - implementing any backbone models
  - creating Pydantic schemas or SQLAlchemy models
  - creating Alembic migrations
  - modifying any existing code
  - repo/package rename

## Deliverables

- code: none
- tests: none
- docs:
  - `docs/blueprints/baticonnect-domain-blueprint.md`
  - `docs/blueprints/baticonnect-surface-blueprint.md`
  - `docs/blueprints/baticonnect-capability-blueprint.md`
  - `docs/blueprints/baticonnect-build-order.md`
  - `docs/projects/baticonnect-product-blueprint-program.md`
  - `docs/waves/w-bc1-canonical-backbone-contracts.md`
  - `docs/waves/w-bc2-ingestion-projection-contracts.md`
  - `docs/waves/w-bc3-read-model-facade-cutlines.md`

## Wave closeout (required in ORCHESTRATOR.md)

- clear: all 8 documents created, brief_lint passes, control-plane check passes
- fuzzy: nothing
- missing: nothing

## Catalog Metadata

- macro_domain: product_architecture
- ring: ring_1_to_4
- user_surface: all
- go_to_market_relevance: direct_wedge
- moat_type: canonical_architecture + truth_backbone
- depends_on: current building-centric substrate

## Linked Blueprints

- `docs/blueprints/baticonnect-domain-blueprint.md`
- `docs/blueprints/baticonnect-surface-blueprint.md`
- `docs/blueprints/baticonnect-capability-blueprint.md`
- `docs/blueprints/baticonnect-build-order.md`

## Linked Programs

- `lease-tenancy-and-occupancy-economics-program.md`
- `transaction-insurance-finance-readiness-program.md`
- `domain-facades-and-service-consolidation-program.md`
- `dataset-scenario-factory-and-seed-strategy-program.md`
- `read-models-query-topology-and-aggregate-apis-program.md`

## Key Doctrines

1. Build once, expose later: design the final canonical graph now, implement by stable layers
2. Superset + adapters: current Building-centric APIs stay stable behind facades; canonical entities add new endpoints alongside
3. Derived projections: Passport, Readiness, Pack, SharedView, PortfolioSummary are never primary truth
4. BatiConnect Ops / Workspace split: single truth engine, two presentation surfaces
5. Sharing and audit from day one: not bolted on later
