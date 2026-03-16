# Legal-Grade Proof and Chain-of-Custody Program

## Mission

Make SwissBuildingOS defensible under audit, dispute, authority review, insurer review, and transaction diligence by hardening how proof is versioned, transmitted, acknowledged, archived, and later challenged.

This program is not about collecting more evidence.
It is about making evidence, packs, and dossier states materially harder to contest.

## Why This Matters

SwissBuilding already produces:
- evidence links
- dossiers
- export packs
- audit trails
- readiness and post-works states

The missing layer is legal-grade defensibility:
- which version is canonical
- which version was delivered
- what changed between versions
- who touched or approved an artifact
- what was acknowledged
- what was archived
- what is safe to reuse later as proof

Without this layer, the product is evidence-rich but still easier to challenge in authority, insurer, transaction, or claims contexts.

## Strategic Outcomes

- dossier and pack artifacts gain canonical lifecycle semantics
- proof can be traced from source through export and archival
- delivery, acknowledgement, and custody become inspectable
- SwissBuilding gains a credible path toward legal-grade evidence handling without overclaiming legal guarantee

## Product Scope

This program should produce:
- stronger proof versioning
- custody and delivery events
- archive-ready export semantics
- evidence access and transmission traceability
- signature and acknowledgement placeholders or hooks

It should not yet become:
- a full e-signature platform
- a formal legal archive product
- a provider-specific trust-services integration maze

## Recommended Workstreams

### Workstream A - Proof and pack version certification

Build canonical version semantics for:
- dossier packs
- authority packs
- contractor packs
- owner / insurer / lender packs
- any proof-bearing export that may be challenged later

Expected capabilities:
- explicit canonical version
- revision lineage
- content hash
- generation timestamp
- source snapshot timestamp
- reason for supersession

Candidate objects:
- `ProofVersion`
- `ArchivedSnapshot`
- `VersionLineage`

### Workstream B - Chain-of-custody event model

Model the handling lifecycle of sensitive artifacts:
- created
- reviewed
- approved
- exported
- transmitted
- downloaded
- acknowledged
- archived
- superseded

Focus especially on:
- authority packs
- disposal evidence
- remediation evidence
- sensitive pollutant reports
- post-works truth artifacts

Candidate objects:
- `CustodyEvent`
- `TransmissionEvent`
- `ArchiveEvent`

### Workstream C - Delivery and acknowledgement proof

Make outbound delivery inspectable.

Examples:
- pack delivered to authority
- contractor pack downloaded
- owner pack opened
- acknowledgement received
- reminder sent

Candidate objects:
- `DeliveryReceipt`
- `AcknowledgementRecord`
- `DistributionReceipt`

### Workstream D - Signature and sealing hooks

Prepare the product for stronger trust services later without binding too early to one provider.

Expected direction:
- placeholder signature state
- future e-signature integration slot
- future qualified timestamp / seal slot
- UI wording that clearly distinguishes:
  - generated
  - acknowledged
  - signed
  - sealed

Candidate objects:
- `SignaturePlaceholder`
- `SealState`

### Workstream E - Legal-grade archival posture

Strengthen how exports and critical evidence are archived and retrieved later.

Expected capabilities:
- retention class
- archive status
- archive location metadata
- immutable snapshot option when useful
- before/after diffability between revisions

## Candidate Improvements

- `ProofVersion`
- `CustodyEvent`
- `DeliveryReceipt`
- `AcknowledgementRecord`
- `ArchivedSnapshot`
- `SignaturePlaceholder`
- `SealState`

## Acceptance Criteria

- proof-bearing exports have explicit version semantics
- SwissBuilding can explain who handled, received, or acknowledged a proof artifact
- custody and delivery state are inspectable
- archive posture is stronger and clearer
- the product becomes more defensible without falsely claiming legal certification it does not yet provide

## Validation

Backend if touched:
- `cd backend`
- `ruff check app/ tests/`
- `ruff format --check app/ tests/`
- `python -m pytest tests/ -q`

Frontend if touched:
- `cd frontend`
- `npm run validate`
- `npm test`
- `npm run test:e2e`
- `npm run build`
