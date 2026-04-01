---
name: status
description: "Dashboard instantané du projet. Usage: /status. Sert aux humains ET aux agents — même format, même source de vérité."
user-invocable: true
---

# /status — Dashboard projet universel

Génère un rapport d'état instantané qui sert à Robin (lecture 5s) ET aux agents (parsing JSON).

## Collecte des données

Exécute ces commandes Bash en parallèle :

### Repo
```bash
echo "BRANCH:$(git branch --show-current)" && echo "HEAD:$(git log -1 --oneline)" && echo "DIRTY:$(git status --porcelain | wc -l) files"
```

### Tests
Selon le projet :
- Node.js : `npm test 2>&1 | tail -5` (cherche "pass X", "fail X")
- Python : `cd backend && python -m pytest tests/ -x -q --timeout=30 2>&1 | tail -5`
Extrais : passed, failed, skipped.

### GitHub (si gh CLI est authentifié)
```bash
gh pr list --state open --json number,title --limit 5 2>/dev/null
gh issue list --state open --json number,title,labels --limit 5 2>/dev/null
```

### Historique récent
- Lis le dernier commit : `git log -5 --oneline`
- Si `transform_log.ndjson` ou `.claude/brainstorm_log.md` existe, lis les dernières entrées

## Algorithme de recommandation

Applique ces règles dans l'ordre (première qui matche = action recommandée) :

1. `tests.failed > 0` → action: `fix_tests`, target: le test qui fail
2. `dirty > 5 files` �� action: `clean_worktree`, reason: trop de changements non commités
3. `PR bloquante` (label blocker ou review requested) �� action: `review_pr`
4. `issue urgente` (label urgent/critical/bug) → action: `triage_issue`
5. Tests verts + repo clean + PR prêtes → action: `merge_ready`
6. Tout est calme → action: `continue`, reason: basé sur TASKS.md ou dernier brainstorm
7. Ambiguïté → action: `ask_human`

## Format de sortie

```
STATUS: [green|yellow|red] | NEXT: [action] | PRIORITY: [high|medium|low]

## /status — [nom du projet]

**TL;DR:** [1 ligne résumé état + prochaine action]

**Repo:** `[branche]` @ `[commit court]` | [N] fichiers modifiés
**Tests:** [passed]/[total] pass | [failed] fail | [skipped] skip
**GitHub:** [N] PR ouvertes | [N] issues ouvertes
**Dernier:** [qui] — [quoi] — [quand]

**→ Next:** [action recommandée + cible + pourquoi]
```

Puis en bloc replié ou à la fin, le JSON canonique pour les agents :

```json
{"status":"green|yellow|red","next":{"action":"...","target":"...","reason":"...","priority":"high|medium|low"},"repo":{"branch":"...","head":"...","dirty":0},"tests":{"passed":0,"failed":0,"skipped":0},"github":{"prs":0,"issues":0},"recent":[{"actor":"...","action":"...","at":"..."}]}
```

## Règles
- Tout doit tenir en 10 lignes max (hors JSON)
- Ne cache jamais un test rouge ou un repo dirty — c'est l'info la plus importante
- Si tu ne peux pas exécuter une commande (pas de gh, pas de tests), mets "unknown" et note pourquoi
- Le JSON doit être parseable en une seule ligne par un agent
