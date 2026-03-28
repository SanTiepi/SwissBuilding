# Doctrine V3 — Workspace Convergence Plan

Date: 28 mars 2026
Depends on: V3 Canonical Migration Plan, ADRs 001-006
Status: Active

---

## Goal

Converge SwissBuilding into a **single app shell with 5 hubs and contextual workspaces**. Make V3 doctrine legible in daily use. No new root families — reorganize existing page sprawl.

---

## App Shell — 5 Primary Hubs

| Hub | Route | Purpose |
|---|---|---|
| **Today** | `/today` | Daily triage, blockers, expiring truth, urgent actions |
| **Buildings** | `/buildings` | Registry, search, entry into Building Home |
| **Cases** | `/cases` | List/filter BuildingCases, entry into Case Room |
| **Finance** | `/finance` | Operational finance across building/case/party/obligation |
| **Portfolio** | `/portfolio-command` | Multi-building prioritization, command center |

### Contextual workspaces (NOT top-level nav)

| Workspace | Launched from | Responsibilities |
|---|---|---|
| **Transfer / Passport** | Building Home, Case Room | Sovereign envelope, freeze/publish/transfer/acknowledge, receipts |
| **Question / SafeToX** | Building Home, Case Room, Today | Governed question, basis/gaps/trust, intent + decision context |

### Universal shell elements
- Global search (Cmd+K)
- Notifications
- Role context
- Recent objects
- "Create case" quick action

---

## Building Home (evolve BuildingDetail)

Tabs/sections:
1. **Overview** — DossierJourney, action queue, predictive alerts
2. **Spatial** — zones, elements, plans, explorer (absorbs BuildingExplorer, BuildingPlans)
3. **Truth** — claims, decisions, evidence, trust state (absorbs BuildingDecisionView)
4. **Change** — timeline, observations, events, signals (absorbs BuildingTimeline)
5. **Cases** — linked BuildingCases, interventions
6. **Passport & Transfer** — envelope history, transfer receipts (contextual workspace)
7. **Questions** — SafeToX verdicts, intent queries (absorbs ReadinessWallet)

---

## Case Room (new canonical workspace)

Rooted in BuildingCase. Tabs/sections:
1. **Overview** — case state, scope, timeline, key metrics
2. **Scope** — spatial scope, pollutant scope, affected zones/elements
3. **Truth & Missing** — relevant evidence, claims, gaps, contradictions
4. **Actions & Rituals** — action queue, ritual history, validate/freeze/publish
5. **Forms & Packs** — applicable forms, generated packs, authority submissions
6. **Finance** — case-linked costs, quotes, budget
7. **Questions** — case-scoped SafeToX verdicts
8. **Transfer** — when case type requires it (handoff, sale)

Absorbs: BuildingInterventions, AuthoritySubmissionRoom, ComplianceArtefacts, AuthorityPacks, RFQ/forms/publications flows.

---

## Finance Workspace

Unifies:
- Operational financial entries (building-rooted, case-linked)
- Case-linked cost flows
- Budget/CAPEX
- Financial decisions
- Transfer-related financial redaction
- Insurer/lender-facing preparation (later)

NOT: a generic accounting app. Remains building-rooted and case-linked.

---

## Portfolio Command Center

Converges:
- Portfolio.tsx → absorb
- PortfolioCommand.tsx → canonical center
- PortfolioTriage.tsx → absorb
- BuildingComparison.tsx → keep as bounded internal view

The ONLY strategic multi-building center.

---

## Page Classification

### Canonical hubs
- Today.tsx
- BuildingDetail.tsx → Building Home
- PortfolioCommand.tsx

### Absorbed into master workspaces
| Page | Absorb into |
|---|---|
| BuildingExplorer.tsx | Building Home → Spatial |
| BuildingPlans.tsx | Building Home → Spatial |
| BuildingTimeline.tsx | Building Home → Change |
| ReadinessWallet.tsx | Building Home → Questions |
| BuildingDecisionView.tsx | Building Home → Truth |
| AuthorityPacks.tsx | Case Room → Forms & Packs |
| AuthoritySubmissionRoom.tsx | Case Room → Actions & Rituals |
| ComplianceArtefacts.tsx | Case Room → Actions & Rituals |
| BuildingComparison.tsx | Portfolio → bounded view |
| PortfolioTriage.tsx | Portfolio → absorb |
| Portfolio.tsx | Portfolio → absorb |
| Dashboard.tsx | Today → absorb |

### Keep as bounded specialist routes
- BuildingsList.tsx
- BuildingSamples.tsx
- Admin pages
- ExtractionReview.tsx
- ExportJobs.tsx

### Explicitly forbidden
New standalone top-level centers for: claims, signals, questions, decisions, publications, transfers, rituals. These must attach to Building Home, Case Room, Today, Finance, or Portfolio.

---

## Projection Families

| Projection | Consumed by | Source |
|---|---|---|
| TodayProjection | Today hub | Actions, signals, obligations, cases, changes |
| BuildingHomeProjection | Building Home | Passport, completeness, readiness, trust, cases, changes |
| CaseRoomProjection | Case Room | Case state, scope, actions, forms, finance, rituals |
| FinanceWorkspaceProjection | Finance hub | Financial entries, budgets, case costs |
| PortfolioCommandProjection | Portfolio hub | Building grades, readiness, priorities, budget horizon |
| SafeToXQuestionProjection | Contextual | DecisionContext, SafeToXState, claims, evidence |
| PassportTransferProjection | Contextual | Envelope, receipts, ritual history |

Rules:
- Workspaces consume projections, not ad hoc joins
- Projections are read-side only
- No page may re-derive canonical truth differently

---

## Convergence Passes

### Pass 1 — Shell
- Establish 5-hub navigation
- Remove nav ambiguity
- Mark contextual workspaces

### Pass 2 — Building Home
- Turn BuildingDetail into canonical memorial/truth workspace
- Absorb spatial, change, truth, passport entry points
- Implement Building Home tabs

### Pass 3 — Case Room
- Create case-rooted execution workspace
- Absorb authority/compliance/intervention/publication flows
- Implement Case Room tabs

### Pass 4 — Portfolio + Finance
- Converge strategic and financial views
- Stop scattering budget/cost/readiness across pages

### Pass 5 — Route cleanup
- Convert absorbed pages to internal tabs/panels
- Deprecate redundant standalone routes
- Document final state

---

## Acceptance

- User explains app shell in one sentence: "Today for actions, Buildings for truth, Cases for execution, Finance for money, Portfolio for strategy"
- From Today → blocked case in 2 clicks
- From Building Home → inspect truth/change/spatial + launch transfer/question without leaving
- From Case Room → execute rituals/forms/packs/finance without separate pages
- From Portfolio → drill to building or case cleanly
- No new top-level nav for change/truth/claims/decisions/transfer/rituals/safe-to-x
