# Post-Moonshot Consolidation — Hotspot Brief

Date: 28 mars 2026
Status: Active — first consolidation wave reference

---

## Backend Service Hotspots

| File | Lines | Classification | Decomposition Seam |
|---|---|---|---|
| `building_enrichment_service.py` | 4,394 | **Split soon** | Adapter per source (MADD, RegBL, cadastre), orchestrator facade |
| `swiss_rules_spine_service.py` | 1,558 | **Split soon** | Rule family modules (asbestos, pcb, lead, hap, radon, pfas) |
| `transaction_readiness_service.py` | 1,382 | **Acceptable for now** | Policy logic per transaction type |
| `contract_extraction_service.py` | 1,372 | **Acceptable for now** | Extraction pattern is consistent, justified size |
| `authority_extraction_service.py` | 1,226 | **Acceptable for now** | Same extraction pattern |
| `audit_readiness_service.py` | 1,194 | **Acceptable for now** | Aggregator, hard to split without losing coherence |
| `pack_builder_service.py` | 1,123 | **Split soon** | Section builders into separate module, pack orchestrator stays |
| `handoff_pack_service.py` | 1,037 | **Acceptable for now** | Similar to pack_builder |
| `quote_extraction_service.py` | 1,016 | **Acceptable for now** | Extraction pattern |
| `readiness_reasoner.py` | 1,011 | **Acceptable for now** | Core engine, coherent |

### Top 3 to split first
1. `building_enrichment_service.py` (4,394 lines) — by far the biggest. Split into source-specific adapters + orchestrator.
2. `swiss_rules_spine_service.py` (1,558 lines) — split by pollutant rule family.
3. `pack_builder_service.py` (1,123 lines) — extract section builders into `pack_sections/` module.

---

## Frontend Page Hotspots

| File | Lines | Classification |
|---|---|---|
| `InterventionSimulator.tsx` | 1,600 | **Acceptable** — complex simulation UI, pre-session |
| `AdminUsers.tsx` | 1,442 | **Acceptable** — admin page, bounded |
| `Campaigns.tsx` | 1,422 | **Acceptable** — pre-session |
| `BuildingDetail.tsx` | 1,016 | **Monitor** — shell page, could grow further |

No dangerous frontend page hotspot from this session.

---

## Frontend Component Hotspots

| File | Lines | Classification |
|---|---|---|
| `ExtractionReview.tsx` | 954 | **Split soon** — form sections into sub-components |
| `OverviewTab.tsx` | 837 | **Monitor** — shell component, many lazy sections |
| `TenderTab.tsx` | 782 | **Monitor** — complex but coherent |
| `ProjectWizard.tsx` | 730 | **Acceptable** — wizard steps |

### Top 1 to split first
1. `ExtractionReview.tsx` (954 lines) — extract MetadataSection, SamplesTable, ConclusionsSection into sub-components.

---

## First Consolidation Wave Brief

**Scope:** 3 bounded decompositions, no new features.

### Wave C1: Split building_enrichment_service.py

Create `backend/app/services/enrichment/`:
- `__init__.py` — re-export facade
- `enrichment_orchestrator.py` — main orchestration logic
- `madd_adapter.py` — MADD/geo.admin source adapter
- `regbl_adapter.py` — RegBL/GWR adapter
- `cadastre_adapter.py` — cadastral/parcel adapter
- Keep the facade so existing imports don't break

Exit: 5 files < 500 lines each instead of 1 file at 4,394.

### Wave C2: Split pack_builder section builders

Create `backend/app/services/pack_sections/`:
- `__init__.py`
- One file per section builder group (passport, completeness, readiness, pollutant, etc.)
- `pack_builder_service.py` becomes a thin orchestrator

Exit: orchestrator < 400 lines, section builders isolated.

### Wave C3: Split ExtractionReview.tsx

Create `frontend/src/components/extractions/`:
- `MetadataSection.tsx`
- `SamplesTable.tsx`
- `ConclusionsSection.tsx`
- `RegulatorySection.tsx`
- `ExtractionReview.tsx` becomes the shell

Exit: ExtractionReview.tsx < 300 lines.

---

## What NOT to do in the first consolidation wave

- Don't rewrite swiss_rules_spine_service yet (needs careful rule-family analysis)
- Don't split pre-session legacy hotspots that are stable and working
- Don't add features during decomposition
- Don't change public APIs — only internal structure
