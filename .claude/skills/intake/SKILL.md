---
name: intake
description: "Questionnaire pré-dev pré-rempli. Usage: /intake <idée>. Les agents brainstorment les questions, l'humain valide/corrige."
user-invocable: true
---

# /intake

L'utilisateur donne une idée. Le système génère un questionnaire de décisions pré-remplies. L'humain valide ou corrige — il ne remplit rien de zéro.

## Process

### 1. Contexte
Scanne le repo : architecture, modules, patterns, conventions. Résume en 3 lignes.

### 2. Codex génère les questions + défauts
Appelle Codex avec l'idée + le contexte. Dis-lui d'inspecter le code pertinent et de générer un questionnaire adapté au poids de l'idée :
- Petite feature → 10-15 questions
- Feature moyenne → 15-25 questions
- Gros changement → 25-35 questions

Pour chaque question : défaut pré-rempli, confiance (haute/moyenne/faible), source (repo/pattern/inférence), pourquoi ce défaut.

Catégories à couvrir (adapte le poids de chaque selon l'idée) :
- Scope & MVP
- Parcours métier / règles de gestion
- Architecture & intégration
- Données & modèle
- UX & utilisateurs
- Priorités & phasage
- Edge cases & erreurs
- Tests & validation
- Déploiement & rollback
- Risques & inconnues

### 3. Claude challenge et enrichit
Prends la liste de Codex. Challenge les réponses basse confiance contre le code réel. Ajoute les questions manquantes. Corrige les défauts faux. Fusionne les doublons. Trie par impact.

### 4. Round optionnel — si l'idée est complexe
Renvoie le questionnaire à Codex pour vérifier : questions manquantes ? contradictions ? confiances réalistes ?

### 5. Présente à l'humain

Chaque question sur 1-2 lignes :
- ✅ haute confiance — probablement correct
- ⚠️ confiance moyenne — à vérifier
- 🔴 décision critique — validation humaine requise

Groupé par section. La longueur totale s'adapte au poids de l'idée.

Termine par :
```
Tout ce qui est ✅ est pré-validé. Indique seulement les numéros à CHANGER.
Exemple: "3: non, 9: utiliser Redis, 15: pas de risque"
Si tout est bon: "ok"
```

### 6. Brief de développement
Après validation, génère un brief compact directement consommable pour développer :
- Scope validé
- Contraintes
- Décisions clés (surtout les modifiées par l'humain)
- Architecture
- Tests requis
- Risques restants
- Première étape

## Principes

- L'humain ne devrait modifier que 15-30% des réponses. Si c'est plus, le pré-remplissage est mauvais.
- Au moins 2-3 questions 🔴 — si tout est "sûr", tu ne poses pas les bonnes questions
- Le questionnaire doit être lisible en 2-3 minutes, pas 20
- Le brief final est le contrat entre l'humain et les agents — tout ce qui est dedans est validé, tout ce qui n'y est pas est hors scope
