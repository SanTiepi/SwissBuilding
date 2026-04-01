---
name: context
description: "Reprendre un projet instantanément. Usage: /context. Reconstruit l'état mental du projet en 10 secondes."
user-invocable: true
---

# /context — Reprise de projet instantanée

Tu reviens sur un projet après des jours/semaines. Ce skill reconstruit tout le contexte nécessaire pour reprendre sans friction.

## Collecte

Exécute en parallèle :

### État du repo
```bash
git branch --show-current && git log -10 --oneline --date=relative --format="%h %ar %s" && git stash list && git status --porcelain | head -10
```

### Dernières décisions
- Lis `.claude/brainstorm_log.md` si existe — derniers verdicts
- Lis `TASKS.md` — ce qui est actif, pending, done récemment
- Lis `docs/STATUS.md` — dernier point de reprise documenté
- Lis `.orchestra/transform_log.ndjson` si existe — dernières transformations

### Mémoire projet
- Lis `.orchestra/project_memory.json` si existe — conventions, module map, décisions
- Lis `CLAUDE.md` — règles du projet

### Santé
- Lance les tests rapidement (fail-fast) — juste savoir si c'est vert ou rouge
- Check si des PR/issues sont ouvertes : `gh pr list --state open --limit 3` + `gh issue list --state open --limit 3`

## Présentation

Adapte la longueur au volume de contexte trouvé. Un projet dormant depuis 2 mois a besoin de plus qu'un projet touché hier.

Structure :

**Où on en est :**
- Branche, dernier commit, quand, par qui
- Tests verts/rouges
- Fichiers dirty ou stash en attente

**Ce qui a été décidé :**
- Les 3-5 dernières décisions/actions importantes (depuis brainstorm_log, TASKS, STATUS, git log)
- Ce qui a été validé vs ce qui est encore ouvert

**Ce qui était en cours :**
- La tâche active (depuis TASKS.md)
- Les fichiers touchés récemment
- Les PR/issues en attente

**Ce qu'il faudrait faire :**
- Recommandation basée sur l'état : tests rouges → fixer, PR en attente → merger, tâche en cours → continuer, rien d'actif → proposer prochaine action

**Ce qui a changé depuis la dernière session :**
- Si d'autres agents ont travaillé (commits non-Robin), les résumer
- Si des deps ont changé, le noter

## Pour les agents

Termine par un bloc compact parseable :
```
CONTEXT: [projet] | BRANCH: [x] | TESTS: [green/red] | LAST: [action] [date] | NEXT: [recommandation]
```

## Principes

- Ce skill ne FAIT rien — il INFORME. Pas d'exécution, pas de modification.
- Si un fichier n'existe pas (pas de brainstorm_log, pas de STATUS), skip silencieusement — ne dis pas "fichier manquant".
- Priorise les infos par utilité : ce qui est cassé > ce qui est en cours > ce qui a été décidé > le contexte historique
- L'objectif c'est que Robin (ou un agent) puisse reprendre le travail dans les 30 secondes qui suivent la lecture
