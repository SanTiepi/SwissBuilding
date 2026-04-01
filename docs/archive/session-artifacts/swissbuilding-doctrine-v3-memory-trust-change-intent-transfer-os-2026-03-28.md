# SwissBuilding Doctrine V3 — Building Memory, Trust, Change, Intent & Transfer OS

Date: 28 mars 2026
Supersedes: V2 (Memory + Trust + Action OS)
Status: Canonical internal doctrine

---

## Thesis

SwissBuilding is a canonical building memory system that observes, judges, transfers, and acts.

It is not a generic enterprise suite. It is not a document archive. It is not a compliance checkbox tool. It is not a marketplace.

It is the system that answers:

- what is true about this building
- what has changed
- what is missing
- what contradicts what
- what is ready, and for what
- what must happen next
- what can be transferred, to whom, with what proof

If the building had a living, trustworthy, transferable memory — this is what it would look like.

---

## What this doctrine is

- A product and architecture governance document
- The canonical north-star for all future SwissBuilding decisions
- A constraint system: it tells you what is allowed and what is forbidden
- A model lens: it defines the concepts the system is built around
- Binding for all agents, engineers, and product decisions operating on this repo

## What this doctrine is not

- Not a release scope or sprint plan
- Not a commercial deck or GTM copy
- Not a promise that every domain is exposed now
- Not a license to add disconnected modules
- Not a schema specification (types are conceptual, not field-level)

## Why V3 exists

V2 established Memory + Trust + Action as the core frame. V3 adds 4 missing capabilities that V2 lacked:

1. **Change** — a building is not just an object; it is a sequence of changes. Without an explicit change grammar, the system cannot distinguish observation from event from signal from delta.

2. **Intent** — the system must not only store and relate; it must answer. "Can I sell?", "Can I renovate?", "What blocks me?" are native product concepts, not UI features bolted on.

3. **Transfer sovereignty** — the building passport/dossier is not an export side-effect. It is a sovereign, versioned, receipted, role-redactable object that survives sale, handoff, diligence, and management change.

4. **Truth-family separation** — a document is not evidence. A claim is not a decision. A publication is not a draft. Collapsing these into one "file" category destroys the trust model.

V3 is intentionally stricter and more exclusionary than V2.

---

## Canonical Root Families

These are the only legitimate long-term anchors for SwissBuilding. No module, page, workflow, automation, or domain pack may become first-class unless it strengthens at least one root family.

### Building

**Definition**: The durable identity and continuity root.

Governs: EGID resolution, address, parcel, lifecycle, ownership chain, canonical identity.
Is not: a project, a dossier, or a tenant.
Examples: `Building`, `BuildingIdentity`, `BuildingLifecycleState`.

### Spatial

**Definition**: The physical structure of the building as a canonical graph.

Governs: zones, levels, spaces, rooms, elements, components, material layers, plan anchoring.
Is not: a cosmetic annotation layer or a plan viewer feature.
Examples: `SpatialScope`, `Zone`, `Level`, `Space`, `Element`, `MaterialLayer`.

Hard rule: no plan may remain a dead attachment in the long-term model. No building truth may remain purely abstract and non-spatial. Spatial truth is part of the canonical graph.

### Party

**Definition**: Any actor that interacts with the building or its cases.

Governs: organizations, contacts, roles, assignments, contributor quality, acknowledgments.
Is not: a CRM or a user directory.
Examples: `Party`, `PartyRole`, `ContributorProfile`, `AcknowledgmentRecord`.

### BuildingCase

**Definition**: The operating episode root. A bounded, time-limited engagement with the building.

Governs: works, permits, authority submissions, RFQ/tender, insurance claims, incidents, maintenance programs, funding/subsidy requests, transactions, due diligence, sale/transfer/handoff.
Is not: the building itself. A case is temporary; the building is permanent.
Examples: `BuildingCase`, `CaseType`, `CaseState`, `CaseStep`, `CaseScope`.

Why mandatory: without BuildingCase, the system cannot answer "is this diagnostic sufficient for THESE works?" A diagnostic exists independently; its value depends entirely on the case context.

### Artifact

**Definition**: The family of truth objects produced, consumed, or governed by the system.

Contains 5 irreducible sub-families:

#### Document
A source artifact. A file, report, plan, certificate, or form that exists as-is.
Is not: structured truth. A document is raw material.

#### Evidence
Structured, traceable, reusable truth derived from documents or observations.
Has: provenance, confidence score, extraction method, validation state.
Is not: a document. Evidence is what the system knows from documents.

#### Claim
An assertion about the building, case, or state. May be verified, contested, or superseded.
Has: author, basis, confidence, status (asserted/verified/contested/superseded).
Is not: a decision. A claim is proposed truth; a decision is governed truth.

#### Decision
A human or governed system-level choice recorded with authority.
Has: decision_maker, basis, date, scope, reversibility.
Is not: a claim. A decision has authority; a claim has an author.

#### Publication
A frozen, shareable, versioned, receipted, outward-facing state.
Has: version, hash, audience, delivery trace, redaction profile.
Is not: a draft. A publication is committed and traceable.

### Action

**Definition**: A concrete next step required to advance a case, resolve a gap, or fulfill an obligation.

Governs: action items, deadlines, assignments, resolution tracking, re-evaluation triggers.
Is not: a notification or a log entry.
Examples: `Action`, `ActionResolution`, `ActionTrigger`.

### OperationalFinance

**Definition**: Financial truth rooted in the building, case, and party graph.

Governs: costs, budgets, quotes, invoices, payments, obligations, subsidies.
Is not: a general ledger or a standalone accounting system.

Doctrine:
- Operational finance first
- Building-rooted
- Case-linked
- Journal-ready semantics early
- Full accounting doctrine only where truly needed

### Transfer

**Definition**: The sovereign movement of building truth between actors.

Governs: passport envelopes, dossier envelopes, transfer receipts, proof receipts, role-redaction, version control, re-import.
Is not: an export button. Transfer is a governed act with provenance and receipt.
Examples: `BuildingPassportEnvelope`, `BuildingDossierEnvelope`, `TransferReceipt`, `ProofReceipt`.

Hard rule: `BuildingPassportEnvelope` is a sovereign object. It must survive sale, handoff, diligence, insurer review, management change, and later re-import. It is versioned, receipted, role-redactable, and transferable.

### Change

**Definition**: The temporal dimension of building truth. A building is a sequence of changes, not a static snapshot.

Contains 4 irreducible sub-types:

#### Observation
A point-in-time reading or measurement. Has: observer, date, method, confidence.

#### Event
A significant occurrence that alters building state. Has: date, type, impact, source.

#### Delta
A computed difference between two states. Has: before, after, date_range, scope.

#### Signal
A pattern or anomaly detected from observations, events, or deltas. Has: type, severity, confidence, recommended_action.

Hard rule: the system must track what changed, when, why, and what it means — not just what exists now.

### Intent

**Definition**: The question-answering and decision-support dimension.

Contains 4 irreducible sub-types:

#### Intent
A human purpose that the system must serve. "I want to renovate." "I want to sell."

#### Question
A specific query the system must answer. "Is the diagnostic valid for this scope?" "What blocks the permit?"

#### DecisionContext
The assembled evidence, claims, rules, and constraints relevant to a decision.

#### SafeToXState
A governed readiness verdict. Safe to start, safe to tender, safe to sell, safe to insure, safe to transfer.
Has: verdict, reasons, blockers, conditions, provenance, confidence.
Is not: a score. It is a governed judgment with explicit basis.

Hard rule: the system must not only store and relate — it must answer. Every "safe to X" verdict must be explicable and traceable to its basis.

---

## Trust and Contradiction Doctrine

### 6 Confidence Levels

| Level | Name | Meaning |
|---|---|---|
| 1 | Source brute | Imported, not analyzed |
| 2 | Enrichi | AI-extracted, not human-validated |
| 3 | Valide | Expert confirmed |
| 4 | Publie | Published with hash and date |
| 5 | Herite | Reused from prior cycle, with provenance |
| 6 | Contradictoire | Two sources disagree on the same point |

### Contradiction grammar

Building memory is never clean. It is partial, contradictory, obsolete, inherited, and multi-source. The doctrine requires explicit handling of:

- **Conflict**: two sources disagree on the same fact
- **Supersession**: a newer source replaces an older one
- **Staleness**: a source has aged beyond its validity window
- **Coverage**: a source covers only part of the required scope
- **Unknown**: no source exists for a required fact

The system must never present contradictory data as resolved without human decision. The system must never hide staleness behind a clean interface.

### Non-negotiable trust rules

1. No verdict without explicable provenance
2. No AI-derived fact presented as equivalent to validated truth
3. No transfer without version, receipt, and provenance semantics
4. Readiness verdicts are always deterministic (rules), never probabilistic
5. AI proposes, human disposes, system traces who validated what and when

---

## Rituals of Truth

The system's institutional credibility comes from governed acts, not just data storage. These rituals are first-class:

| Ritual | Meaning |
|---|---|
| **Validate** | Expert confirms an extraction or claim |
| **Freeze** | Content is locked for a specific purpose |
| **Publish** | A versioned, hashed, receipted artifact is committed outward |
| **Transfer** | Building truth moves to a new actor with provenance |
| **Acknowledge** | A recipient confirms receipt of a publication or transfer |
| **Reopen** | A previously frozen or published state is reopened for revision |
| **Supersede** | A newer version explicitly replaces an older one |
| **Receipt** | A cryptographic or timestamped proof of delivery |

Each ritual must be traceable: who, when, what, why.

---

## Workspace Doctrine

### Top-level workspaces

| Workspace | Purpose | Entry frequency |
|---|---|---|
| **Today** | Daily operational start: what needs action now | Every day |
| **Building Home** | Durable memory/truth start: what is this building | Every interaction |
| **Case Room** | Bounded execution: manage a specific case | Per case |
| **Finance Workspace** | Operational finance: costs, budgets, obligations | Weekly/monthly |
| **Transfer / Passport** | Sovereign transfer: generate, version, deliver, receipt | Per transfer event |
| **Portfolio Command Center** | Director-level: prioritize, arbitrage, budget across buildings | Weekly/strategic |
| **Question / SafeToX** | Decision support: can I sell/renovate/insure/finance | Per question |

### UX doctrine

- `Today` and `Building Home` are dual primary entry points
- `Today` is operational (what do I do now)
- `Building Home` is memorial (what is true about this building)
- `Case Room` is where serious bounded execution happens
- One system does **not** mean one uniform interface
- Rejecting portal zoo does **not** mean rejecting specialized workspaces
- All actors use the same canonical system
- Permissions, redactions, CTAs, and depth vary by role
- No actor gets a parallel truth store
- No role-specific copy of the dossier becomes canonical

---

## Status Doctrine

### Base canonical grammar

Every status-bearing object in the system derives from this base grammar:

| Status | Meaning |
|---|---|
| `draft` | Created, not yet committed |
| `verified` | Reviewed and confirmed |
| `blocked` | Cannot proceed, reason attached |
| `ready` | All conditions met |
| `sent` | Transmitted to a recipient |
| `acknowledged` | Recipient confirmed receipt |
| `superseded` | Replaced by a newer version |
| `closed` | Terminal state, no further action |

### Family overlays

The base grammar may be extended with family-specific overlays where necessary:

- **Evidence**: raw → extracted → validated → published → inherited → contradictory
- **Case**: planned → in_preparation → ready → in_progress → completed → cancelled
- **Publication**: draft → frozen → published → delivered → acknowledged → superseded
- **Finance**: estimated → committed → invoiced → paid → reconciled
- **Readiness**: not_evaluated → not_ready → partially_ready → ready → degraded
- **Transfer**: preparing → frozen → sent → received → acknowledged → re-imported
- **SafeToX**: unknown → blocked → conditional → clear

No new status overlay may be introduced without explicit doctrine justification.

---

## First-Class Types

These types must be conceptually unambiguous and relationally clear. They do not require field-level schemas yet, but any future schema must be derivable from these definitions without inventing product semantics.

### Identity & Structure
- `Building` — durable identity root
- `SpatialScope` — the full spatial extent of a building
- `Zone` — a functional or physical subdivision (floor, facade, basement, technical room)
- `Level` — a vertical division (storey)
- `Space` — a room or bounded area within a level
- `Element` — a physical building component (wall, pipe, roof, window)

### Actors
- `Party` — any actor (organization, person, role)

### Cases
- `BuildingCase` — a bounded operating episode
- `CaseType` — works, permit, claim, incident, transfer, maintenance, funding, transaction
- `CaseState` — current lifecycle position
- `CaseStep` — a discrete milestone within a case

### Truth
- `Document` — a source artifact
- `ArtifactEnvelope` — metadata wrapper for any artifact (provenance, version, hash)
- `Evidence` — structured truth derived from sources
- `Claim` — an assertion about the building
- `Decision` — a governed choice with authority
- `Publication` — a frozen, versioned, receipted outward-facing state

### Change
- `Observation` — a point-in-time reading
- `Event` — a significant occurrence
- `Delta` — a computed difference between states
- `Signal` — a detected pattern or anomaly

### Intent
- `Intent` — a human purpose
- `Question` — a specific query
- `DecisionContext` — assembled basis for a decision
- `SafeToXState` — a governed readiness verdict

### Transfer
- `BuildingPassportEnvelope` — sovereign, versioned, transferable building passport
- `BuildingDossierEnvelope` — case-specific dossier package
- `TransferReceipt` — proof of transfer delivery
- `ProofReceipt` — proof of evidence delivery

### Action
- `Action` — a concrete next step

### Finance
- `OperationalFinancialEntry` — a financial fact rooted in building/case/party
- `JournalEntry` — a journal-ready accounting record

### Projections
- `TrustState` — current trust profile of a building or artifact
- `TodayFeedItem` — an item in the daily action feed
- `BuildingHomeProjection` — the assembled view of a building's current state
- `CaseRoomProjection` — the assembled view of a case's current state

---

## Prohibitions

The following are explicitly forbidden under V3 doctrine:

1. **Generic ERP drift** unrelated to buildings
2. **Domain mini-app sprawl** — no standalone calculator, viewer, or page that exists as an end in itself
3. **Dead-attachment plans** — no plan or document may remain a passive file without spatial or semantic anchoring
4. **Status sprawl** — no new status values without explicit doctrine justification
5. **AI-as-truth** — no AI-derived fact presented as equivalent to validated truth
6. **Receipt-less transfer** — no transfer without version, provenance, and receipt semantics
7. **Detached finance** — no financial entry disconnected from building, case, party, or obligation
8. **Disconnected modules** — no module that does not strengthen at least one canonical root family
9. **Portal zoo** — no parallel truth stores for different roles
10. **Recommendation** — no ranking of contractors, products, or services influenced by payment

---

## Core Doctrine vs Future Domain Packs

### Core doctrine (must be architecturally sound now)

- Root families
- Truth grammar (Document/Evidence/Claim/Decision/Publication)
- Change grammar (Observation/Event/Delta/Signal)
- Intent grammar (Intent/Question/DecisionContext/SafeToX)
- Workspace model
- Actor model
- Transfer/passport sovereignty
- Trust model (6 levels + contradiction grammar)
- Finance doctrine (operational-first, journal-ready)
- Rituals of truth
- Status doctrine (base + overlays)
- Rule of roots

### Future domain packs (must pass root-family test)

Each future pack must explicitly demonstrate which root families it strengthens.

| Domain Pack | Primary Roots Strengthened |
|---|---|
| Insurance | BuildingCase, OperationalFinance, Transfer |
| Claims | BuildingCase, Evidence, Change |
| Maintenance | BuildingCase, Spatial, Action, Change |
| Leases | Party, OperationalFinance, Building |
| Co-ownership | Party, Building, Decision |
| Vendor memory / SLA | Party, BuildingCase, Evidence |
| Public-owner modes | Party, Building, BuildingCase |
| Energy / carbon / live performance | Change, Spatial, Evidence |
| Partner network / ecosystem exchange | Party, Transfer, Evidence |
| Territory / district | Spatial, Building, Change |

A future domain pack that cannot name which roots it strengthens is not allowed.

---

## Repo Grounding Appendix

This doctrine does not exist in a vacuum. The repo already contains strong proto-OS ingredients. V3 exists to reduce conceptual sprawl and raise doctrinal severity.

### Prior substrate (not competing doctrines)

| Document | Role |
|---|---|
| `docs/architecture.md` | Technical architecture reference |
| `docs/blueprints/baticonnect-domain-blueprint.md` | Domain model inventory |
| `docs/blueprints/baticonnect-surface-blueprint.md` | Surface/UX inventory |
| `docs/blueprints/baticonnect-capability-blueprint.md` | Capability inventory |
| `docs/vision-100x-master-brief.md` | Long-term vision and category map |
| `docs/product-frontier-map.md` | Feature frontier and coverage assessment |
| `docs/projects/baticonnect-ultimate-product-manifesto-2026-03-28.md` | Product north-star (8 loops, 10 surfaces) |

### Relationship

- The manifesto describes what the product does
- The blueprints describe what exists
- V3 describes what the product IS and what it is NOT
- V3 is the preferred internal model lens going forward
- When the manifesto and V3 disagree on model semantics, V3 governs

---

## Summary

SwissBuilding is a building memory system that can observe, judge, transfer, and act.

It is built on 14 canonical root families. Every module must strengthen at least one. No module may exist as an end in itself.

It distinguishes 5 truth families, 4 change families, and 4 intent families. It governs 8 rituals of truth. It enforces 6 levels of confidence and an explicit contradiction grammar.

It is one canonical system with many role-native workspaces. It is not a portal zoo. It is not a generic ERP. It is not a document archive.

Its ultimate form is: the system that makes the building non-opaque, trustworthy, transferable, and actionable — for every actor, across every lifecycle stage.
