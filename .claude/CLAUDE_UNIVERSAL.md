# CLAUDE.md — Template universel

> Adapter la section "Projet" par repo.

## Projet
- Nom : [nom]
- Stack : [stack]
- État : [actif / maintenance / frozen]
- Objectif : [1 ligne]

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
