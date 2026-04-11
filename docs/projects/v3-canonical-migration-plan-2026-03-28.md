# Doctrine V3 — Canonical Migration Plan

Date: 28 mars 2026
Source: Codex migration doctrine
Status: Active — governs all future work

---

## Goal

V3 roots become the **only place where new semantics are born**.
Legacy objects remain only as temporary projections, adapters, or compatibility surfaces.
No new feature work lands in legacy models/services unless it is explicitly migration support.

## Migration Posture

- Do **not** force destructive migration where data migration is risky
- Do **freeze** legacy semantics immediately
- Do **bridge** old read paths to canonical V3 roots
- Do **deprecate** standalone legacy centers once equivalent V3 projections exist

---

## Canonicalization Matrix

### Canonical write-side (V3 roots — all new semantics here)

| Object | File | Root Family |
|---|---|---|
| BuildingCase | `models/building_case.py` | BuildingCase |
| BuildingObservation | `models/building_change.py` | Change |
| BuildingEvent | `models/building_change.py` | Change |
| BuildingDelta | `models/building_change.py` | Change |
| BuildingSignal | `models/building_change.py` | Change |
| BuildingClaim | `models/building_claim.py` | Artifact/Claim |
| BuildingDecision | `models/building_claim.py` | Artifact/Decision |
| BuildingIntent | `models/building_intent.py` | Intent |
| BuildingQuestion | `models/building_intent.py` | Intent |
| DecisionContext | `models/building_intent.py` | Intent |
| SafeToXState | `models/building_intent.py` | Intent |
| BuildingPassportEnvelope | `models/passport_envelope.py` | Transfer |
| PassportTransferReceipt | `models/passport_envelope.py` | Transfer |
| TruthRitual | `models/truth_ritual.py` | Trust (transversal) |

### Subordinate domain objects (keep, attach to V3 roots)

| Object | Attaches to |
|---|---|
| Intervention | BuildingCase (via case.intervention_id) |
| TenderRequest / TenderQuote | BuildingCase (via case.tender_id) |
| FormTemplate / FormInstance | BuildingCase + Building |
| ComplianceArtefact | BuildingCase + rituals |
| InsurancePolicy / Claim (domain) | BuildingCase + OperationalFinance |
| Lease / Contract | Building + Party |
| ProofDelivery | Transfer + rituals |
| EvidencePack / authority packs | Publication (via PackBuilder) |

Rule: these remain valid domain objects but must attach to Building + BuildingCase + canonical truth/publication/transfer semantics.

### Compatibility surfaces (frozen, no new semantics)

| Object | Bridge | Future |
|---|---|---|
| ChangeSignal | change_tracker_service bridges to BuildingSignal | Migrate consumers, then retire |
| change_signal_generator.py | detect_signals() in change_tracker_service | Wrapper, then retire |
| api/change_signals.py | Compatibility reads only | Freeze schema, no expansion |

Rule: no new product meaning may be introduced in a compatibility surface.

---

## API Compatibility Doctrine

| Family | Status | Rule |
|---|---|---|
| building_cases | **Canonical** | All new case semantics here |
| building_changes | **Canonical** | All new change semantics here |
| building_truth | **Canonical** | All new claim/decision semantics here |
| intents | **Canonical** | All new intent/safetox semantics here |
| passport_envelopes | **Canonical** | All new transfer semantics here |
| rituals | **Canonical** | All truth transitions here |
| change_signals | **Compatibility** | Frozen, no new routes, no schema expansion |
| Legacy routes | **Subordinate** | May stay stable but only as translation layers |

Rules:
- Translation layers map FROM canonical V3 roots OUTWARD, never the reverse
- Compatibility endpoints may preserve old response shapes but must not invent new state machines
- New consumers must not be pointed at legacy compatibility endpoints

---

## Workspace Migration

### Canonical product centers (absorb everything)

| Workspace | Page | Absorbs |
|---|---|---|
| Today | `Today.tsx` | Daily actions, predictive alerts, signals |
| Building Home | `BuildingDetail.tsx` | DossierJourney, packs, forms, life, changes, truth, intent |
| Case Room | Future (via BuildingCase) | Intervention detail, tender detail, permit procedure |
| Finance Workspace | Future | Financial entries, budgets, obligations |
| Transfer / Passport | PassportEnvelope views | Transfer packages, authority packs, receipts |
| Portfolio Command | `PortfolioCommand.tsx` | Portfolio analytics, comparisons, heatmap |

### Temporary standalone centers (must converge)

| Page | Future State |
|---|---|
| ChangeSignals.tsx | **Absorb** into Building Home (change timeline) |
| ReadinessWallet.tsx | **Absorb** into Building Home (DossierJourney) |
| AuthorityPacks.tsx | **Keep bounded** under Transfer workspace |
| BuildingTimeline.tsx | **Absorb** into Building Home |
| BuildingComparison.tsx | **Keep bounded** under Portfolio Command |

Rule: each temporary center must end in one of 3 states:
1. Absorbed into a master workspace
2. Kept as a bounded specialist view
3. Deprecated and removed

Forbidden: new standalone product centers for each V3 root family.

---

## Migration Passes (execution order)

### Pass 1 — Canonical freeze (immediate)
- Label all canonical roots in code comments
- Label all compatibility surfaces
- Label deprecated product centers
- Write ADRs (see below)
- No new features in legacy models

### Pass 2 — Change compatibility
- Inventory every consumer of ChangeSignal
- Classify: keep temporarily / migrate soon / replace entirely
- Route all future change semantics through canonical change objects
- Keep bridge for existing consumers

### Pass 3 — Workspace convergence
- Move change/truth/intent/passport views under Building Home, Today, or Case Room
- Stop creating new standalone centers
- Absorb ReadinessWallet, ChangeSignals, BuildingTimeline into Building Home

### Pass 4 — API cleanup
- Document canonical vs compatibility routes
- Stop expanding compatibility schemas
- Move new frontend/API consumers to canonical surfaces only

### Pass 5 — Debt retirement
- Once consumer inventory is near-zero:
  - Migrate ChangeSignal data to BuildingSignal
  - Retire redundant standalone centers
  - Consolidate old helper services

---

## Required ADRs

| ADR | Decision |
|---|---|
| V3 Canonical Roots | Lists the 14 root families. No module becomes first-class without root test. |
| BuildingCase as Operating Root | BuildingCase is the integration point for change, truth, intent, transfer. |
| TruthRitual as Sole Transition Layer | All freeze/publish/acknowledge/supersede/reopen/receipt goes through ritual_service. |
| ChangeSignal Compatibility | ChangeSignal is frozen. BuildingSignal is canonical. Bridge maintained until retirement. |
| Dual Primary Entry Points | Today (operational) + Building Home (memorial). No third primary. |
| Projection vs Canonical Truth | Pages are projections. Only models are canonical. No page may own truth behavior. |

Each ADR must state: the decision, what is allowed, what is forbidden, which old objects are compatibility-only, what triggers future removal.

---

## Validation

The migration is correct only if:

- No new semantic feature lands in ChangeSignal
- ritual_service is the only place where truth transitions are authored
- Canonical V3 objects remain the source of new state and meaning
- Legacy routes can be maintained without becoming the design center
- Each standalone page has an explicit future state (absorb/keep/deprecate)
- New frontend work targets master workspaces first
- Another engineer can tell, for any object/service/page, whether it is canonical, subordinate, compatibility-only, or deprecated
