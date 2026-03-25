# Claude Master Execution Pack

Date de controle: `25 mars 2026`

## North Star

`SwissBuilding` doit gagner sur:

- verite canonique du batiment
- clarte procedurale
- reutilisation de preuve
- coordination multi-acteurs
- echange fiable

Ne pas gagner par largeur.
Gagner par profondeur, continuite et confiance.

## Decision Stack

### Core now

- canonical building workspace
- `ControlTower` / operating inbox
- `Obligation`
- procedure engine
- proof and delivery layer
- `SwissRules` spine
- passport / exchange contract

### Next moat

- portfolio intelligence grounded in proof
- partner trust / contributor quality
- geometry intelligence
- learning loops
- material / circularity intelligence

### Future infrastructure

- passport exchange network
- authority flow
- trust vault / chain of custody
- territory / public systems coordination
- agent operating layer

### Integrate instead of build

- full property ERP
- generic chantier suite
- BIM authoring
- generic DMS / drive replacement
- generic portfolio planning detached from proof

### Not now

- full insurer platform
- full lender stack
- resident super-app
- marketplace

## Build Gate

Construire seulement si le bloc augmente au moins `2/4`:

1. valeur cumulative du dossier
2. clarte procedurale
3. reutilisation de preuve
4. dependance utile multi-acteurs

Sinon:

- integrer
- preparer schema seulement
- ou deferer

## Current Priority Order

1. **close active regression clusters first**
   - si un pattern homogene existe, le vider avant toute full suite
   - exemple actuel: `401 vs 403` sur les tests `unauthenticated`
2. **procedure engine**
3. **ControlTower v2**
4. **proof delivery**
5. **passport exchange hardening**
6. **SwissRules watch foundations**

## Repo Invariants

- `egid` != `egrid` != `official_id`
- no partially wired features
- imports idempotent + explicit upserts
- shared constants in `backend/app/constants.py`
- official public data sources over UI scraping
- hub files reserved to supervisor merge only:
  - `backend/app/api/router.py`
  - `backend/app/models/__init__.py`
  - `backend/app/schemas/__init__.py`
  - `frontend/src/i18n/{en,fr,de,it}.ts`

## Validation Doctrine

- inner loop first
- confidence loop before "done"
- full loop only at wave boundary or proof moment
- never use full suites by reflex

Operational rule:

- if a regression cluster is homogeneous, do:
  - sweep the cluster
  - rerun targeted files
  - rerun confidence
  - run full only once

Reference:

- [test-execution-optimization-2026-03-25.md](./test-execution-optimization-2026-03-25.md)
- [claude-validation-matrix-2026-03-25.md](./claude-validation-matrix-2026-03-25.md)
- [auth-regression-sweep-pack-2026-03-25.md](./auth-regression-sweep-pack-2026-03-25.md)

## Definition of Done

### Model / schema wave

- model + schema + migration exist
- targeted tests pass
- hub wiring prepared for supervisor merge
- `ruff check` and `ruff format --check` clean

### Service / API wave

- service behavior covered by targeted integration tests
- endpoint contracts are explicit
- no hidden partial wiring
- confidence loop passes

### Frontend wave

- visible consumer surface exists
- loading / error / empty handled
- dark mode safe
- `npm run validate` clean
- targeted vitest pass

### Mixed wave

- backend and frontend contracts agree
- confidence passes on both sides
- one acceptance path is proven end to end

## Wave Closeout Checklist

- [ ] smallest useful validation loop used first
- [ ] targeted tests green
- [ ] confidence loop green
- [ ] hub file merge pass done if needed
- [ ] no new warnings introduced
- [ ] no partially wired feature exposed
- [ ] `ORCHESTRATOR.md` updated if this was a wave

## Key References

- [AGENTS.md](/C:/PROJET%20IA/SwissBuilding/AGENTS.md)
- [stack-frontier-map-and-build-vs-integrate-2026-03-25.md](./stack-frontier-map-and-build-vs-integrate-2026-03-25.md)
- [swissbuilding-must-win-benchmark-2026-03-25.md](/C:/PROJET%20IA/SwissBuilding/docs/market/swissbuilding-must-win-benchmark-2026-03-25.md)
- [product-excellence-vs-adoption-and-market-lock-in-2026-03-25.md](./product-excellence-vs-adoption-and-market-lock-in-2026-03-25.md)
- [swissbuilding-10-15-20-year-vision-and-synergy-map-2026-03-25.md](./swissbuilding-10-15-20-year-vision-and-synergy-map-2026-03-25.md)
- [swissrules-enablement-pack.md](./swissrules-enablement-pack.md)
- [swissrules-coverage-matrix-2026-03-25.md](./swissrules-coverage-matrix-2026-03-25.md)
- [swissrules-watch-priority-backlog-2026-03-25.md](./swissrules-watch-priority-backlog-2026-03-25.md)
- [authority-flow-foundation-pack-2026-03-25.md](./authority-flow-foundation-pack-2026-03-25.md)
- [proof-trust-layer-roadmap-2026-03-25.md](./proof-trust-layer-roadmap-2026-03-25.md)
- [passport-exchange-network-foundation-pack-2026-03-25.md](./passport-exchange-network-foundation-pack-2026-03-25.md)
- [partner-trust-operating-pack-2026-03-25.md](./partner-trust-operating-pack-2026-03-25.md)
- [authority-adapter-priority-map-2026-03-25.md](./authority-adapter-priority-map-2026-03-25.md)
- [geometry-intelligence-operating-pack-2026-03-25.md](./geometry-intelligence-operating-pack-2026-03-25.md)
- [territory-public-systems-operating-pack-2026-03-25.md](./territory-public-systems-operating-pack-2026-03-25.md)
- [benchmarking-grounded-in-proof-operating-pack-2026-03-25.md](./benchmarking-grounded-in-proof-operating-pack-2026-03-25.md)
- [agent-operating-layer-foundation-pack-2026-03-25.md](./agent-operating-layer-foundation-pack-2026-03-25.md)
- [openbim-convergence-operating-pack-2026-03-25.md](./openbim-convergence-operating-pack-2026-03-25.md)
- [pilot-communes-pack-2026-03-25.md](./pilot-communes-pack-2026-03-25.md)
- [swissbuilding-competitor-gap-matrix-2026-03-25.md](/C:/PROJET%20IA/SwissBuilding/docs/market/swissbuilding-competitor-gap-matrix-2026-03-25.md)
- [claude-wave-opportunity-map-2026-03-25.yaml](./claude-wave-opportunity-map-2026-03-25.yaml)
- [claude-wave-brief-kit-2026-03-25.md](./claude-wave-brief-kit-2026-03-25.md)
