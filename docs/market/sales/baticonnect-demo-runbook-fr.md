# BatiConnect — Runbook de Demo (FR)

Version: V1 — Demo unique 20 minutes
Date: 28 mars 2026

---

## Meta

| | |
|---|---|
| **Duree** | 20 minutes |
| **Buyer cible** | Responsable technique de gerance multi-batiments VD/GE |
| **Objectif** | Le prospect comprend que son dossier n'est pas pret alors qu'il pensait qu'il l'etait |
| **Scenario** | Batiment ancien VD, pre-1990, amiante, AOT imminente |
| **Sortie attendue** | Le prospect accepte un pilote paye sur ses propres batiments |

---

## Preparation avant la demo

- [ ] Seed prospect-grade charge et verifie
- [ ] Batiment demo avec trous reels: diagnostic perime, scope mismatch, contradiction
- [ ] Flow complet teste: passport → completeness → readiness → actions → pack autorite
- [ ] Aucun bug critique sur le chemin must-win
- [ ] Temps de chargement < 3 secondes sur chaque ecran

---

## Script minute par minute

### 0:00 — 2:00 | Contexte et cadrage

**Ce qu'on fait**: poser le cadre, pas montrer le produit.

**Phrase d'introduction**:
"Imaginons un immeuble des annees 70 a Lausanne. Vous avez un appel d'offres pour des travaux d'assainissement dans 2 mois. Votre dossier polluants est dans un drive, avec des rapports de 2 labos differents. Vous pensez que c'est a peu pres complet. Voyons ce qu'il en est vraiment."

**Ecran**: aucun. On parle.

**Objectif**: le prospect se reconnait dans la situation.

---

### 2:00 — 5:00 | Passeport batiment — "Ca a l'air documente"

**Ecran**: Building Overview / Passport

**Phrase d'introduction**:
"Voici le passeport de cet immeuble. Vous voyez: il y a des diagnostics, des documents, un historique. A premiere vue, ca a l'air documente."

**Ce qu'on montre**:
- Grade A-F visible
- Nombre de documents/diagnostics
- Apparence de completude

**Ce qu'on ne dit PAS encore**: les trous. On laisse le prospect penser que c'est OK.

**Objectif**: creer le contraste pour le reveal qui suit.

---

### 5:00 — 9:00 | Completude + Readiness — le reveal

**Ecran**: Completeness Engine → Readiness

**Phrase d'introduction**:
"Maintenant, regardons ce que le systeme voit reellement. Pas juste les documents qui existent, mais ce qui manque, ce qui est perime, et si le dossier est procéduralement pret."

**Ce qu'on montre**:
- Score de completude avec les trous explicites
- Verdict readiness: "pas pret" ou "pret sous conditions"
- Raisons: piece manquante, diagnostic perime, scope incomplet
- Chaque verdict avec sa provenance

**Aha moment**:
"Vous voyez ? Les PDF existent, mais le dossier n'est pas pret. Le diagnostic amiante date de 2019 et ne couvre pas les caves. Votre perimetre travaux inclut les caves. Si vous soumettez ca, l'autorite vous le renvoie."

**Objectif**: le prospect realise que "avoir des documents" ≠ "etre pret".

---

### 9:00 — 12:00 | Diagnostic perime, scope mismatch, contradiction

**Ecran**: detail du diagnostic / contradiction detector

**Phrase d'introduction**:
"Regardons de plus pres. Le systeme a detecte 3 problemes concrets."

**Ce qu'on montre** (choisir 1-2 selon le seed):
- **Diagnostic perime**: date de validite depassee, perimetre trop ancien
- **Scope mismatch**: le diagnostic ne couvre pas la zone prevue pour les travaux
- **Contradiction**: deux rapports se contredisent sur la presence d'amiante dans le meme element

**Phrase cle**:
"Personne ne voit ca aujourd'hui dans un drive. Il faut ouvrir chaque PDF, comparer les dates, verifier les perimetres. BatiConnect le fait automatiquement."

**Objectif**: montrer la profondeur de detection.

---

### 12:00 — 15:00 | Actions correctives concretes

**Ecran**: Actions / Unknown Generator / Readiness Action Generator

**Phrase d'introduction**:
"Le systeme ne se contente pas de montrer les problemes. Il les transforme en actions concretes."

**Ce qu'on montre**:
- Liste d'actions generee automatiquement
- Chaque action liee a un blocage precis
- Priorite, responsable suggere, deadline
- Format: pourquoi / preuve / action suivante

**Phrase cle**:
"Voila ce que votre RT aurait du savoir il y a 3 semaines. Pas un PDF de plus: une liste d'actions claires pour debloquer le dossier."

**Objectif**: passer du probleme a la solution.

---

### 15:00 — 18:00 | Resoudre un trou et relancer

**Ecran**: resolution d'action → re-evaluation readiness

**Phrase d'introduction**:
"Simulons: on resout un des trous. Je marque cette action comme traitee et je relance l'evaluation."

**Ce qu'on montre**:
- Marquer une action comme resolue
- Relancer le readiness_reasoner
- Le score de completude monte
- Le verdict readiness change (ex: "pas pret" → "pret sous conditions")

**Phrase cle**:
"Chaque action resolue ameliore le dossier de facon mesurable. Pas de boite noire: vous voyez exactement l'impact."

**Objectif**: montrer que le systeme est vivant, pas statique.

---

### 18:00 — 20:00 | Pack autorite + close

**Ecran**: generation pack autorite → conclusion

**Phrase d'introduction**:
"Quand le dossier est pret, vous generez le pack autorite en un clic. Avec provenance, completude, et tracabilite."

**Ce qu'on montre**:
- Generation du pack autorite
- Contenu: pieces incluses, completude, readiness, provenance

**Metriques a rappeler**:
1. Temps de preparation: heures au lieu de jours
2. Trous detectes avant soumission: [nombre] pieces manquantes revelees
3. Retours d'autorite evites: zero surprise apres soumission

**Phrase de close**:
"Ce que vous avez vu en 20 minutes, c'est la difference entre penser que le dossier est complet et savoir qu'il est pret. On peut faire la meme chose sur 5-10 de vos batiments reels en 6-8 semaines. Pilote paye, scorecard avant/apres. Interesse ?"

---

## Plans de secours

### Si un ecran echoue

Ne pas paniquer. Dire: "Le systeme calcule en temps reel, laissez-moi rafraichir." Si le probleme persiste, passer a l'ecran suivant et revenir plus tard. Ne jamais s'arreter sur un bug — le prospect retient la derniere impression.

### Si un score n'est pas comprehensible

Dire: "Ce score combine [X] criteres. Ce qui compte, c'est la raison: [pointer la raison explicite]. Le score est un resume; la raison est la verite."

Ne jamais defendre un chiffre abstrait. Toujours ramener a la raison concrete.

### Si le prospect coupe pour poser des questions

C'est un bon signe. Repondre brievement (30 secondes max), puis dire: "Excellent, je vais justement vous montrer ca dans la suite de la demo." Reprendre le fil. Ne pas transformer la demo en Q&A.

### Si le prospect demande "combien ca coute ?"

Repondre directement: "Le pilote est a CHF 5-10k pour 5-10 batiments sur 6-8 semaines. Payant, cadre, avec scorecard. Si les resultats sont la, on convertit en abonnement annuel. Je peux vous envoyer la proposition cette semaine."

Ne jamais esquiver la question du prix.

---

## Erreurs a eviter

- Ne pas montrer le portefeuille ou la comparaison multi-batiments (hors scope V1)
- Ne pas parler d'IA en premier — parler de completude et readiness
- Ne pas faire une visite exhaustive du produit — suivre le script narratif
- Ne pas montrer des ecrans "vides" ou "parfaits" — le reveal marche parce que ca a l'air bien puis on montre les trous
- Ne pas utiliser de jargon technique (rule_resolver, completeness_engine) — parler en langage metier
