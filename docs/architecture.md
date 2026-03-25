# SwissBuildingOS — Architecture

## System Overview

SwissBuildingOS is designed as an **Agent OS for at-risk buildings**.
The system is meant to transform public data, diagnostic reports, documents, events, and building history into:
- evidence
- decisions
- actions
- deliverable packs
- portfolio strategy

The architecture is therefore not just CRUD plus APIs. It is evolving toward 5 product layers:
- **Evidence OS**
- **Building Memory OS**
- **Action OS**
- **Portfolio OS**
- **Agent OS**

This architecture should also be read as the implementation path toward a broader **Building Intelligence Network**.

---

## Tech Stack

| Layer         | Technology                        |
|---------------|-----------------------------------|
| Backend API   | FastAPI (Python 3.11+)            |
| Frontend      | React (TypeScript, Vite)          |
| Database      | PostgreSQL 15 + PostGIS           |
| Object Storage| MinIO (S3-compatible)             |
| Containerization | Docker / Docker Compose        |
| Auth          | JWT (python-jose) + bcrypt        |
| Observability | Prometheus + structlog            |

---

## Project Structure

```
backend/
  app/
    models/          # SQLAlchemy ORM models
    schemas/         # Pydantic request/response schemas
    services/        # Business logic layer
    api/             # FastAPI route handlers (v1)
    ml/              # Machine learning modules

frontend/
  src/
    pages/           # Route-level page components
    components/      # Reusable UI components
    api/             # API client / fetch wrappers
    hooks/           # Custom React hooks
```

---

## Current Core Schema

The current implementation uses the following core tables:

| Table                 | Purpose                                      |
|-----------------------|----------------------------------------------|
| `users`               | User accounts and credentials                |
| `organizations`       | Companies / entities that own or manage buildings |
| `buildings`           | Building records with geolocation (PostGIS)  |
| `diagnostics`         | Pollutant diagnostic reports per building     |
| `samples`             | Lab samples collected during a diagnostic    |
| `events`              | Timeline events on a building (works, inspections) |
| `documents`           | Uploaded files (reports, photos, plans)       |
| `pollutant_rules`     | Regulatory thresholds per pollutant type      |
| `building_risk_scores`| Computed risk scores per building             |
| `audit_logs`          | Immutable log of all state-changing actions   |

Key relationships:
- A **building** belongs to an **organization**.
- A **diagnostic** belongs to a **building** and contains multiple **samples**.
- **Documents** and **events** are scoped to a building.
- **building_risk_scores** are derived from diagnostics and pollutant rules.

## Digital Building Identity

Target principle:
- a building should keep a persistent identity across its lifecycle

Target identity anchors:
- `EGID`
- `EGRID` when available from trustworthy sources
- parcel / cadastral references when available
- coordinates / geospatial anchors

Important implementation constraint:
- identifiers must remain distinct
- not every source currently exposes a trustworthy value for every identity anchor

## Reserved Future Product Domains

These domains are part of the target architecture and should be treated as planned first-class objects, not as current claims:

- `BuildingMemoryVersion`
- `EvidenceLink` / `EvidenceItem`
- `ActionItem`
- `Campaign`
- `Assignment`
- `HandoffPack` / `ProofPack` / `ExportJob`
- `SavedSimulation`
- `PortfolioScenario`
- `DataQualityIssue`
- `ChangeSignal`
- `AgentRecommendation`
- `AgentRun`

They support the future target state where the backend remains the source of truth for:
- recommendations
- evidence
- change signals
- system actions
- agent outputs

---

## RBAC Model

Access control is role-based with 6 roles:

| Role            | Description                                         |
|-----------------|-----------------------------------------------------|
| `admin`         | Full platform access, user management               |
| `owner`         | Building owner — views own buildings and diagnostics |
| `diagnostician` | Creates and manages diagnostics and samples          |
| `architect`     | Views buildings, diagnostics; plans renovations      |
| `authority`     | Regulatory authority — read-only oversight           |
| `contractor`    | Renovation contractor — scoped to assigned buildings |

Permissions are expressed as `resource:action` pairs (e.g., `buildings:create`, `diagnostics:validate`) and enforced at the API layer.

---

## Layered System Model

### Evidence OS

Purpose:
- connect scores, diagnostics, documents, rules, and history to explicit evidence

Examples:
- explainable risk
- confidence / uncertainty
- traceable regulatory rationale
- future evidence graph

### Building Memory OS

Purpose:
- treat the building as a living memory across time, imports, documents, diagnostics, and changes

Examples:
- digital twin state over time
- source history
- document evolution
- future memory versions
- re-qualification triggers

### Action OS

Purpose:
- translate risk and missing information into coordinated work

Examples:
- manual and system actions
- playbooks
- assignments
- intervention preparation
- future campaigns

### Portfolio OS

Purpose:
- aggregate buildings into a steerable portfolio

Examples:
- prioritization
- CAPEX planning
- saved views
- map-supported decisions
- future national-scale intelligence accumulation

### Agent OS

Purpose:
- orchestrate invisible specialized agents inside the workflows

Examples:
- document reading
- data reconciliation
- conflict detection
- suggestion generation
- pack preparation
- re-triggering actions

Rule:
- invisible agents come first
- a visible copilote can come later only after workflow value is proven

## Market Entry and Expansion Logic

Initial wedge:
- pollutant diagnostics before renovation

Why this wedge:
- legal obligation
- identifiable budgets
- strong information fragmentation
- direct path to structured data acquisition

Long-term expansion targets:
- renovation planning
- maintenance intelligence
- insurance and investment analytics
- broader building intelligence infrastructure

## Key Services

### risk_engine
Calculates pollutant probability scores for buildings based on construction year, materials, sample results, and geographic data. It is the seed of Evidence OS and future explainable risk outputs.

### compliance_engine
Evaluates diagnostic results against Swiss regulations:
- **CFST 6503** — Amiante (asbestos) directive
- **OLED** — Ordonnance on waste (demolition materials)
- **ORRChim** — Ordonnance on chemical risk reduction
- **ORaP** — Ordonnance on air pollution control

Returns pass/fail status per regulation with detailed findings. It is part of the future proof and playbook backbone.

### renovation_simulator
Estimates remediation costs based on pollutant type, surface area, building characteristics, and current market rates. This is the seed of future Portfolio OS and CAPEX arbitration flows.

### geospatial_service
Leverages PostGIS for spatial queries: proximity searches, heatmap generation, geographic clustering of at-risk buildings. This is the basis for future portfolio map steering.

---

## Document and Agentic Modules

### pdf_parser
Combines OCR and parsing to extract structured data from uploaded diagnostic PDF reports. It is the first step toward future agentic document workflows, but it should remain explainable and reviewable.

### risk_model
Predicts pollutant presence probability for buildings that have not yet been diagnosed, using building features and context. Its future role is not just prediction, but explainable contribution to proof-backed decisions.

## Platform Boosters

These tools are considered acceleration layers for the target architecture:

- Immediate:
  - `OCRmyPDF`
  - `Dramatiq + Redis`
  - `ClamAV`
- Near-term:
  - `Gotenberg`
  - `Meilisearch`
  - `GlitchTip`
- Conditional:
  - `Docling`
  - `PaddleOCR`

Explicitly not part of the near-term architecture:
- vector DB / RAG stack
- generic chatbot
- opaque AI features
- mandatory paid cloud OCR by default

Note: Remediation marketplace (mise en concurrence encadree) is validated as a new product surface sharing this architecture. See `docs/vision-100x-master-brief.md` for details.

---

## Observability

- **Metrics**: Prometheus-compatible endpoint at `/metrics` exposing request counts, latencies, error rates, and business metrics (diagnostics created, risk scores computed).
- **Logging**: Structured JSON logging via `structlog`. Every log entry includes `request_id`, `user_id`, and `timestamp` for traceability.

---

## Security

| Concern            | Implementation                              |
|--------------------|---------------------------------------------|
| Authentication     | JWT access + refresh tokens                 |
| Password storage   | bcrypt hashing with salt                    |
| Authorization      | RBAC enforced per endpoint                  |
| Input validation   | Pydantic schema validation on all inputs    |
| Rate limiting      | Per-IP and per-user rate limits on auth endpoints |
| Audit trail        | All mutations logged to `audit_logs`        |
