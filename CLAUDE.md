# SwissBuilding Claude Bootstrap

Read [AGENTS.md](./AGENTS.md) for operating rules.
Read [MEMORY.md](./MEMORY.md) for project state.
Read [ORCHESTRATOR.md](./ORCHESTRATOR.md) for active execution board (large/multi-wave missions).

> AI agents MAY update this file to fix outdated counts, commands, or references.

## Projet

- Nom : BatiConnect (repo: SwissBuilding)
- Stack : FastAPI + React 18 + TypeScript + PostgreSQL/PostGIS + MinIO
- État : actif
- Objectif : Building Life OS — couche d'interprétation, de preuve et de décision au-dessus des registres publics suisses

## Sources de vérité

1. Instruction de l'utilisateur
2. Ce fichier
3. Code + tests

## Session start

`/context` silencieusement. Résume en 2-3 lignes.

## Comment tu travailles

Tu as un écosystème à ta disposition. Utilise-le naturellement, pas mécaniquement.

### WorldEngine / Codex = ton moteur de briefing

Quand un problème est complexe ou incertain, ne réfléchis pas seul. Lance un briefing :

`codex exec --full-auto "Problème: [X]. Décompose en dimensions. Quels experts sont pertinents ? Pour chaque: 1 recommandation + 1 risque + 1 critère de succès testable."`

Ce qui revient n'est pas un "avis" — c'est un **objet de décision** : options, risques, tests, garde-fous. Tu l'utilises comme contrat de travail.

**Tu peux contester le briefing.** Si le code existant contredit une recommandation, dis-le. Le briefing s'améliore par la contestation.

**Les experts émergent du problème.** Pas un panel fixe — le contexte détermine qui parle. Problème de données + UX + légal → 3 experts spécifiques, pas un comité générique.

### Quand lancer un briefing

- Tu sens de l'incertitude sur l'approche
- Le changement touche 3+ domaines
- Tu hésites entre 2 architectures
- L'idée est nouvelle et non testée
- Tu es en mode Explore sur un brainstorm

### Quand NE PAS lancer de briefing

- Tu sais exactement quoi faire
- C'est un fix simple
- Tu vas juste attendre sans rien faire en parallèle

### Tes subagents

Tu peux paralléliser avec Agent Teams. Utilise-les quand le travail est décomposable en tâches indépendantes.

### Propositions non sollicitées

Si en travaillant tu vois un angle mort, un risque, une opportunité — DIS-LE même si personne ne l'a demandé.

## Mode A — Assisté (défaut)

```
Instruction → briefing si incertain → code → tests → fix si fail → review → commit
```

## Mode B — Full autonome

```
/context → briefing → exécute → vérifie → next ou stop
```

Garde-fous : pas hors goal, pas de dérive, stop si bloqué.

## Skills

- `/context` — reprendre un projet
- `/brainstorm` — éprouver une idée (Explore = briefing multi-expert)
- `/intake` — questionnaire pré-dev pré-rempli
- `/status` — dashboard
- `/genesis` — idée → repo complet
- `/portfolio` — vue multi-projets
- `/fix-loop` — boucle test/fix auto

## Ecosystem

BatiConnect is a **standalone brand** (Batiscan Sarl is founder/operator).

### 3 Products
| Product | Role | Status |
|---|---|---|
| Site public (batiscan.ch) | Acquisition, SEO, CTA | Active |
| Batiscan V4 (app.batiscan.ch) | ERP diagnostic interne | Frozen |
| BatiConnect (this repo) | Building intelligence + remediation module + AI layer | Active |

BatiConnect carries:
1. **Building intelligence** -- dossier, evidence, completeness, trust, readiness, portfolio
2. **Remediation module** (internal) -- mise en concurrence encadree for pollutant remediation works (NOT a separate product)
3. **Transversal AI layer** -- progressive learning: Phase 1 (LLM does work) -> Phase 2 (deterministic rules) -> Phase 3 (LLM supervises)

**Data flywheel**: every use improves the platform (corrections feed ai_feedback, usage trains rules).

See `docs/vision-100x-master-brief.md` for the full ecosystem map.
See `AGENTS.md` (section "Ecosystem Invariants") for the 6 hard rules.
See `docs/roadmap-48-months.md` for the 48-month roadmap (29 programmes, 304+ features M0-M12).

## Hard Rules

- `egid` != `egrid` != `official_id` (see AGENTS.md for types)
- no partially wired features — hide or simplify incomplete work
- no backend expansion unless explicitly gated (EXCEPTION: Robin has authorized aggressive building — build wide and deep, see manifesto)
- hub files (i18n, router.py, models/__init__, schemas/__init__) = supervisor merge only
- shared constants in `backend/app/constants.py`
- imports: idempotent + explicit upserts
- before claiming done: check AGENTS.md Definition of Done

## Mission Protocol

For large missions:
- prompt = mission framing only (don't restate repo context)
- `ORCHESTRATOR.md` = durable execution board (maintain Next 10, wave status, debriefs)
- `Lead Feed` section = Codex→Claude channel
- repo docs = standing context (don't expect prompt to contain everything)
- prompt structure / size rules live in `AGENTS.md` (`Codex → Claude Prompting Rules`)

## Validation Commands

### Frontend (`cd frontend`)

| Command | Purpose |
|---------|---------|
| `npm run validate` | tsc + eslint + prettier (fast gate) |
| `npm test` | vitest unit (~996 tests) |
| `npm run test:e2e` | playwright mock (no backend) |
| `npm run test:e2e:real` | playwright real (needs backend running — VPS or local, runs preflight auto) |
| `npm run build` | prod build + PWA artifacts |
| `npm run lint:fix && npm run format:fix` | auto-fix |

### Backend (`cd backend`)

| Command | Purpose |
|---------|---------|
| `ruff check app/ tests/` | lint (must be 0 errors) |
| `ruff format --check app/ tests/` | format (must be 0 errors) |
| `python -m pytest tests/ -q` | ~7150 tests |
| `python -m app.seeds.seed_verify` | verify seed dataset |
| `ruff check --fix app/ tests/ && ruff format app/ tests/` | auto-fix |

### Repo Health (`cd backend`)

| Command | Purpose |
|---------|---------|
| `python scripts/pre_commit_check.py` | all fitness functions (route shell, file sizes, compatibility, API, canonical) |
| `python scripts/pre_commit_check.py --fast` | fast gate (route shell + compatibility only) |
| `python scripts/pre_commit_check.py --json` | full check with JSON report to stdout |
| `python scripts/check_repo_health.py` | full health report with JSON file output |
| `make check` | lint + format + health (full pre-merge gate) |
| `make health` | all fitness functions via Makefile |

### Strategy

- after frontend edits: `npm run validate`
- after backend edits: `ruff check app/ tests/`
- before done: run relevant tests
- full validation (build + all tests): only when scope justifies it
- testing doctrine: signal density > test count (see AGENTS.md)
