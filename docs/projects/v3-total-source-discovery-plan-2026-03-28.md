# SwissBuilding — Total Source Discovery & Exploitation Plan

Date: 28 mars 2026
Supersedes: v3-source-exploitation-program (which covered Wave 1 only)
Status: Canonical source strategy

---

## Objective

Build the full map of every exploitable source, every procedure, every refresh mechanism, and every workspace consumer. End state: one canonical source registry, one priority-ranked exploitation map.

---

## Source Universe — 8 Families

### Family A — Public Official Identity & Parcel

| Source | Circle | Access | Trust | Priority |
|---|---|---|---|---|
| Address search (geo.admin) | 1 | API | canonical identity | Now |
| EGID (RegBL/GWR) | 1 | API/bulk | canonical identity | Now |
| EGRID (cadastral) | 1 | API | canonical identity | Now |
| RDPPF (restrictions) | 1 | API | canonical constraint | Now |
| MADD public (national) | 1 | WFS/GeoJSON | canonical identity | Now |
| Parcel/cadastral services | 1 | API | canonical identity | Next |

### Family B — Public Spatial & Territorial Context

| Source | Circle | Access | Trust | Priority |
|---|---|---|---|---|
| swissBUILDINGS3D 3.0 | 1 | Download | observed context | Next |
| Footprints/geometry | 1 | WMS | observed context | Next |
| Zoning/land use | 1 | WMS/API | canonical constraint | Next |
| Heritage/ISOS/monuments | 1 | WMS | canonical constraint | Next |
| Hazards (flood/landslide/seismic) | 1 | WMS | canonical constraint | Next |
| Groundwater/water protection | 1 | WMS | canonical constraint | Next |
| Contaminated sites | 1 | WMS | canonical constraint | Next |
| Noise (road/rail/aviation) | 1 | WMS | observed context | Done |
| Solar roof suitability | 1 | API | observed context | Later |
| Public transport quality | 1 | WMS | observed context | Done |
| Thermal networks | 1 | WMS | observed context | Done |
| Radon map | 1 | WMS | canonical constraint | Done |
| Climate/MeteoSwiss | 1 | API | observed context | Later |

### Family C — Rules, Procedures, Forms, Authority Channels

| Source | Circle | Access | Trust | Priority |
|---|---|---|---|---|
| Federal legal anchors (OTConst, CFST, ORRChim, OLED, ORaP) | 1 | Manual/structured | canonical constraint | Done (rule_resolver) |
| Cantonal permit portals (FRIAC, eConstruction) | 1 | Portal/API | canonical constraint | Next |
| Communal procedure variants | 1 | Manual | canonical constraint | Later |
| Authority forms/filing requirements | 1 | Download | canonical constraint | Next |
| Utility/concession approval sources | 1 | Portal | supporting evidence | Later |
| Waste/pollutant/fire/accessibility/energy procedure sources | 1 | Manual/portal | canonical constraint | Next |
| Subsidy/tax incentive programs (cantonal) | 1 | Portal/API | supporting evidence | Now |

### Family D — Standards & Quasi-Official Ecosystem

| Source | Circle | Access | Trust | Priority |
|---|---|---|---|---|
| GEAK/CECB (energy performance) | 2 | Portal/partner | supporting evidence | Later |
| Minergie certification | 2 | Portal | supporting evidence | Later |
| openBIM/IFC/BCF/IDS/bSDD | 2 | File import | supporting evidence | Later |
| Digital building logbook direction | 2 | Standard | supporting evidence | Later |
| Renovation passport (EU direction) | 2 | Standard | supporting evidence | Later |

### Family E — Commercial & Open Ecosystem

| Source | Circle | Access | Trust | Priority |
|---|---|---|---|---|
| Street imagery/Mapillary | 2 | API | commercial hint | Later |
| Mobility/amenity/market context | 2 | API | commercial hint | Later |
| Contractor/supplier reference | 2 | Partner | commercial hint | Later |
| Pricing/benchmark feeds | 2 | License | commercial hint | Later |

### Family F — Proprietary / Partner / Account-Fed

| Source | Circle | Access | Trust | Priority |
|---|---|---|---|---|
| ERP/accounting exports | 3 | File/API | partner-fed | Next |
| Contracts/leases/invoices | 3 | Upload | partner-fed | Exists (models) |
| Insurer systems/claims/underwriting | 3 | Partner | partner-fed | Later |
| Lender/diligence/transaction data rooms | 3 | Partner | partner-fed | Later |
| Notary/transfer/ownership evidence | 3 | Partner | partner-fed | Later |
| FM/CMMS/SLA/maintenance systems | 3 | Partner | partner-fed | Later |
| Utility bills/recurring services | 3 | Upload/API | partner-fed | Later |

### Family G — Live Building & Recurring Operations

| Source | Circle | Access | Trust | Priority |
|---|---|---|---|---|
| Meters (energy/water) | 3 | API/upload | observed context | Later |
| BMS/GTB/sensor feeds | 3 | API | observed context | Later |
| Energy/carbon/indoor environment | 3 | API | observed context | Later |
| Recurring service events | 3 | Upload | partner-fed | Later |
| Maintenance/incident streams | 3 | Upload | partner-fed | Later |
| Warranty/renewal signals | 3 | Upload | partner-fed | Later |

### Family H — Document-Native Incoming Evidence

| Source | Circle | Access | Trust | Priority |
|---|---|---|---|---|
| Diagnostic reports (6 pollutants) | 3 | Upload → extraction | supporting evidence | Done |
| Plans (architectural/situation) | 3 | Upload | supporting evidence | Exists |
| Permits/authority decisions | 3 | Upload → extraction | canonical constraint | Next |
| Authority complement requests | 3 | Upload | canonical constraint | Next |
| Quotes/devis | 3 | Upload → extraction | supporting evidence | In progress |
| Contracts/policies/claims | 3 | Upload | partner-fed | Exists (models) |
| Invoices/tax documents | 3 | Upload | partner-fed | Later |
| Handover/post-works/guarantees | 3 | Upload | supporting evidence | Exists |
| PV/minutes/emails/photos | 3 | Upload | supporting evidence | Later |

---

## Source → Canonical Object Map

| Source Family | Building | Spatial | Party | Case | Evidence | Claim | Decision | Finance | Transfer | Change | Intent |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A (Identity) | X | X | | | | | | | X | | |
| B (Spatial context) | X | X | | | X | | | | | X | X |
| C (Procedures) | | | | X | | | X | | | | X |
| D (Standards) | | X | | | X | | | | X | | X |
| E (Commercial) | | X | | | | | | | | | |
| F (Partner-fed) | | | X | X | X | | | X | X | | |
| G (Live ops) | | X | | | X | | | X | | X | |
| H (Documents) | X | X | X | X | X | X | X | X | X | X | X |

---

## Source → Workspace Map

| Source Family | Today | Building Home | Case Room | Finance | Portfolio | Passport | SafeToX |
|---|---|---|---|---|---|---|---|
| A (Identity) | | X | | | | X | |
| B (Spatial context) | | X | X | | X | X | X |
| C (Procedures) | X | | X | | | | X |
| D (Standards) | | X | | | | X | X |
| E (Commercial) | | X | | | X | | |
| F (Partner-fed) | X | X | X | X | X | X | X |
| G (Live ops) | X | X | | X | X | | |
| H (Documents) | X | X | X | X | | X | X |

---

## Work-Family × Source Coverage

| Work Family | Procedure Source | Authority | Forms | Proof Required | Priority |
|---|---|---|---|---|---|
| Pollutants/remediation | OTConst, CFST, ORRChim | SUVA, canton | SUVA notification, waste plan, cantonal declaration | Diagnostic, waste plan, SUVA form | Done |
| Demolition | Permit cantonal | Canton, commune | Demolition permit | Diagnostic, permit | Next |
| Structure | Permit cantonal | Canton, engineer | Building permit | Engineer report, permit | Later |
| Roof/facade/envelope | Permit if heritage | Canton, heritage | Heritage review if ISOS | Diagnostic if pre-1990, permit | Next |
| HVAC/ventilation | Energy regulations | Canton | Energy declaration | GEAK if applicable | Later |
| Electrical | NIBT/ESTI | ESTI, concessionaire | Installation attestation | Compliance cert | Later |
| Plumbing/sanitary | Cantonal health | Health authority | Sanitary declaration | Compliance cert | Later |
| Fire safety | AEAI/cantonal | Fire authority | Fire safety concept | Fire report | Later |
| Accessibility | SIA 500, LHand | Canton | Accessibility concept | Assessment | Later |
| Energy renovation | MoPEC, cantonal | Canton, energy office | Energy declaration, GEAK | CECB, energy audit | Next |
| Waterproofing | SIA norms | — | — | Assessment | Later |
| Maintenance/service | Contract-based | — | — | SLA, maintenance log | Later |
| Insurance/claims | Contract-based | Insurer | Claim form | Incident report, photos | Later |
| Transaction/transfer | Notary, land registry | Land registry | Sale contract | Due diligence pack | Next |
| Subsidy/funding | Cantonal programs | Canton, federal | Subsidy application | Project docs, energy audit | Now |

---

## Freshness & Watch Model

| Source Family | Watch Tier | Delta Types | Reaction |
|---|---|---|---|
| A (Identity) | Quarterly | dataset_refresh | Identity re-check |
| B (Spatial context) | Monthly | dataset_refresh | Context overlay refresh |
| C (Procedures) | Weekly/monthly | new_rule, amended_rule, form_change, portal_change | Template invalidation, blocker refresh, safe-to-x re-eval |
| D (Standards) | Quarterly | schema_change, new_rule | Pack review |
| F (Partner-fed) | Event-driven | new data | Truth update, consequence chain |
| G (Live ops) | Real-time/daily | new data | Performance update |
| H (Documents) | Event-driven | new document | Full consequence chain |

---

## Heuristic Replacement Matrix

| Module | Current | Target | Priority |
|---|---|---|---|
| Radon risk | Heuristic (canton bucket) | **Source-backed** (geo.admin — Done) | Done |
| Subsidy/funding eligibility | Hardcoded programs | **Source-backed** (cantonal data) | Now |
| Environmental exposure | Heuristic | **Hybrid** (geo.admin + heuristic) | Next |
| Procedure blockers | Rule-based | **Hybrid** (rule + public context) | Next |
| Transfer/tax preparation | Assumption-based | **Derived, marked clearly** | Later |
| Energy performance | Not implemented | **Source-backed** (GEAK/CECB) | Later |
| Market context | Not implemented | **Commercial, marked clearly** | Later |

---

## Now / Next / Later / Partner-Gated Roadmap

### Now (implemented or in progress)
- EGID resolution (Done)
- MADD/Vaud public import (Done)
- geo.admin 10 overlays (Done)
- Identity chain EGID→EGRID→RDPPF (In progress)
- Diagnostic extraction 6 pollutants (Done)
- Quote extraction (In progress)
- Consequence engine (In progress)
- Federal rules (rule_resolver — Done)
- Subsidy programs VD (prioritized)

### Next
- swissBUILDINGS3D spatial deepening
- Cantonal permit portal integration (FRIAC, eConstruction)
- Authority document extraction (permits, decisions)
- ERP/accounting import adapters
- Heritage/ISOS constraint overlay
- Hazard overlay (flood, landslide, seismic)
- Energy renovation procedure sources

### Later
- GEAK/CECB/Minergie integration
- BIM/IFC spatial import
- Insurer/lender partner connectors
- Live sensor/meter feeds
- Street imagery classification
- FM/CMMS integration
- Market/benchmark feeds

### Partner-Gated
- Insurer underwriting inputs
- Lender diligence data rooms
- Notary transfer evidence
- Utility billing feeds
- Contractor quality/SLA data

---

## Acceptance

- One exhaustive source inventory (this document)
- Every source has status, priority, workspace destination
- Every work family has first-pass source/procedure mapping
- At least one example in each circle (Done: Circle 1 = geo.admin, Circle 3 = diagnostic upload)
- New source can be added without inventing new provenance/workspace/procedure model
- Any heuristic-heavy area has explicit classification (source-backed / hybrid / derived-only)
