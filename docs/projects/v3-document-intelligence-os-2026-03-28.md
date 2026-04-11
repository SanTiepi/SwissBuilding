# SwissBuilding — Document Intelligence OS for Buildings

Date: 28 mars 2026
Depends on: Doctrine V3, Source Exploitation Program
Status: Foundational framework

---

## Thesis

SwissBuilding is not a GED. It is not an OCR layer. It is the **universal compiler of building documentary heritage**.

Every incoming document becomes raw material that can feed truth, procedure, economy, action, transfer, and cumulative building memory.

```
document -> canonical graph -> questions -> decisions -> actions -> publications -> cumulative memory
```

---

## What a Document Produces

A single incoming document can simultaneously produce:

| Output | Example |
|---|---|
| **Facts** | Building has 3 floors, built in 1972 |
| **Evidence** | Asbestos absent in zone 3 per lab analysis |
| **Claims** | Contractor asserts work completed per scope |
| **Obligations** | SUVA notification required before works |
| **Restrictions** | Heritage protection prevents facade modification |
| **Commitments** | Contractor guarantees 5-year warranty |
| **Costs** | Remediation quoted at CHF 45,000 |
| **Deadlines** | Permit expires 2027-03-15 |
| **Rights** | Owner authorized to proceed per permit |
| **Risks** | PCB concentration exceeds threshold in element X |
| **Changes** | New diagnostic supersedes 2022 report |
| **Recipients** | Authority must receive notification |
| **Future outputs** | Pack must be regenerated with new evidence |

---

## Document Families (complete taxonomy)

### Diagnostic & Technical
- Diagnostic reports (amiante, PCB, plomb, HAP, radon, PFAS)
- Laboratory analyses
- Technical notices / fiches techniques
- Maintenance logs
- Inspection reports
- Condition assessments

### Plans & Spatial
- Architectural plans
- Situation plans
- Intervention plans
- Cadastral extracts
- BIM / IFC / BCF models

### Legal & Regulatory
- Permits (construction, demolition, transformation)
- Authority decisions / arretes
- Authority complement requests
- Cantonal declarations
- SUVA notifications
- Waste disposal plans
- Attestations / certificates

### Commercial & Financial
- Quotes / devis
- Invoices / factures
- Contracts (works, services, maintenance)
- Purchase orders / bons de commande
- Insurance policies
- Claims documents
- Subvention requests / decisions
- Tax documents

### Operational
- Work orders / bons d'intervention
- PV de reception
- PV de chantier
- Acknowledgment records
- Handoff / transfer documents
- Garantie declarations

### Governance & Co-ownership
- Co-ownership documents (PPE)
- AG/assembly resolutions
- Management mandates
- Resident notices

### External
- Emails with attachments
- ERP exports
- Data room documents (sale/due diligence)
- Photos / imagery

---

## Information Units (extractable from documents)

Every document type maps to one or more extractable information units:

### Identity & Spatial
| Unit | Example |
|---|---|
| `Identity` | EGID, address, parcel, owner |
| `SpatialScope` | Zones covered, floors, rooms, facades |
| `Element` | Wall, pipe, roof, window, coating |
| `Material` | Asbestos chrysotile, PCB joint, lead paint |
| `System` | HVAC, electrical, plumbing |

### Truth & Evidence
| Unit | Example |
|---|---|
| `Measurement` | 450 mg/kg PCB, 350 Bq/m3 radon |
| `Evidence` | Lab result with method, date, operator |
| `Claim` | "No asbestos detected in zone 3" |
| `Decision` | "Permit granted with conditions" |

### Obligations & Rights
| Unit | Example |
|---|---|
| `Requirement` | Diagnostic amiante required before renovation |
| `Obligation` | SUVA notification 14 days before works |
| `Restriction` | No demolition without heritage review |
| `Approval` | Cantonal authority approves works scope |
| `Commitment` | 5-year warranty on waterproofing |

### Financial
| Unit | Example |
|---|---|
| `Cost` | CHF 45,000 remediation |
| `Coverage` | Insurance covers CHF 500,000 |
| `Exclusion` | Deductible CHF 5,000, excludes pre-existing |

### Temporal
| Unit | Example |
|---|---|
| `Deadline` | Permit valid until 2027-03-15 |
| `Change` | New report supersedes 2022 analysis |
| `Risk` | PCB exceeds threshold — action required |

### Publication & Transfer
| Unit | Example |
|---|---|
| `Publication` | Authority-ready pack v3 |
| `TransferPayload` | Building passport for sale |

---

## Canonical Object Mapping

Each information unit maps to V3 canonical objects:

| Unit | Maps to |
|---|---|
| Identity | Building, SpatialScope |
| SpatialScope | Zone, Level, Space |
| Element / Material | Element, MaterialLayer |
| Measurement | BuildingObservation |
| Evidence | Evidence (via DiagnosticExtraction) |
| Claim | BuildingClaim |
| Decision | BuildingDecision |
| Requirement | Action (via readiness_action_generator) |
| Obligation | Obligation model |
| Restriction | BuildingClaim (type: restriction) |
| Approval | BuildingDecision (type: permit_decision) |
| Commitment | BuildingClaim (type: commitment) |
| Cost | OperationalFinancialEntry |
| Coverage | InsurancePolicy |
| Exclusion | InsurancePolicy.exclusions |
| Deadline | Obligation / Action deadline |
| Change | BuildingEvent + BuildingDelta |
| Risk | BuildingSignal |
| Publication | Publication via ritual_service |
| TransferPayload | BuildingPassportEnvelope |

---

## Consumer Engines

A single document can feed multiple engines simultaneously:

| Engine | What it consumes |
|---|---|
| **Building Home** | Identity, spatial, evidence, claims, trust |
| **Case Room** | Scope, obligations, requirements, costs, deadlines |
| **SafeToX** | Evidence, claims, restrictions, approvals, risks |
| **Procedure Stack** | Requirements, forms, authority routes, approvals |
| **RFQ / Comparison** | Costs, scope, exclusions, deadlines, contractors |
| **Finance** | Costs, coverage, exclusions, commitments, invoices |
| **Insurance** | Coverage, claims, exclusions, risks |
| **Transfer / Passport** | All evidence, claims, decisions, history |
| **Portfolio** | Aggregated risks, costs, readiness, grades |
| **Watch / Delta** | Changes, supersessions, expirations |

---

## Automatic Consequences

When a document enters the system and is processed (parse → review → apply), it can trigger:

| Consequence | Trigger |
|---|---|
| **Truth update** | New evidence or measurement replaces/complements existing |
| **New claim** | Document asserts something new about the building |
| **Contradiction detected** | New evidence contradicts existing claim |
| **SafeToX re-evaluation** | Readiness basis changed |
| **Validation needed** | AI extraction requires human review |
| **Action created** | Missing piece identified, complement needed |
| **Complement request** | Authority document requests additional information |
| **Pack republication** | Published pack is now stale (new evidence) |
| **Case opened/reopened** | New document triggers or impacts a case |
| **Passport delta** | Building passport needs new version |
| **Obligation created** | Document creates a new deadline or requirement |
| **Financial entry** | Quote/invoice creates financial record |
| **Signal emitted** | Change pattern detected |

### Consequence chain

```
Document uploaded
  → OCR + extraction (parse)
  → Human review (review)
  → Apply to canonical graph (apply)
    → Update evidence/claims/decisions
    → Run contradiction_detector
    → Run unknown_generator
    → Run readiness_action_generator
    → Run change_tracker (record event + detect signals)
    → Run trust_score_calculator
    → Check if published packs need refresh
    → Check if passport needs new version
    → Emit notifications to relevant actors
```

---

## Confidence & Validation Hierarchy

| Level | Description | Requires |
|---|---|---|
| 1. Imported | File received, not analyzed | Upload |
| 2. Parsed | OCR/text extracted | Automatic |
| 3. Extracted | Structured data derived | AI + rules |
| 4. Reviewed | Human confirmed extraction | Expert click |
| 5. Applied | Data written to canonical graph | Review + apply |
| 6. Published | Included in a publication/pack | Ritual: publish |
| 7. Transferred | Part of a sovereign transfer | Ritual: transfer |

### What must remain human-validated

- Any claim about pollutant presence/absence
- Any decision about readiness or compliance
- Any publication sent to an authority
- Any transfer of sovereign passport
- Resolution of contradictions
- Financial amounts above threshold

### What can be automated (with confidence score)

- Document classification (type detection)
- Metadata extraction (dates, references, lab names)
- Spatial scope detection
- Threshold comparison (regulatory values)
- Deadline calculation
- Obligation identification
- Action suggestion

---

## What This Is Not

- Not a generic OCR tool
- Not a document management system (GED)
- Not an AI that replaces expert judgment
- Not an auto-publisher of unvalidated truth
- Not a chatbot that answers questions from PDFs

It IS: the compilation engine that transforms documentary chaos into canonical, governed, transferable building truth.

---

## Implementation Priority

### Already built
- DiagnosticExtractionService (PDF → structured diagnostic data, 6 pollutants)
- ExtractionReview UI (parse → review → apply)
- Correction loop (ai_feedback flywheel)
- OCRmyPDF + ClamAV pipeline

### Next
- Extend extraction to quotes/devis (scope, amounts, exclusions, deadlines)
- Extend extraction to authority documents (permits, decisions, complement requests)
- Automatic consequence chain (post-apply triggers)
- Multi-engine feeding (one apply → multiple consumers notified)

### Later
- Insurance document extraction
- Contract/lease extraction
- BIM/IFC spatial import
- Photo/imagery classification
- Email attachment auto-routing
