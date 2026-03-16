# Open-Source Accelerators 2026 Radar

## Mission

Keep SwissBuildingOS aligned with the strongest open-source building blocks that became newly practical or materially more mature by 2026, so the product can accelerate category-defining layers without rebuilding commodity infrastructure.

## Why This Matters

SwissBuilding should build its moat in:
- building truth
- evidence
- readiness
- orchestration
- portfolio intelligence
- living building memory

It should not waste time rebuilding mature open-source layers when they now exist in a usable state.

This radar exists to guide:
- architecture pull decisions
- low-regret integrations
- capability experiments
- future Claude workstreams
- "build vs pull" choices when a new engine becomes urgent

## Pull Principles

- pull open-source where it accelerates an existing SwissBuilding engine
- do not pull a tool only because it is trendy
- prefer standards-aware tools over isolated point solutions
- keep SwissBuilding as the source of truth for:
  - readiness
  - evidence
  - dossier logic
  - rules packs
  - building passport semantics
- if a tool becomes the operational source of truth for one capability, document that boundary clearly
- keep experimental tools behind a clear service boundary

## Capability Radar

### 1. Multimodal document understanding

Strong candidates:
- `Docling`
  - structured document conversion, tables, layout, multimodal parsing
  - strategic use:
    - dossier bootstrap
    - grounded extraction
    - multimodal query
  - sources:
    - https://github.com/docling-project/docling
    - https://docling-project.github.io/docling/
- `OCRmyPDF`
  - pragmatic OCR baseline for scanned PDFs
  - strategic use:
    - searchable dossier memory
    - better downstream extraction
  - source:
    - https://ocrmypdf.readthedocs.io/en/stable/index.html
- `PaddleOCR`
  - stronger OCR path when scans, tables, or layouts exceed the pragmatic baseline
  - strategic use:
    - harder scans
    - multilingual OCR
    - structured extraction assist
  - source:
    - https://www.paddleocr.ai/latest/en/index.html
- `Apache Tika`
  - broad metadata and content extraction utility
  - strategic use:
    - vault metadata normalization
    - coarse extraction fallback
  - source:
    - https://tika.apache.org/

### 2. Human correction, curation, and annotation

Strong candidates:
- `Argilla`
  - dataset curation and human-feedback tooling
  - strategic use:
    - knowledge workbench
    - extraction correction
    - terminology normalization
    - agent feedback loops
  - source:
    - https://docs.argilla.io/latest/
- `Label Studio`
  - general labeling and review workflows
  - strategic use:
    - human review for extracted fields
    - evidence classification
    - weak-signal labeling
  - source:
    - https://labelstud.io/guide/
- `CVAT`
  - image/document/plan annotation
  - strategic use:
    - plan markup bootstrap
    - field photo annotation
    - geometry-linked evidence labeling
  - source:
    - https://docs.cvat.ai/docs/

### 3. Geometry / BIM / IFC

Strong candidates:
- `IfcOpenShell`
  - open-source IFC toolkit and geometry engine
  - strategic use:
    - IFC import/export
    - geometry references
    - passport/logbook convergence
    - geometry-aware contradiction checks
  - sources:
    - https://ifcopenshell.org/
    - https://docs.ifcopenshell.org/

### 4. Building semantics and systems intelligence

Strong candidates:
- `Brick`
  - open ontology direction for building systems and equipment
  - strategic use:
    - technical systems layer
    - system readiness
    - semantic mapping
  - source:
    - https://docs.brickschema.org/
- `Project Haystack`
  - operational semantics for building systems and telemetry
  - strategic use:
    - live operations layer
    - equipment tags
    - system-aware packs and maintenance memory
  - source:
    - https://project-haystack.org/doc/

### 5. Search and retrieval

Strong candidates:
- `Meilisearch`
  - repo-aligned search layer
  - strategic use:
    - dossier search
    - evidence retrieval
    - grouped building/document/action navigation
  - source:
    - https://www.meilisearch.com/docs

### 6. Maps and spatial distribution

Strong candidates:
- `MapLibre`
  - open-source map rendering base
  - strategic use:
    - portfolio map
    - restriction heatmaps
    - evidence heatmaps
  - source:
    - https://maplibre.org/maplibre-gl-js/docs/
- `PMTiles / Protomaps`
  - efficient self-hosted tile distribution
  - strategic use:
    - self-hosted basemaps
    - large-scale spatial packaging
    - bounded external viewers
  - source:
    - https://docs.protomaps.com/pmtiles/

### 7. Workflow and durable execution

Strong candidates:
- `Temporal`
  - durable execution for long-running workflows
  - strategic use:
    - autonomous dossier completion
    - retries and checkpoints
    - workflow traces
    - pack generation orchestration
  - source:
    - https://docs.temporal.io/
- `Valkey`
  - Redis-compatible open infrastructure path
  - strategic use:
    - queue/cache durability path if Redis posture changes
  - source:
    - https://www.valkey.io/docs/

### 8. Identity, policy, and enterprise controls

Strong candidates:
- `Keycloak`
  - mature identity and SSO
  - strategic use:
    - enterprise SSO
    - tenant-aware identity foundation
  - source:
    - https://www.keycloak.org/documentation
- `OpenFGA`
  - relationship-based authorization engine
  - strategic use:
    - audience-bounded sharing
    - external viewer permissions
    - pack visibility rules
  - source:
    - https://openfga.dev/docs
- `Open Policy Agent`
  - policy evaluation engine
  - strategic use:
    - policy-as-code for sharing constraints
    - approval gates
    - environment and tenant policy checks
  - source:
    - https://www.openpolicyagent.org/docs/latest/

### 9. Observability and recovery

Strong candidates:
- `OpenTelemetry`
  - vendor-neutral telemetry foundation
  - strategic use:
    - trace workflows
    - instrument agent runs
    - export and OCR pipeline visibility
  - source:
    - https://opentelemetry.io/docs/
- `SigNoz`
  - open-source observability platform
  - strategic use:
    - internal operator view
    - recovery and support workflows
  - source:
    - https://signoz.io/docs/

### 10. Analytics, benchmarking, and learning

Strong candidates:
- `DuckDB`
  - embedded analytics engine
  - strategic use:
    - benchmark snapshots
    - portfolio analytics
    - pack-ready aggregates
  - source:
    - https://duckdb.org/docs/
- `Ibis`
  - portable dataframe/query layer
  - strategic use:
    - consistent analytics expressions across engines
    - safer benchmark/service-layer analytics
  - source:
    - https://ibis-project.org/
- `OpenLineage`
  - lineage signal for data and workflow pipelines
  - strategic use:
    - evidence provenance tracing beyond documents
    - analytics and import lineage
  - source:
    - https://www.openlineage.io/docs/

### 11. Live telemetry, event ingestion, and building-state transport

Strong candidates:
- `Home Assistant`
  - pragmatic integration layer for small-building or residential device ecosystems
  - strategic use:
    - fast prototyping for owner/resident/device surfaces
    - bounded smart-home / smart-building bridges
  - source:
    - https://www.home-assistant.io/docs/
- `EMQX`
  - MQTT broker and event transport layer
  - strategic use:
    - live telemetry ingest for meters, probes, and field devices
    - event fan-out into anomaly and incident workflows
  - source:
    - https://docs.emqx.com/
- `NATS / JetStream`
  - lightweight eventing and durable messaging
  - strategic use:
    - internal live-state propagation
    - bounded event backbone between ingest, signals, packs, and projections
  - source:
    - https://docs.nats.io/

## What Became Newly Practical by 2026

These are materially more realistic than they were in 2025:
- grounded multimodal extraction with usable structure
- bounded autonomous dossier completion with verification traces
- cross-modal change detection between plans, reports, images, and interventions
- IFC-aware geometry workflows usable by product teams, not only BIM specialists
- standards-aligned semantics for systems/equipment without inventing a private ontology first
- open-source relationship/policy tooling strong enough for enterprise sharing controls
- self-hosted modern map distribution for larger spatial products
- low-friction embedded analytics and lineage for benchmark/intelligence layers
- open-source observability stacks good enough for agent-heavy product operations

## Suggested Pull Order

### Pull now when the matching workstream needs it

1. `Docling`
   - when multimodal extraction or grounded query must move beyond OCR-only
2. `IfcOpenShell`
   - when geometry-native intelligence leaves the sketch stage
3. `Argilla` / `Label Studio` / `CVAT`
   - when the knowledge workbench or plan/photo review becomes a bottleneck
4. `Brick` / `Project Haystack`
   - when systems/equipment intelligence becomes product-visible
5. `Temporal`
   - when agent/workflow orchestration requires durability beyond lightweight queues
6. `Keycloak` + `OpenFGA` / `OPA`
   - when enterprise identity and audience-bounded sharing become active programs
7. `OpenTelemetry` + `SigNoz`
   - when reliability/observability workstream deepens
8. `MapLibre` + `PMTiles`
   - when portfolio map and external spatial distribution harden
9. `DuckDB` + `Ibis` + `OpenLineage`
   - when benchmarking and privacy-safe learning become productized

### Pull later only if the gain is real

- `PaddleOCR`
  - only when OCR quality is the true bottleneck
- `Apache Tika`
  - only if metadata extraction breadth becomes a real need beyond current parsers
- `Valkey`
  - only if infra posture or licensing direction requires a Redis-compatible shift

## Not-Now Rules

Do not use this radar to justify:
- generic chatbot layers
- opaque AI summaries without proof links
- vector-db-first architecture as a substitute for product truth
- replacing the product's own evidence/readiness logic with a third-party stack
- overfitting the stack to tools before a SwissBuilding engine actually needs them

## Acceptance Criteria

This radar is useful if:
- Claude can pull from it when a new capability becomes urgent
- build-vs-pull decisions can be made faster
- SwissBuilding's moat remains in product intelligence, not duplicated infrastructure work
- the repo keeps a current map of open-source accelerators that became materially practical by 2026
