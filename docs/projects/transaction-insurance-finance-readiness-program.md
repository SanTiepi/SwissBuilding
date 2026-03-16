# Transaction, Insurance, and Finance Readiness Program

## Mission

Extend SwissBuildingOS from renovation and compliance readiness into:

- transaction readiness
- insurance readiness
- finance / refinancing readiness

The goal is to make the building dossier useful not only for works, but also for acquisition, disposition, underwriting, and lender review.

## Why This Matters

Once trust, proof, contradictions, unknowns, and post-works truth exist, the next major value layer is:

- can this asset be sold confidently?
- can it be insured confidently?
- can it be financed confidently?

These are high-value decision surfaces and strong commercial differentiators.

## Core Outcomes

### 1. Transaction readiness

Expected:

- `safe_to_sell`
- due-diligence proof pack
- unresolved unknowns and contradictions visible
- seller / buyer-oriented dossier summary

### 2. Insurance readiness

Expected:

- `safe_to_insure`
- latent risk visibility
- exclusions / caveats / missing proof surfaced clearly
- insurer-facing pack structure

### 3. Finance readiness

Expected:

- `safe_to_finance`
- asset trust / proof / residual risk summary
- lender-facing pack structure

## Recommended Workstreams

### Workstream A — Readiness type expansion

- add transaction / insurance / finance readiness
- connect to trust, unknowns, contradictions, post-works truth

### Workstream B — Pack architecture

- buyer/seller pack
- insurer pack
- lender pack

### Workstream C — UI decision surfaces

- building-level readiness cards
- pack generation entry points
- clear blockers and caveats

## Acceptance Criteria

- the product can express at least one non-renovation readiness state in a meaningful way
- the dossier can be repackaged for transaction or underwriting use
- trust and unknowns are usable in commercial/financial decisions

## Validation

Backend:

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
