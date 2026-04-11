# SwissBuilding — Master Future Steps Plan

Date: 28 mars 2026
Status: Canonical roadmap — governs all future work sequencing
Depends on: Doctrine V3, Migration Plan, ADRs, Workspace Convergence, Projection/Redaction, Source Exploitation

---

## Target State

- One canonical building system
- One active memory and trust layer
- One spatially anchored graph
- One case-driven execution model
- One safe-to-x / question layer
- One sovereign passport/transfer layer
- One role-native app shell
- One building-centered ERP-grade platform without generic ERP drift

## Always-On Guardrails

- No new root outside canonical families
- No new top-level surface outside Today, Buildings, Cases, Finance, Portfolio
- No truth/publication/transfer transition outside ritual_service
- No new semantics in legacy compatibility layers
- No source integration without provenance, freshness, and workspace destination
- No procedure logic that lives only in UI flows
- No full generic ERP, full BIM authoring, full insurer stack, or full lender stack

---

## Phase A — Canonical Freeze + Workspace Convergence

### Step 1: Canonical Freeze and ADR Hardening
- Finalize canonical classification of every model/service/page
- Freeze ChangeSignal as compatibility-only
- Lock ADR set
- **Gate**: any engineer can classify any object as canonical/subordinate/compatibility/deprecated

### Step 2: Workspace Convergence
- Finish 5-hub shell (Today, Buildings, Cases, Finance, Portfolio)
- Turn Building Home into durable truth/memory surface
- Turn Case Room into bounded execution surface
- Absorb standalone views under master workspaces
- **Gate**: no new top-level nav needed for signals/decisions/transfer/rituals/claims/safe-to-x

## Phase B — Projection/Redaction + Public Source Backbone

### Step 3: Projection, Role View, and Redaction Registry
- Formalize 7 canonical projections
- Register all projections; forbid ad hoc page-owned read models
- Finalize role-native view and redaction doctrine
- **Gate**: same building shown safely to multiple actors without truth forks

### Step 4: Public Source Backbone
- Build address → EGID → EGRID → RDPPF identity chain
- Expand national MADD/RegBL, swissBUILDINGS3D, geo.admin overlays
- Make public context visible in Building Home, Case Room, SafeToX, Passport
- Replace heuristics where public sources exist
- **Gate**: pilot building shows auditable identity/parcel/spatial/context truth with provenance

## Phase C — Procedure OS + Trade Matrix + Freshness

### Step 5: Procedure OS for All Layers
- Introduce canonical procedure grammar (ProcedureTemplate, ProcedureVariant, ProcedureStep, etc.)
- Cover federal/cantonal/communal/authority/utility/site/owner layers
- Make procedures native to BuildingCase
- **Gate**: a case shows what applies, what blocks, who must act, through which route

### Step 6: Work-Family and Trade Matrix
- Define neutral work-family matrix for all corps de metier
- Map each to procedure context, authorities, forms, proof, contractor categories
- Extend RFQ/contractor/handoff beyond pollutants
- **Gate**: several non-pollutant work families have end-to-end pathways

### Step 7: Freshness and Delta Intelligence
- Turn SwissRules Watch into broader update intelligence
- Add impact reactions: blocker refresh, template invalidation, case reopen
- **Gate**: a source/procedure/form change triggers concrete system reaction

## Phase D — Passport/Transfer + Finance/Insurance/Transaction

### Step 8: Passport, Transfer, and Exchange Standard
- Harden PassportEnvelope as sovereign, diffable, receipted exchange object
- Machine-readable export/import, not PDF-only
- Selective openBIM/digital logbook alignment
- **Gate**: passport survives sale, handoff, insurer/lender review, re-import

### Step 9: Finance, Insurance, and Transaction Readiness
- Extend readiness to safe_to_sell, safe_to_insure, safe_to_finance
- Keep finance building-rooted, case-linked
- Bounded projections for insurer/lender/notary/buyer
- **Gate**: building credibly prepared for sale/underwriting/financing

## Phase E — Post-Works + Owner Ops + Portfolio Intelligence

### Step 10: Post-Works Truth and Building Operations
- Close pre-work → works → post-works truth loop
- Recurring ops: warranties, maintenance, services, incidents, claims
- Post-works truth as major trust update
- **Gate**: what changed/removed/remains/requalified shown in one memory chain

### Step 11: Owner Ops and Everyday Building Memory
- Owner operating layer: vault, budgets, insurance ops, renewal calendars
- Building-rooted, evidence-linked, not consumer-finance drift
- **Gate**: owner knows what building is, what's due, what's risky, what's next

### Step 12: Portfolio Intelligence and Campaign Operating Model
- Many buildings → one decision surface
- CAPEX timing, campaign design, budget-at-risk, procedural blockers
- Proof-grounded, not generic BI
- **Gate**: property manager arbitrates timing/risk/budget across assets

## Phase F — Network, Standards, and Ecosystem

### Step 13: Network, Standards, and Ecosystem Layer
- Partner trust, contributor quality, APIs, exchange contracts
- Passport exchange, reusable evidence chains, network effects
- **Gate**: SwissBuilding behaves as market infrastructure, not just local app

---

## Cross-Cutting Systems (progress in parallel)

| System | Requirement |
|---|---|
| Trust and rituals | Validate/freeze/publish/acknowledge/transfer/receipt/supersede/reopen stay canonical |
| Testing | Golden-path scenarios per phase, not just unit coverage |
| AI discipline | ai_generated flags, correction loops, no opaque verdicts, deterministic promotion |
| Source governance | Class, freshness, fallback, license, workspace destination per source |
| Procedure governance | Explainable by layers, variants, forms, proof sets, blockers |
| Projection governance | No page invents business semantics because a projection is missing |

---

## Phase Progression Gates

No later phase should broaden scope if current gate is not met.

```
Phase A → Phase B → Phase C → Phase D → Phase E → Phase F
```

**Global success signal**: SwissBuilding can explain a building, operate a case, absorb source changes, prepare audiences, transfer truth, and accumulate memory without creating module sprawl, truth duplication, or opaque workflow logic.
