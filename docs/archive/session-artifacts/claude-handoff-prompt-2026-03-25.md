# Claude Handoff Prompt

Use this prompt as-is or adapt lightly.

```text
Claude,

Contexte immediat:
- Tu es sur SwissBuilding.
- Le repo contient maintenant un master execution pack et des docs de priorisation/validation.
- Le blocage du moment n'est pas un bug produit diffus: c'est surtout une mauvaise boucle de validation autour d'un cluster auth homogene.

Si tu dois repartir en one-shot plutot qu'en petites waves:
- lis `docs/projects/claude-one-shot-finisher-pack-2026-03-25.md`
- puis utilise `docs/projects/claude-one-shot-finisher-prompt-2026-03-25.md`

Si le core one-shot est deja ferme et qu'il faut enchainer d'un coup:
- lis `docs/projects/claude-post-core-one-shot-pack-2026-03-25.md`
- puis utilise `docs/projects/claude-post-core-one-shot-prompt-2026-03-25.md`

Priorite immediate:
1. Ferme le cluster backend `unauthenticated 401 vs 403`.
2. Arrete les full backend runs tant que ce cluster n'est pas vide.
3. Rerun ensuite:
   - fichiers auth touches
   - cluster securite/auth cible
   - confidence loop
   - une seule full suite backend a la fin

Regle:
- Si les echecs sont homogenes, sweep du cluster d'abord, full rerun ensuite.
- Ne relance pas `pytest tests/ -q` en boucle tant que le motif principal n'est pas clos.
- Utilise d'abord:
  - `cd backend && python scripts/run_auth_regression_sweep.py scan`
  - `cd backend && python scripts/run_auth_regression_sweep.py rewrite`
  - `cd backend && python scripts/run_auth_regression_sweep.py pytest`

Docs a lire en premier:
- `docs/projects/claude-now-priority-stack-2026-03-25.md`
- `docs/projects/claude-one-shot-finisher-pack-2026-03-25.md`
- `docs/projects/claude-master-execution-pack-2026-03-25.md`
- `docs/projects/claude-restart-checklist-2026-03-25.md`
- `docs/projects/claude-wave-opportunity-map-2026-03-25.yaml`
- `docs/projects/claude-operating-pack-registry-2026-03-25.md`
- `docs/projects/claude-next-wave-selector-2026-03-25.md`
- `docs/projects/claude-validation-matrix-2026-03-25.md`
- `docs/projects/auth-regression-sweep-pack-2026-03-25.md`
- `docs/projects/swissrules-enablement-pack.md`
- `docs/projects/swissrules-coverage-matrix-2026-03-25.md`
- `docs/projects/swissrules-watch-priority-backlog-2026-03-25.md`
- `docs/projects/claude-supervisor-merge-pack-2026-03-25.md`
- `docs/projects/claude-wave-brief-kit-2026-03-25.md`
- `docs/projects/doc-overload-guardrails-2026-03-25.md`

Comportement attendu:
- utilise les plus petites boucles de validation qui donnent du signal
- respecte strictement les hub files reserves
- une fois le cluster auth ferme, reprends la prochaine wave selon le master pack

Rappel:
- `egid` != `egrid` != `official_id`
- pas de seconde entite obligation
- pas de seconde inbox d'actions
- pas de logique permis parallele a `permit_tracking`

Objectif:
- sortir du bruit de validation
- revenir a une execution propre, rapide et priorisee
```
