---
name: portfolio
description: "Vue d'ensemble de tous les projets Robin. Usage: /portfolio. État, tests, dernière activité de chaque repo."
user-invocable: true
---

# /portfolio — Dashboard multi-projets

Scanne tous les repos de Robin et affiche un tableau de bord unifié.

## Process

Scanne ces répertoires (adapte si d'autres existent) :
```bash
for repo in "c:/PROJET IA/test-autonomous" "c:/PROJET IA/SwissBuilding" "c:/PROJET IA/Batiscan-V4" "c:/PROJET IA/PulseOps" "c:/PROJET IA/OrbitPilot" "c:/PROJET IA/WorldEngine" "c:/PROJET IA/NegotiateAI" "c:/PROJET IA/Swissforestry" "c:/PROJET IA/FreeTime/freetime"; do
  if [ -d "$repo/.git" ]; then
    echo "=== $(basename $repo) ==="
    cd "$repo"
    git log -1 --format="%ar — %s" 2>/dev/null
    npm test 2>&1 | grep -E "^ℹ (pass|fail|tests)" 2>/dev/null || python -m pytest --co -q 2>&1 | tail -1 2>/dev/null || echo "no tests"
  fi
done
```

## Présentation

Tableau compact :

```
## /portfolio — Projets Robin

| Projet | Tests | Dernier commit | État |
|---|---|---|---|
| WorldEngine | 180/180 ✅ | 2h ago — feat: build v1 | complet |
| OrbitPilot | 62/62 ✅ | 3h ago — ... | complet |
| NegotiateAI | 3/23 ❌ | 1h ago — init | en cours |
| PulseOps | 25/25 ✅ | 5h ago — ... | complet |
| SwissBuilding | ~7000 tests | 2h ago — ... | maintenance |
| Batiscan V4 | ~700 tests | 1d ago — ... | prod |
| Swissforestry | — | just now | genesis |
| test-autonomous | 611/611 ✅ | 30m ago — ... | stable |

🟢 5 projets verts  🔴 1 projet en échec  🔵 2 en cours
```

Puis pour chaque projet en ❌ ou en cours, 1 ligne de recommandation.

## Principes
- Exécution rapide (<30s pour tous les repos)
- Ne lance PAS les tests complets de gros repos (SwissBuilding, Batiscan) — juste git log
- Si un repo n'a pas de tests, marque "—"
- Si un repo n'est pas un git repo, skip silencieusement
