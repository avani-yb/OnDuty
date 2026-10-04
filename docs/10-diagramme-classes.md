# 10 — Diagramme de Classes

## 1. Vue d'ensemble

Le modèle de données s'articule autour d'un utilisateur unique pouvant cumuler les rôles Client/Transporteur, d'une entité **Course** centrale (fusion de la réservation et de son suivi), et d'entités satellites pour le contrôle IA, la vérification d'identité, les paiements et les litiges.

## 2. Classes principales

### 2.1 `Utilisateur`
**Attributs :**
- `id` : identifiant unique
- `nom`, `prenom`
- `telephone`, `email`
- `mot_de_passe_hash`
- `photo_profil`
- `date_creation`
- `est_transporteur` : booléen — indique si le rôle Transporteur est activé sur ce compte
- `type_compte` : énumération (client_standard, admin) — distingue le compte admin unique du reste des utilisateurs
- `score_fiabilite` : décimal — score composite recalculé après chaque course (voir 2.7)
- `statut_compte` : énumération (actif, suspendu)

**Méthodes (conceptuelles) :**
- `activerRoleTransporteur()`
- `calculerScoreFiabilite()`
- `modifierMotDePasse()`

### 2.2 `InformationsVehicule`
**Attributs :**
- `id`
- `utilisateur` (FK vers `Utilisateur`, 1-1, présent uniquement si `est_transporteur = true`)
- `type_vehicule` : énumération (camion, pick-up, voiture)
- `marque`, `modele`
- `immatriculation`
- `capacite_max_kg`

### 2.3 `Verification` (KYC)
**Attributs :**
- `id`
- `utilisateur` (FK)
- `type_verification` : énumération (cni, vehicule)
- `statut` : énumération (en_attente, validee, rejetee)
- `date_soumission`, `date_traitement`
- `resultat_brut` : champ structuré (réponse Smile Identity ou du fallback OCR)
- `numero_tentative` : entier — permet de garder l'historique de plusieurs tentatives de vérification pour un même utilisateur

**Relation :** un `Utilisateur` peut avoir **plusieurs** `Verification` (historique complet des tentatives), une seule étant "active/validée" à un instant donné.

### 2.4 `Trajet`
**Attributs :**
- `id`
- `transporteur` (FK vers `Utilisateur`)
- `origine`, `destination`
- `date_depart`
- `capacite_disponible_kg`
- `statut` : énumération (actif, complet, expire, supprime)

### 2.5 `Demande`
**Attributs :**
- `id`
- `client` (FK vers `Utilisateur`)
- `origine`, `destination`
- `date_souhaitee`
- `description`
- `poids_estime_kg`
- `video_url`
- `statut` : énumération (en_cours_controle, validee, rejetee, publiee)

### 2.6 `ControleIA`
**Attributs :**
- `id`
- `demande` (FK, 1-1 par tentative)
- `resultat_detection_objets` : champ structuré (sortie Vision API)
- `resultat_coherence` : champ structuré (sortie Groq)
- `verdict` : énumération (valide, rejete)
- `motif_rejet` : texte (nullable)
- `date_execution`
- `duree_traitement_secondes`

**Relation :** une `Demande` peut avoir **plusieurs** `ControleIA` (une par tentative, cf. "le client recommence le processus").

### 2.7 `ContestationRejet`
**Attributs :**
- `id`
- `controle_ia` (FK)
- `client` (FK)
- `statut` : énumération (en_attente, confirmee, infirmee)
- `commentaire_admin`
- `date_soumission`, `date_traitement`

### 2.8 `Course`
*(Entité unique fusionnant réservation et suivi, conformément à ta décision — le statut évolue tout au long du cycle de vie.)*

**Attributs :**
- `id`
- `demande` (FK vers `Demande`)
- `trajet` (FK vers `Trajet`)
- `client` (FK vers `Utilisateur`)
- `transporteur` (FK vers `Utilisateur`)
- `statut` : énumération (reservee, en_attente_paiement, payee, depart, en_route, arrivee, livree, annulee, en_litige)
- `date_creation`, `date_depart_reel`, `date_livraison`

**Méthodes (conceptuelles) :**
- `annuler()`
- `mettreAJourStatut(nouveau_statut)`
- `confirmerReception()`

### 2.9 `Paiement`
**Attributs :**
- `id`
- `course` (FK, 1-1)
- `montant`
- `methode` : énumération (mtn_momo, orange_money)
- `statut` : énumération (en_attente, bloque_escrow, libere, rembourse)
- `date_paiement`, `date_liberation`
- `reference_transaction`

### 2.10 `Incident`
**Attributs :**
- `id`
- `course` (FK)
- `transporteur` (FK)
- `description` : texte libre
- `date_signalement`

### 2.11 `Litige`
**Attributs :**
- `id`
- `course` (FK)
- `declarant` (FK vers `Utilisateur` — client ou transporteur)
- `motif` : texte libre
- `statut` : énumération (ouvert, en_cours_analyse, resolu)
- `decision_admin` : texte
- `date_declaration`, `date_resolution`

### 2.12 `Evaluation`
*(Alimente le score de fiabilité du transporteur.)*
**Attributs :**
- `id`
- `course` (FK, 1-1)
- `client` (FK — évaluateur)
- `transporteur` (FK — évalué)
- `note` : entier (1 à 5)
- `commentaire` : texte (facultatif)
- `date_evaluation`

## 3. Score de fiabilité — composition

Le `score_fiabilite` d'un transporteur (attribut calculé sur `Utilisateur`) est un score composite recalculé après chaque course, intégrant plusieurs facteurs :

- **Moyenne des notes** issues des `Evaluation` reçues.
- **Taux de ponctualité** : proportion de courses où les statuts (départ, arrivée, livré) ont été mis à jour dans les délais attendus.
- **Nombre d'incidents signalés** sur ses courses (facteur pénalisant).
- **Nombre de litiges** où il a été jugé responsable (facteur pénalisant).

La formule exacte de pondération entre ces facteurs sera précisée lors de l'implémentation (probablement dans un module de service dédié, ex. `services/fiabilite.py` côté Django) — ce fichier documente les entrées du calcul, pas la formule finale.

## 4. Relations — tableau de synthèse

| Classe A | Relation | Classe B | Multiplicité |
|---|---|---|---|
| Utilisateur | possède | InformationsVehicule | 1 — 0..1 |
| Utilisateur | soumet | Verification | 1 — 0..* |
| Utilisateur (transporteur) | publie | Trajet | 1 — 0..* |
| Utilisateur (client) | initie | Demande | 1 — 0..* |
| Demande | subit | ControleIA | 1 — 1..* |
| ControleIA | peut générer | ContestationRejet | 1 — 0..1 |
| Demande | aboutit à | Course | 1 — 0..1 |
| Trajet | associé à | Course | 1 — 0..* |
| Course | génère | Paiement | 1 — 1 |
| Course | peut avoir | Incident | 1 — 0..* |
| Course | peut avoir | Litige | 1 — 0..* |
| Course | génère | Evaluation | 1 — 0..1 |
| Utilisateur (client) | déclare | Litige | 1 — 0..* |
| Utilisateur (transporteur) | déclare | Litige | 1 — 0..* |

## 5. Notes de conception

- Le choix d'une entité `Course` unique (plutôt qu'une séparation Réservation/Course) simplifie le modèle et colle à la réalité métier : il n'y a pas de distinction fonctionnelle entre "réservé" et "en cours", juste des statuts successifs.
- L'historisation de `Verification` et `ControleIA` (plusieurs enregistrements possibles) est essentielle pour l'audit et la gestion des contestations — c'est un point de vigilance à ne pas simplifier lors de l'implémentation.
- Le score de fiabilité étant recalculé après chaque course, prévoir soit un recalcul synchrone (simple mais coûteux à l'échelle), soit une tâche asynchrone déclenchée à la clôture de chaque course (préférable, à discuter dans `13-architecture-technique.md`).
