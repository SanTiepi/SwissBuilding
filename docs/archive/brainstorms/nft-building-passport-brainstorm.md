# NFT Building Passport — Brainstorm

> Date: 2026-04-01
> Status: Brainstorm — à valider
> Auteurs: Robin Fragnière + Claude + Codex

---

## Pourquoi un NFT pour le passeport bâtiment?

### Le problème réel aujourd'hui

Le dossier bâtiment est un **PDF dans un email**. Il a ces défauts:
1. **Pas de chaîne de confiance**: qui a produit ce PDF? Quand? A-t-il été modifié?
2. **Pas d'historique prouvable**: impossible de savoir ce qui a changé entre deux versions
3. **Pas de vérification sans accès**: un tiers (banque, assureur) doit demander le dossier au propriétaire
4. **Pas de transfert automatique**: lors d'une vente, le dossier "tombe" souvent dans un email perdu
5. **Pas de valeur marchande**: le dossier est un coût, jamais un actif
6. **Pas d'interopérabilité**: chaque plateforme a son format

### Ce que le NFT résout

Le NFT n'est PAS un gadget crypto. C'est un **registre décentralisé de preuves vérifiables**.

| Problème | Solution NFT |
|----------|-------------|
| Qui a produit le dossier? | Émetteur = adresse wallet vérifiable (BatiConnect) |
| A-t-il été modifié? | Hash du contenu = immuable sur la chaîne |
| Historique des versions? | Chaque version = nouveau token lié au précédent |
| Vérification par un tiers? | Scan QR/lien → état vérifié sans compte ni login |
| Transfert lors de vente? | Token transféré au nouveau propriétaire (ou automatique via notaire) |
| Interopérabilité? | Standard ouvert (ERC-721/1155 + metadata JSON-LD) |

---

## Quel modèle NFT?

### Option A — Soulbound Building Token (SBT) ← RECOMMANDÉ

**Concept**: Chaque bâtiment a un token non-transférable lié à son EGID. Le token ne change pas de main — il est lié au bâtiment, pas au propriétaire. C'est un **certificat d'identité du bâtiment**.

**Avantages**:
- Pas de spéculation (c'est un certificat, pas un actif tradable)
- Compatible avec la vision "passeport" (le passeport reste avec le bâtiment, pas avec la personne)
- Simplifie la compliance FINMA (pas un instrument financier)
- Pas de marché secondaire à gérer

**Contenu on-chain** (minimal, ~500 bytes):
```json
{
  "egid": 123456,
  "passport_version": 42,
  "grade": "B+",
  "completeness": 0.87,
  "timestamp": "2026-04-01T10:00:00Z",
  "issuer": "0x...BatiConnect",
  "content_hash": "sha256:abc123...",
  "metadata_uri": "https://api.baticonnect.ch/passport/123456/v42"
}
```

**Contenu off-chain** (dans BatiConnect, accessible via URI):
- Dossier complet, diagnostics, preuves, timeline, scores, rapports
- Accessible avec permission (public: grade + completeness, privé: tout le reste)

### Option B — NFT Versioned Passport

**Concept**: Chaque version du passeport = un nouveau NFT (ERC-721). La chaîne de tokens forme l'historique. Le dernier token est le passeport actuel.

**Avantages**:
- Historique complet on-chain
- Transferable lors de vente (le notaire transfère le dernier token)
- Vérifiable par n'importe qui

**Inconvénients**:
- Coût gas par version (atténué par L2)
- Plus complexe à gérer
- Pourrait être classifié comme actif financier par FINMA

### Option C — Verifiable Credential (VC) sans blockchain

**Concept**: Pas de NFT du tout. Utiliser le standard W3C Verifiable Credentials avec signature cryptographique de BatiConnect.

**Avantages**:
- Pas de blockchain à maintenir
- Standard W3C reconnu
- Vérifiable hors ligne
- Zéro coût gas

**Inconvénients**:
- Pas de registre décentralisé (confiance = BatiConnect uniquement)
- Pas d'historique immuable tiers
- Moins "wow" pour le marketing

### Recommandation: Approche hybride SBT + VC

1. **SBT on-chain** (Soulbound): identité du bâtiment + hash du passeport actuel + grade + completeness
2. **Verifiable Credentials off-chain**: chaque attestation (diagnostic, conformité, readiness) = un VC signé par BatiConnect
3. **Metadata off-chain**: tout le contenu détaillé dans BatiConnect, accessible via URI

Le SBT prouve l'existence et l'état. Les VC prouvent les détails. BatiConnect stocke tout.

---

## Architecture technique

### Blockchain recommandée

| Option | Pour | Contre | Coût/tx |
|--------|------|--------|---------|
| **Base (Coinbase L2)** | L2 Ethereum, frais très bas, écosystème solide | US-based | ~$0.001 |
| **Polygon PoS** | Mature, low-cost, large adoption | Centralisation partielle | ~$0.01 |
| **Tezos** | Suisse (fondation Zoug), energy-efficient, smart contracts formels | Écosystème plus petit | ~$0.005 |
| **Ethereum L1** | Maximum crédibilité/sécurité | Coût prohibitif pour volume | ~$5-50 |

**Recommandation**: **Base ou Tezos**
- Base: meilleur écosystème, coûts minimaux, ERC-721/SBT natif
- Tezos: narratif suisse fort (fondation à Zoug), bon pour le marché CH

### Smart Contract

```solidity
// BuildingPassportSBT.sol (simplified)
contract BuildingPassportSBT is ERC721, Ownable {
    struct PassportState {
        uint256 egid;
        string grade;           // "A" to "F"
        uint16 completeness;    // 0-1000 (0.0-100.0%)
        bytes32 contentHash;    // SHA-256 of full passport JSON
        string metadataUri;     // https://api.baticonnect.ch/passport/{egid}/v{version}
        uint256 version;
        uint256 timestamp;
    }
    
    mapping(uint256 => PassportState) public passports; // tokenId => state
    mapping(uint256 => uint256) public egidToToken;     // EGID => tokenId
    
    // Soulbound: disable transfers
    function _beforeTokenTransfer(address from, address to, uint256) internal pure override {
        require(from == address(0) || to == address(0), "Soulbound: non-transferable");
    }
    
    function mintPassport(uint256 egid, string grade, uint16 completeness, 
                          bytes32 contentHash, string metadataUri) external onlyOwner {
        // Mint new SBT for building
    }
    
    function updatePassport(uint256 egid, string grade, uint16 completeness,
                           bytes32 contentHash, string metadataUri) external onlyOwner {
        // Update existing passport state (new version)
    }
    
    function verify(uint256 egid) external view returns (PassportState memory) {
        // Anyone can verify passport state
    }
}
```

### Intégration avec BatiConnect existant

```
passport_service.py
  └→ generate_passport()
      └→ compute SHA-256 hash
      └→ call smart contract updatePassport()
      └→ store tx_hash in building_passport_state.blockchain_tx
      └→ return passport + verification_url

QR code on pack PDF:
  └→ https://verify.baticonnect.ch/{egid}
      └→ reads on-chain state
      └→ compares hash with current passport
      └→ displays: ✅ Verified | Grade: B+ | Completeness: 87% | Updated: 2026-04-01
```

---

## Cas d'usage concrets

### CU-1: Vérification par l'autorité (P0 — killer use case)

**Aujourd'hui**: L'autorité reçoit un PDF par email. Elle ne sait pas s'il est à jour, complet, ou authentique.

**Avec NFT**: L'autorité scanne le QR code sur le pack. Elle voit instantanément:
- ✅ Passeport vérifié (hash match)
- Grade: B+
- Complétude: 87%
- Dernière mise à jour: il y a 3 jours
- Émetteur: BatiConnect (vérifié)
- 6 diagnostics, 4 interventions, 2 preuves post-travaux

**Pas besoin de compte BatiConnect. Pas besoin de login. Juste scanner.**

### CU-2: Mutation immobilière / vente (P0)

**Aujourd'hui**: Le notaire demande "le dossier du bâtiment". Le vendeur cherche dans ses emails. 50% du dossier est perdu. Due diligence = 2 semaines.

**Avec NFT**: Le notaire scanne le SBT. Il voit l'historique complet:
- 42 versions du passeport depuis 2026
- Grade passé de D → C → B+ en 3 ans
- Toutes les interventions documentées
- Due diligence en 5 minutes au lieu de 2 semaines

### CU-3: Hypothèque bancaire (P1)

**Aujourd'hui**: La banque demande une expertise. Coût: 2-5k CHF. Délai: 2-4 semaines.

**Avec NFT**: La banque vérifie le SBT:
- Score bancabilité: 78/100
- Aucun polluant critique non traité
- Énergie classe C (trajectoire vers B)
- Assurance à jour, sinistralité basse
- → Pré-approbation accélérée, expertise réduite

### CU-4: Assurance (P1)

**Aujourd'hui**: Renouvellement annuel = questionnaire papier rempli par le propriétaire (souvent faux/incomplet).

**Avec NFT**: L'assureur vérifie le SBT en temps réel:
- Profil risque actualisé automatiquement
- Capteurs OK → réduction prime auto
- Historique sinistres vérifié et immuable
- → Tarification dynamique, juste, sans paperasse

### CU-5: Certificat vert / ESG (P2)

**Aujourd'hui**: Les rapports ESG immobiliers sont déclaratifs et non vérifiables.

**Avec NFT**: Score durabilité on-chain, vérifiable par les investisseurs:
- Émissions CO2/m2 vérifiées
- Interventions de rénovation énergétique prouvées
- Trajectoire vers Net Zero documentée
- → Green bond eligibility vérifiable

---

## Cadre légal suisse

### Loi DLT (2021)

La Suisse est l'un des pays les plus avancés au monde pour la réglementation blockchain:

1. **Art. 973d CO** (nouveau): Les droits-valeurs inscrits dans un registre de droits-valeurs (DLT) sont reconnus légalement
2. **LSFIN/LEFin**: Cadre pour les prestataires de services financiers
3. **FINMA Token Classification**:
   - **Payment token**: NON (le SBT n'est pas un moyen de paiement)
   - **Utility token**: OUI — le SBT donne accès à un service (vérification passeport)
   - **Asset token**: NON si SBT (non-transférable, pas de valeur marchande)

### Classification recommandée

Le Building Passport SBT est un **utility token** car:
- Il n'est pas transférable (soulbound)
- Il n'a pas de valeur marchande propre
- Il donne accès à un service de vérification
- Il ne représente pas un droit financier

→ **Pas de licence FINMA nécessaire** pour un utility token

### Protection des données (nLPD)

**On-chain** (public): EGID, grade, completeness, hash, timestamp — pas de données personnelles
**Off-chain** (protégé): tout le contenu détaillé — accès contrôlé par BatiConnect

→ **Compatible nLPD** car aucune donnée personnelle on-chain

---

## Modèle économique

### Qui paie?

| Acteur | Ce qu'il paie | Prix indicatif | Valeur reçue |
|--------|--------------|----------------|-------------|
| Propriétaire/gérance | Abonnement BatiConnect (inclut NFT) | 0 CHF additionnel | Passeport vérifiable, transfert facile |
| Notaire | Vérification due diligence | 50-200 CHF/transaction | DD en 5 min au lieu de 2 semaines |
| Banque | API vérification score | 20-100 CHF/query | Pré-approbation accélérée |
| Assureur | Feed risque temps réel | 500-2000 CHF/an/1000 bâtiments | Tarification dynamique |
| Autorité | Gratuit (adoption) | 0 CHF | Vérification instantanée |

### Revenue additionnel estimé

Avec 1000 bâtiments sur la plateforme:
- Notaires: 50 mutations/an × 100 CHF = 5k CHF/an
- Banques: 100 queries/an × 50 CHF = 5k CHF/an
- Assureurs: 2 contrats × 1000 CHF = 2k CHF/an
- **Total additionnel: ~12k CHF/an pour 1000 bâtiments**

Avec 10'000 bâtiments: ~120k CHF/an additionnel (et growing)

La vraie valeur n'est pas le revenu NFT direct — c'est le **lock-in** et le **moat**:
- Une fois le SBT émis, le bâtiment est "inscrit" dans BatiConnect de façon irréversible
- Les tiers (banques, assureurs, notaires) s'habituent à vérifier via le SBT
- Le réseau d'effet rend le passeport plus précieux à chaque nouvel acteur connecté

---

## Roadmap NFT

### Phase 1 — Proof of Concept (M6-M9, ~4 semaines dev)

| # | Item | Effort | Detail |
|---|------|--------|--------|
| 1 | Smart contract SBT (Tezos ou Base testnet) | 1 semaine | Mint, update, verify |
| 2 | Integration passport_service → blockchain | 1 semaine | Hash + publish on mint/update |
| 3 | Page de vérification publique | 1 semaine | verify.baticonnect.ch/{egid} — scan QR |
| 4 | QR code sur tous les packs PDF | 2 jours | Ajout auto du QR vérification |
| 5 | Demo avec 5 bâtiments pilotes | 1 semaine | Mint SBT pour bâtiments seed |

**Coût total Phase 1: ~4 semaines dev + ~$50 frais blockchain (testnet gratuit)**

### Phase 2 — Mainnet + Partenaires (M9-M12)

| # | Item | Effort | Detail |
|---|------|--------|--------|
| 6 | Déploiement mainnet | 1 semaine | Migration testnet → mainnet |
| 7 | API vérification pour tiers | 2 semaines | REST API: GET /verify/{egid} |
| 8 | Partenariat notaire pilote | 2 semaines | 1 étude notariale VD teste la vérification |
| 9 | Verifiable Credentials pour attestations | 2 semaines | VC signées pour chaque diagnostic/conformité |
| 10 | Page publique portfolio | 1 semaine | "X bâtiments vérifiés sur BatiConnect" |

### Phase 3 — Écosystème (M12-M18)

| # | Item | Detail |
|---|------|--------|
| 11 | API bancaire (score hypothécaire) | Feed vérifiable pour banques |
| 12 | Feed assureur (risque temps réel) | API temps réel pour assureurs |
| 13 | Standard ouvert publié | Specification du Building Passport Token |
| 14 | Partenariat registre foncier | Discussion avec autorités |
| 15 | Cross-platform interop | Autres plateformes immobilières peuvent vérifier |

---

## Risques et mitigations

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| "C'est de la crypto, je ne comprends pas" | Haute | Moyen | Jamais mentionner "NFT" au client — parler de "passeport vérifiable" ou "certificat numérique" |
| FINMA requalifie en asset token | Basse | Haute | SBT non-transférable = utility token clair. Avis juridique préventif. |
| Coûts blockchain augmentent | Basse | Basse | L2 = frais quasi-nuls. Migrable entre L2s. |
| Adoption tiers lente | Haute | Moyen | Commencer par la valeur interne (vérification sans login). Tiers = phase 2. |
| Privacy leak on-chain | Basse | Haute | ZERO données personnelles on-chain. Seulement: EGID, hash, grade, completeness. |

---

## Décision clé: le wording

**NE JAMAIS dire "NFT" aux clients.** 

Dire:
- "Passeport bâtiment certifié numériquement"
- "Certificat d'état vérifiable"
- "Preuve d'authenticité blockchain"
- "Sceau numérique BatiConnect"

Le mot "NFT" = baggage négatif (spéculation, crypto-bros, Bored Apes). La technologie est bonne. Le branding doit être sobre et professionnel.

---

## Apport Codex — Points critiques (2026-04-01)

### Ce qui fait sens (validé Codex)
- **Mutation/refinancement**: acheteur, banque, assureur, notaire vérifient instantanément le dernier état certifié
- **Preuve de conformité**: autorité ou assureur scanne un QR, voit émetteur/date/statut/scope sans ouvrir BatiConnect
- **Underwriting portefeuille**: banque/assureur ingère des preuves standardisées sur des centaines d'immeubles sans chasing documentaire

### Ce qui ne fait PAS sens (alerte Codex)
- ❌ **Token comme titre de propriété**: en Suisse, les droits réels passent par le registre foncier, pas par un NFT
- ❌ **NFT transférable = transfert immobilier**: dangereux juridiquement. Le transfert juridique reste notarial/foncier
- ❌ **Wallet owner-facing avec seed phrase**: trop de friction pour gérances, notaires, propriétaires
- ❌ **Asset token avec droits économiques**: glisse vers classification FINMA lourde

### Recommandation Codex: MVP sans blockchain d'abord

**Séquence pragmatique**:
1. **D'abord**: Building Credential signé (QES/regulated seal + W3C Verifiable Credentials + registre de révocation)
2. **Ensuite**: Ancrage blockchain SEULEMENT si les tiers demandent une preuve publique indépendante
3. **Jamais**: Token comme substitut au registre foncier

### Standards recommandés
- Certificat unique: `ERC-721 + ERC-5192` (soulbound)
- Famille d'attestations: `ERC-1155`
- Sur Tezos: `FA2` avec politique `no-transfer`
- **Interop utile**: `VC / OpenID4VCI / OpenID4VP` >> marketplace NFT

### Budget réaliste (Codex)
| Phase | Budget | Scope |
|-------|--------|-------|
| MVP credentials | CHF 150-300k | Credential + QR verifier + révocation + export |
| + juridique + audit | CHF 300-700k | Avis juridique, audit sécu, pilote partenaire |
| Full produit | > CHF 1M | Wallet, public chain, partenaires multiples |

### Infrastructure suisse pertinente
- **eGRIS**: numérisation du registre foncier suisse (egris.admin.ch) — futur pont possible
- **e-ID suisse**: infrastructure nationale de credentials en construction (eid.admin.ch)
- **Swisscom Digital Trust**: signature électronique qualifiée
- **Loi DLT (2021)**: crée sécurité juridique pour droits tokenisés, mais pas raccourci vers registre foncier

### Avis Codex (verbatim)
> "Il y a une vraie opportunité, mais seulement si vous vendez un réseau de vérification et de handoff, pas un objet crypto."

---

## Conclusion

### Approche recommandée (synthèse Claude + Codex)

**Phase 1 (M6-M9): Verifiable Credential sans blockchain**
- Signature QES (Swisscom Digital Trust ou SwissSign)
- W3C Verifiable Credentials pour chaque attestation
- QR code vérification sur tous les packs PDF
- Page publique verify.baticonnect.ch/{egid}
- **Coût: ~4 semaines dev + CHF 5-10k signature électronique**

**Phase 2 (M9-M12): Ancrage blockchain optionnel**
- SBT sur Base ou Tezos (testnet d'abord)
- Hash du passeport + grade + completeness on-chain
- Version lineage (chaque version liée à la précédente)
- **Seulement si Phase 1 prouve la demande tiers**

**Phase 3 (M12-M18): Écosystème partenaires**
- API pour notaires, banques, assureurs
- Pilote avec 1 étude notariale VD
- Alignement avec eGRIS et e-ID suisse
- Standard ouvert publié

### Pourquoi c'est un moat

Le Building Passport SBT/VC n'est pas un gadget. C'est une **infrastructure de confiance** qui:
1. Rend le passeport vérifiable sans compte ni login
2. Crée un historique immuable et auditable
3. Facilite le transfert lors des mutations
4. Ouvre des revenus B2B (notaires, banques, assureurs)
5. Construit un moat quasi-irréversible (bâtiment inscrit = bâtiment verrouillé)
6. S'aligne avec l'infrastructure e-ID et eGRIS suisse en construction

**Le mot d'ordre: "Passeport bâtiment certifié", JAMAIS "NFT".**
