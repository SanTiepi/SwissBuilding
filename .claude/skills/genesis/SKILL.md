---
name: genesis
description: "De l'idée au repo prêt-à-construire. Usage: /genesis <idée en 1 ligne>. Brainstorm + intake + génération du repo complet."
user-invocable: true
---

# /genesis — De l'idée au repo fonctionnel

L'utilisateur donne une idée en 1 ligne. Le skill produit un repo complet et prêt — un agent senior peut l'ouvrir et construire avec juste "Go."

## Flow

### 1. Détecte le type de projet

Avant tout, classifie automatiquement :

- **Site web / landing page** → HTML/CSS/JS pur, pas de build, pas de tests unitaires
- **API / backend** → Node.js ESM ou Python FastAPI, modules + tests
- **CLI tool** → Node.js ESM, commandes + tests
- **App full-stack** → backend + frontend séparés
- **Librairie / SDK** → exports + tests + docs
- **Autre** → adapte au contexte

Le type de projet change TOUT : la structure, les fichiers générés, les tests, les commandes, le CLAUDE.md.

### 2. Brainstorm multi-expert (30s)

Challenge l'idée. Fais parler 3-5 experts de domaines DIFFÉRENTS selon l'idée :
- Choisis les experts les plus pertinents ET les plus inattendus
- Chaque expert donne 1 insight unique en 1-2 lignes
- Applique la pensée divergente : cadre implicite, contraire vrai, analogie forcée
- Utilise Codex si disponible (en background)

### 3. Intake express (2 min)

15-20 décisions pré-remplies. L'utilisateur valide/corrige.
Présente avec ✅ ⚠️ 🔴.

### 4. Génération du repo

Adapte la structure au type de projet détecté :

#### Type: Site web / landing page
```
[projet]/
  index.html          — page complète avec CSS intégré
  assets/             — images, fonts si nécessaire
  CLAUDE.md           — brief du site, sections, design, contenu
  .gitignore
```
Pas de tests unitaires. Le "test" c'est : le site s'ouvre dans un navigateur et tous les liens/sections fonctionnent.

#### Type: API / backend Node.js
```
[projet]/
  CLAUDE.md            — mission, contrats d'interface, architecture
  package.json         — scripts (test, start)
  src/                 — 1 fichier squelette par module (exports qui throw)
  test/                — 1 fichier de test par module (tests qui FAILENT = contrat)
  .claude/skills/      — skills universels
  .gitignore
```

#### Type: API / backend Python
```
[projet]/
  CLAUDE.md
  pyproject.toml / requirements.txt
  app/                 — modules avec stubs
  tests/               — pytest tests qui failent
  .claude/skills/
  .gitignore
```

#### Type: CLI tool
```
[projet]/
  CLAUDE.md
  package.json         — bin entry point
  src/
    cli.mjs            — argument parsing + dispatch
    [modules].mjs      — logique métier
  test/
  .claude/skills/
  .gitignore
```

#### Type: Full-stack
```
[projet]/
  CLAUDE.md
  backend/             — API (Node.js ou Python)
  frontend/            — HTML/CSS/JS ou framework
  .claude/skills/
  .gitignore
```

### 5. CLAUDE.md adapté au type

Le CLAUDE.md généré contient TOUT ce qu'un agent a besoin. Son contenu s'adapte :

- **Site web** : brief créatif, sections attendues, palette de couleurs, contenu texte, CTA, responsive requirements
- **API** : contrats d'interface (signatures), architecture modules, décisions figées, commandes test/start
- **CLI** : commandes supportées, arguments, format de sortie
- **Full-stack** : les deux

### 6. Init Git + commit

```bash
git init && git add -A && git commit -m "genesis: [nom] — repo prêt pour construction"
```

### 7. Lancer la construction

Lance en background si possible :
```bash
cd [chemin] && claude -p "You are a senior autonomous engineer for this repo. Read CLAUDE.md. Build it." --dangerously-skip-permissions > .genesis_build.log 2>&1 &
```

Si pas possible (session imbriquée), donne le prompt à copier-coller.

Résumé pour l'utilisateur :
```
✅ Repo [nom] créé dans [chemin]
📁 Type: [site web / API / CLI / full-stack]
🚀 Construction lancée en autonomie
📊 [X] fichiers à créer
```

## Principes

- Détecte le type AUTOMATIQUEMENT — ne demande jamais "c'est quoi comme projet ?"
- Le brainstorm doit SURPRENDRE
- L'intake doit être RAPIDE — 2 min max
- Le repo doit être COMPLET pour le type détecté
- Tout le travail intellectuel est fait AVANT le code
