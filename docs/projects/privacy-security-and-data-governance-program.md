# Privacy, Security, and Data Governance Program

## Mission

Make SwissBuildingOS trustworthy not only as a product of evidence and readiness, but as a system that handles sensitive building, project, and actor data with discipline that can scale across jurisdictions and enterprise buyers.

This program should strengthen:

- data boundary clarity
- sharing controls
- privacy posture
- security-sensitive workflow design
- governance of sensitive evidence and actor data

## Why This Matters

As SwissBuildingOS grows into:
- proof packs
- authority packs
- contractor packs
- transaction / insurance / lender packs
- partner gateways
- exchange standards

it becomes increasingly exposed to:
- over-sharing risk
- role leakage
- sensitive-document drift
- weak provenance on who accessed what and why
- future enterprise blockers around security and governance

International-class products are not only powerful.
They are governable under scrutiny.

## Core Outcomes

### 1. Data-sharing boundaries become explicit

Expected:
- clear distinction between:
  - internal building truth
  - shareable proof subsets
  - sensitive or internal-only fields
- pack generation respects audience boundaries by construction

### 2. Security-sensitive workflows become first-class

Expected:
- downloads, packs, and external sharing flows become auditable
- temporary or scoped access patterns exist where useful
- high-risk actions and evidence access can be reasoned about

### 3. Data governance becomes product-grade

Expected:
- retention and archival posture is clearer
- provenance of sensitive changes is easier to inspect
- future compliance and enterprise review become easier, not harder

## Recommended Workstreams

### Workstream A — Audience-bounded data surfaces

- define audience classes for packs and external views:
  - internal
  - owner
  - contractor
  - authority
  - insurer / lender later
- ensure pack and export logic can enforce bounded visibility

### Workstream B — Sensitive evidence handling

- classify documents and artefacts by sensitivity
- add safe patterns for:
  - downloadable vs internal-only
  - redacted vs full
  - expiring share links if appropriate

### Workstream C — Access and audit hardening

- strengthen access/audit semantics around:
  - exports
  - shared links
  - dossier generation
  - external pack retrieval

### Workstream D — Data governance primitives

- retention/archival policy surfaces
- provenance of change for sensitive objects
- explicit ownership and stewardship for key data classes

### Workstream E — Security-by-product review

- identify the most product-relevant security and privacy gaps without turning the repo into a compliance bureaucracy
- focus on:
  - sharing
  - retrieval
  - externalization
  - role boundaries

## Candidate Improvements

- `DataSensitivity`
- `AudienceScope`
- `ShareLink`
- `RedactionProfile`
- `EvidenceAccessLog`
- `ExternalPackAccess`
- `DataRetentionPolicy`
- `SensitiveFieldRegistry`

## Acceptance Criteria

- the product has a clearer audience-aware sharing model
- pack/export logic is compatible with bounded visibility
- sensitive evidence handling is more deliberate
- auditability of access and sharing improves
- the repo is more enterprise-review-ready on privacy/security posture

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

## Notes

This program is about pragmatic governance, not paperwork theatre.

Prefer:
- explicit audience boundaries
- safe-by-default sharing
- auditable externalization

Avoid:
- generic security polishing disconnected from product reality
- heavy policy systems with no product leverage
