# Doctrine V3 — Projection, Role View & Redaction

Date: 28 mars 2026
Depends on: Workspace Convergence Plan, ADR-006 (Projection vs Canonical Truth)
Status: Planned — defines read-side governance

---

## Purpose

Define how SwissBuilding is **read**, **filtered**, and **shared** without creating parallel truths. One canonical write-side, many role-bounded read-sides.

---

## Projection Vocabulary

| Term | Definition |
|---|---|
| **Projection** | Read-side assembly from canonical roots. Never owns truth. |
| **Workspace Projection** | The canonical projection serving one master workspace. |
| **Audience View** | A role-bounded variant of a projection. Same truth, different depth/visibility. |
| **Redaction Profile** | Named, inspectable filter that controls what is visible in a shared artifact. Changes visibility, never truth. |
| **Bounded Externalization** | A frozen, receipted, redacted subset of a projection shared outside the system. |

### Hard Rules

- Projections are read-side only
- Projections never become canonical truth
- No business rule may live only in a page or ad hoc frontend composition
- Projections must assemble from canonical roots, not invent a new object model
- Redaction changes visibility, never truth
- One canonical system != one uniform projection

---

## Canonical Projection Families

| Projection | Workspace | Reads From | Redaction Layer |
|---|---|---|---|
| **TodayProjection** | Today | Actions, cases, signals, obligations, expiring objects, transfers, questions | None (internal) |
| **BuildingHomeProjection** | Building Home | Building, spatial, truth, change, passport, case summaries, questions | Role-based depth |
| **CaseRoomProjection** | Case Room | Case, scope, truth, actions, rituals, forms/packs, finance links, questions | Case-scope |
| **FinanceWorkspaceProjection** | Finance | Building/case/party/obligation/publication-linked finance only | Financial redaction |
| **PortfolioCommandProjection** | Portfolio | Building grades, readiness, priorities, budget horizon, risk | Aggregated (no detail) |
| **PassportTransferProjection** | Contextual | Frozen envelope state, receipts, redaction metadata | Full redaction profiles |
| **SafeToXQuestionProjection** | Contextual | Intent, question, decision context, trust, evidence, claims, decisions, changes | Basis transparency |

### What each projection is NOT allowed to own

- TodayProjection: must not store actions (canonical source is ActionItem)
- BuildingHomeProjection: must not store truth (canonical source is Claim/Decision/Evidence)
- CaseRoomProjection: must not duplicate case state (canonical source is BuildingCase)
- PassportTransferProjection: must not modify the envelope (use ritual_service)

---

## Role-Native Views

### Role Families

| Role | Primary Workspaces | Max Depth | Default Hidden |
|---|---|---|---|
| **Owner** | Building Home, Portfolio | Medium | Technical details, internal notes |
| **Regie / Property Manager** | Today, Building Home, Cases, Portfolio | Full | Nothing |
| **Technical Operator (RT)** | Today, Building Home, Cases | Full | Finance aggregates |
| **Diagnostician / Expert** | Building Home (spatial, truth) | Domain-specific | Cases, finance, portfolio |
| **Contractor / Vendor** | Case Room (scope, packs) | Case-bounded | Other cases, finance, portfolio |
| **Insurer** | Building Home (risk, truth) | Redacted | Financial detail, internal notes |
| **Lender / Buyer / Diligence** | Building Home, Transfer | Redacted | Internal operations |
| **Authority** | Case Room (submissions, packs) | Submission-bounded | Internal actions, finance |
| **Notary / Transfer Actor** | Transfer workspace | Envelope-bounded | Operational detail |

### Access modes

| Mode | Description |
|---|---|
| **Authenticated** | Full user with role-based permissions |
| **Tokenized** | External actor with limited-scope access token (contractor, authority) |
| **Internal-only** | Never shared outside the organization |

### Hard Rule

- No role gets a separate canonical dossier copy
- No portal-specific projection may become the design center
- Role views are bounded variants of canonical projections

---

## Redaction Doctrine

### Redaction Profiles

| Profile | What is hidden | Use case |
|---|---|---|
| `none` | Nothing | Internal use |
| `financial` | Amounts, quotes, budgets, cost comparisons | Transfer to buyer, public sharing |
| `personal` | Contact details, personal data | External sharing |
| `internal_notes` | Internal comments, operator notes | Authority/insurer packs |
| `authority_safe` | Financial + personal + internal | Authority submission |
| `insurer_safe` | Personal + internal, financial visible | Insurance preparation |
| `contractor_safe` | Other cases + portfolio + finance | Contractor execution scope |
| `transfer_safe` | Configurable per transfer (financial optional) | Sale, handoff, management change |

### Rules

- Redaction applies at projection/publication time
- Redaction profiles are named and inspectable
- Each publication records which redaction profile was used
- Role access and shared-link access are related but not identical
- Transfer and publication history preserve both canonical origin and exposed subset

### Existing hooks (already implemented)

- `pack_builder_service.py` — `redact_financials` parameter
- `authority_pack_service.py` — `redact_financials` parameter
- `transfer_package_service.py` — `redact_financials` parameter
- `passport_envelope_service.py` — `redaction_profile` field
- `BuildingPassportEnvelope` — `financials_redacted`, `personal_data_redacted`

---

## Projection Registry

Every projection must be registered:

| Field | Description |
|---|---|
| `name` | Projection name |
| `canonical_source_roots` | Which root families it reads |
| `primary_workspace` | Which workspace consumes it |
| `intended_audience` | Role families served |
| `redaction_compatibility` | Which profiles can apply |
| `owner_service` | Backend service/facade that produces it |
| `status` | canonical / bounded / compatibility / deprecated |

### Anti-Sprawl Rule

No new aggregate endpoint or page-level composition is allowed unless registered as:
- Canonical projection
- Bounded specialist projection
- Compatibility projection

### Current read-side services classification

| Service | Classification | Target Projection |
|---|---|---|
| `today_service` | **Canonical** | TodayProjection |
| `portfolio_command_service` | **Canonical** | PortfolioCommandProjection |
| `passport_envelope_service` (read) | **Canonical** | PassportTransferProjection |
| `intent_service.get_safe_to_x_summary` | **Canonical** | SafeToXQuestionProjection |
| `building_life_service` | **Bounded** | BuildingHomeProjection (calendar section) |
| `predictive_readiness_service` | **Bounded** | TodayProjection + BuildingHomeProjection |
| `action_queue_service` | **Bounded** | BuildingHomeProjection (actions section) |
| `pack_builder_service` (read) | **Bounded** | PassportTransferProjection |
| `building_comparison_service` | **Bounded** | PortfolioCommandProjection |
| `building_dashboard_service` | **Compatibility** | → absorb into BuildingHomeProjection |
| `portfolio_summary_service` | **Compatibility** | → absorb into PortfolioCommandProjection |
| `completion_workspace_service` | **Compatibility** | → absorb into BuildingHomeProjection |
| `shared_link_service` | **Bounded** | Externalization |

---

## Passes

### Pass 1 — Doctrine
- Define vocabulary, projection families, role rules, redaction doctrine, registry format
- **This document = Pass 1 done**

### Pass 2 — Inventory
- Classify all existing read services
- Map each to canonical/bounded/compatibility/deprecated

### Pass 3 — Workspace mapping
- Map each workspace to its canonical projection
- Map old pages to absorbed/bounded/deprecated

### Pass 4 — Governance
- ADRs for projection registry, role views, redaction profiles, publication-safe projections
- Block ad hoc read-side sprawl

---

## Acceptance

- Every master workspace has exactly one canonical projection family
- Every role is a bounded view over those projections
- Redaction is explicit, profile-driven, never changes truth
- Transfer/passport exposure is explainable and receiptable
- Same building shown safely to owner, authority, insurer, contractor without dossier duplication
- New page request can be rejected if canonical projection already covers the need
