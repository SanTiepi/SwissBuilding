---
name: fix-loop
description: "Boucle automatique code→test→diagnostic→fix→retest. Usage: /fix-loop ou automatique après un test fail."
user-invocable: true
---

# /fix-loop — Boucle test/fix automatique

Quand les tests échouent après une modification, cette boucle diagnostique et corrige automatiquement.

## Déclenchement
- Explicite : l'utilisateur tape `/fix-loop`
- Automatique : après toute modification de code, si les tests ciblés échouent

## Boucle

### 1. Lancer les tests ciblés
Exécute les tests sur les fichiers modifiés. Pas la suite complète sauf si nécessaire.

### 2. Si vert → terminé
Dis "Tests verts" et passe à la suite.

### 3. Si rouge → diagnostic
Lis l'erreur. Donne en 3 lignes max :
```
SYMPTÔME: [ce qui fail]
CAUSE: [pourquoi, basé sur le stack trace et le code]
FIX: [ce qu'il faut changer]
```

### 4. Applique le fix
Fais la modification minimale. Pas de refactor, pas d'amélioration — juste le fix.

### 5. Retest
Relance les mêmes tests. Si vert → terminé. Si rouge → retour au step 3.

### 6. Limite
Max 3 itérations. Si toujours rouge après 3 tentatives :
```
BLOQUÉ: [ce qui fail encore]
HYPOTHÈSE: [pourquoi les fix n'ont pas marché]
ACTION: [demander à l'utilisateur ou investiguer plus profondément]
```

## Principes
- Fix minimal — ne pas profiter du fix pour "améliorer" le code
- Diagnostic avant action — comprendre le problème avant de le corriger
- Transparence — montrer chaque étape, pas juste le résultat final
- Pas de boucle infinie — 3 itérations max puis stop
