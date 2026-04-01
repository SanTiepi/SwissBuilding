---
name: wave-next
status: in-progress
created: 2026-04-01T02:12:00Z
updated: 2026-04-01T02:12:00Z
progress: 0%
prd: .claude/prds/wave-next.md
github: (will be set on sync)
---

# Epic: wave-next — Post Building Life OS Consolidation + Features

## Overview

Consolidate the repo (192→≤60 docs), fix code quality (silent exceptions, lint), activate untapped geo enrichment (24 layers), populate ClimateExposureProfile, update control files.

## Architecture Decisions

- Archiving not deleting: session artifacts go to docs/archive/, not /dev/null
- NFT brainstorm content absorbed into roadmap-48-months.md
- 61 programme files preserved but indexed in roadmap
- Exception handling: add logging, don't change control flow

## Technical Approach

### Consolidation (docs/)
- Move claude-* and tactical packs to docs/archive/
- Cross-reference 61 programmes into roadmap
- Integrate NFT brainstorm into roadmap

### Backend Quality
- ruff --fix for imports
- Add logger.warning to critical silent exceptions
- No structural changes

### Geo Enrichment
- Wire existing fetchers in orchestrator.py
- Persist swissBUILDINGS3D fields
- Add composite geo risk score

### Climate
- Populate ClimateExposureProfile fields
- Create OpportunityWindow detection service

## Task Breakdown Preview

| # | Task | Parallel | Effort |
|---|------|----------|--------|
| 001 | Archive 55 obsolete docs | ✅ | S |
| 002 | Integrate NFT + vision into roadmap | ✅ | M |
| 003 | Index 61 programmes in roadmap | ✅ | M |
| 004 | Fix ruff errors + silent exceptions | ✅ | S |
| 005 | Activate 24 geo.admin layers | ❌ (after 004) | M |
| 006 | Persist swissBUILDINGS3D fields | ✅ with 005 | S |
| 007 | Composite geo risk score | ❌ (after 005) | M |
| 008 | Populate ClimateExposureProfile | ✅ | M |
| 009 | OpportunityWindow detection service | ❌ (after 008) | M |
| 010 | Update CLAUDE.md + AGENTS.md | ✅ | S |

## Dependencies
- 005 depends on 004 (clean lint before adding code)
- 007 depends on 005 (needs geo data to compute score)
- 009 depends on 008 (needs climate data for window detection)

## Success Criteria (Technical)
- `ruff check` = 0 errors
- docs/projects/ ≤60 files
- enrichment pipeline calls 24 fetchers
- ClimateExposureProfile has 10/10 fields populated in tests
- All existing tests pass

## Estimated Effort
- Total: ~30-40 hours
- Parallel streams: 3 (consolidation, quality, features)
- Critical path: 005→007 (geo activation→score)
