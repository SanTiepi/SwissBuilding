# Multimodal Building Understanding and Grounded Query Program

## Mission

Use recent multimodal advances to turn mixed building inputs into structured, evidence-grounded building knowledge:
- PDF reports
- plans
- annotated images
- site photos
- voice notes
- tabular attachments

The goal is not a generic chatbot.
It is a grounded building-understanding layer that can extract, align, and answer from proof.

## Why This Matters

This became materially more realistic only recently because multimodal systems are now far better at:
- reading text plus layout
- connecting images and plans to structured entities
- grounding answers in cited source fragments
- extracting structured outputs with usable confidence

For SwissBuilding, this unlocks:
- faster dossier bootstrap
- richer field capture
- more useful search and question-answering
- stronger building memory with less manual entry

## Strategic Outcomes

- multimodal ingestion becomes a moat, not just OCR
- users can query a building in natural language with grounded answers
- plans, photos, and reports become one connected memory surface

## Product Scope

This program should produce:
- cross-modal extraction and alignment
- evidence-grounded query surfaces
- confidence and provenance for every extracted or answered claim

It should not become:
- an ungrounded chatbot
- a free-form assistant that invents facts

## Recommended Workstreams

### Workstream A - Multimodal extraction graph

Candidate objects:
- `MultimodalSourceFragment`
- `CrossModalAnchor`
- `ExtractedClaim`

### Workstream B - Grounded query layer

Expected capabilities:
- ask about a building in natural language
- return structured or semi-structured answers
- cite source fragments, plans, or images
- expose confidence and missing knowledge

Candidate objects:
- `GroundedQuery`
- `GroundedAnswer`
- `AnswerCitation`

### Workstream C - Cross-modal alignment

Expected capabilities:
- link report mention to material
- link material to zone
- link photo to plan anchor
- link voice note to observation

Candidate objects:
- `CrossModalLink`
- `AlignmentConfidence`

## Acceptance Criteria

- SwissBuilding gains a grounded multimodal understanding layer
- question-answering is evidence-backed and citation-first
- multimodal extraction strengthens the building memory instead of bypassing it

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
