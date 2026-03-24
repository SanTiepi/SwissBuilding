# BatiConnect Ingestion Pipeline Contract

## Purpose
Defines the interface contract for how external data enters the BatiConnect canonical model.
This is a design specification — implementation is deferred to a future wave.

## Ingestion Sources
1. Document upload (PDF, images) → ClamAV scan → OCR → classification → extraction → canonical projection
2. Email/mail → parse → extract entities → match to existing → project into canonical model
3. ERP bulk import → CSV/JSON mapping → validate → upsert into canonical entities
4. Public data feeds (RegBL, cantonal registries) → existing Vaud public importer pattern

## Ingestion Pipeline Stages
1. **Intake**: receive raw input (file, email, API call, batch)
2. **Sanitize**: virus scan (ClamAV), format validation
3. **Extract**: OCR (OCRmyPDF), AI extraction, structured parsing
4. **Classify**: document type, entity type, confidence scoring
5. **Match**: find existing entities (building, contact, contract) via natural keys
6. **Project**: create/update canonical entities with provenance tracking
7. **Link**: create DocumentLink relations, EvidenceItem relations
8. **Notify**: generate ChangeSignals, update trust scores

## Entity Projection Rules
- Every projected entity gets ProvenanceMixin values: source_type="import", confidence based on extraction quality
- Matching uses natural keys: building EGRID/EGID, contact email/external_ref, lease reference_code, contract reference_code, policy policy_number
- Conflict resolution: existing verified data wins over inferred imports
- Idempotent: re-importing same source produces same result

## BC2 Entities Available for Projection
| Entity | Natural Key | Source Examples |
|--------|------------|----------------|
| Lease | reference_code + building_id | ERP export, scanned lease doc |
| Contract | reference_code + building_id | ERP export, scanned contract |
| InsurancePolicy | policy_number | Insurer export, scanned policy |
| Claim | reference_number | Insurer notification |
| FinancialEntry | external_ref | Accounting export |
| TaxContext | building_id + tax_type + fiscal_year | Tax notice scan |
| InventoryItem | serial_number (optional) | Equipment inventory scan |
| DocumentLink | document_id + entity_type + entity_id + link_type | Auto-generated during projection |

## Document Processing Flow (existing, extended)
1. Upload → `file_processing_service.py` (ClamAV + OCRmyPDF)
2. Classify → `document_classification_service.py`
3. Extract → future AI extraction service
4. Project → future projection service creates BC2 entities
5. Link → DocumentLink junction created automatically

## Provenance Tracking
- Every import batch gets a unique source_ref
- source_type: "import" for bulk, "ai" for AI-extracted, "manual" for user-entered
- confidence: "verified" for official sources, "inferred" for AI-extracted, "declared" for user-entered

## Implementation Notes (for future wave)
- Batch imports should be transactional (all-or-nothing per batch)
- Error reporting: per-row errors with source line reference
- Duplicate detection: check natural keys before insert, update if exists (upsert pattern)
- Audit: every import logged in AuditLog with batch reference
