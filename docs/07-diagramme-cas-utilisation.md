# 07 — Diagramme de Cas d'Utilisation

## 1. Acteurs

- **Visiteur**
- **Client** (rôle actif par défaut sur tout compte)
- **Transporteur** (rôle activable en complément du rôle Client, jamais exclusif — cf. `03-acteurs-parties-prenantes.md`)
- **Administrateur**
- **Système IA** (acteur secondaire / système externe : regroupe les API de contrôle — Vision API, Groq, Smile Identity — sollicitées par le système, pas un acteur humain)
- **Système de paiement mobile** (acteur secondaire : MTN MoMo / Orange Money)

## 2. Vue d'ensemble par acteur

### 2.1 Visiteur
- UC-01 : Consulter la page de branding
- UC-02 : Créer un compte

### 2.2 Client
- UC-03 : Initier une demande d'expédition
- UC-04 : Consulter les propositions de matching
- UC-05 : Sélectionner un transporteur
- UC-06 : Payer une course
- UC-07 : Consulter l'historique des paiements
- UC-08 : Suivre la progression du colis
- UC-09 : Confirmer la réception
- UC-10 : Gérer son profil
- UC-11 : Vérifier sa CNI
- UC-12 : Devenir transporteur
- UC-13 : Annuler une réservation
- UC-14 : Contester un rejet IA
- UC-15 : Déclarer un litige

### 2.3 Transporteur
- UC-16 : Ajouter un trajet
- UC-17 : Supprimer un trajet
- UC-18 : Consulter les demandes compatibles avec son trajet
- UC-19 : Accepter une demande
- UC-20 : Signaler un incident
- UC-21 : Mettre à jour le statut d'une course
- UC-22 : Consulter l'historique des paiements
- UC-23 : Gérer son profil (+ informations véhicule)
- UC-15 (partagé) : Déclarer un litige

### 2.4 Administrateur
- UC-24 : Gérer les comptes utilisateurs
- UC-25 : Visualiser le tableau de bord
- UC-26 : Traiter un litige
- UC-27 : Traiter une contestation de rejet IA

## 3. Relations structurantes (include / extend)

- **UC-03 (Initier une demande) *include* UC-IA-01 (Exécuter le contrôle IA)** : impossible de créer une demande sans passer par le contrôle IA — relation obligatoire.
- **UC-IA-01 *extend* UC-14 (Contester un rejet IA)** : la contestation n'intervient que dans le cas alternatif où le contrôle IA rejette la demande.
- **UC-14 *include* UC-27 (Traiter une contestation)** : toute contestation soumise par le client déclenche systématiquement une action admin.
- **UC-05 (Sélectionner un transporteur) *include* UC-19 (Accepter une demande)** côté transporteur : la réservation n'est confirmée que lorsque les deux actions se rencontrent (sélection client + acceptation transporteur) — relation de synchronisation plutôt qu'un simple include unidirectionnel, à représenter comme un point de jonction entre les deux cas.
- **UC-06 (Payer une course) *include* UC-PAIEMENT-01 (Créer une transaction escrow)** : tout paiement passe par la création d'un enregistrement escrow, pas de paiement direct sans passage par l'escrow.
- **UC-09 (Confirmer la réception) *extend* UC-PAIEMENT-02 (Libérer les fonds escrow)** : la libération des fonds est déclenchée par la confirmation, mais reste un cas distinct côté modélisation (peut aussi être déclenchée par UC-26 en cas de litige résolu en faveur du transporteur).
- **UC-15 (Déclarer un litige) *extend* UC-20 (Signaler un incident)** : un signalement d'incident peut mener à un litige, mais les deux restent des cas distincts (un incident signalé n'entraîne pas automatiquement un litige).
- **UC-12 (Devenir transporteur) *include* UC-11 (Vérifier sa CNI)** : impossible d'activer le rôle Transporteur sans passer par une vérification CNI renforcée.

## 4. Fiches de cas d'utilisation détaillées

### UC-03 — Initier une demande d'expédition
- **Acteur principal :** Client
- **Acteurs secondaires :** Système IA
- **Précondition :** Client authentifié.
- **Scénario nominal :**
  1. Le client renseigne origine, destination, date souhaitée.
  2. Le client filme l'article et rédige une description.
  3. Le système soumet la vidéo + description au contrôle IA (UC-IA-01).
  4. Le contrôle IA retourne "validé" sous 30 secondes.
  5. La demande est publiée et devient éligible au matching.
- **Extension (E1) — Rejet IA :**
  4a. Le contrôle IA retourne "rejeté".
  4b. La demande n'est pas émise ; le client est informé du motif.
  4c. Le client peut relancer UC-03 depuis le début, ou déclencher UC-14.

### UC-IA-01 — Exécuter le contrôle IA
- **Acteur principal :** Système IA (déclenché par UC-03)
- **Scénario nominal :**
  1. Détection d'objets/substances interdits sur la vidéo (Vision API).
  2. Vérification de cohérence entre description et contenu visuel (Groq).
  3. Détection d'indices d'altération de l'objet.
  4. Verdict global calculé (validé/rejeté) et motif associé.
- **Contrainte :** délai total ≤ 30 secondes (BNF-04).

### UC-05 / UC-19 — Sélection et acceptation (réservation)
- **Acteurs principaux :** Client (UC-05), Transporteur (UC-19)
- **Précondition :** Demande validée par l'IA et matching effectué.
- **Scénario nominal :**
  1. Le client consulte la liste classée de transporteurs (UC-04).
  2. Le client sélectionne un transporteur (UC-05).
  3. Le transporteur reçoit la demande dans sa liste de demandes compatibles (UC-18).
  4. Le transporteur accepte (UC-19).
  5. La réservation est confirmée pour les deux parties.
- **Extension (E1) — Refus/non-réponse transporteur :** la demande reste visible pour d'autres transporteurs de la liste ; le client peut sélectionner une autre proposition.

### UC-13 — Annuler une réservation
- **Acteur principal :** Client
- **Précondition :** Réservation confirmée (UC-05/UC-19), course non encore livrée.
- **Scénario nominal :**
  1. Le client annule la réservation.
  2. Si un paiement escrow existait, il est intégralement débloqué/remboursé (RM-02).
  3. Le transporteur est notifié de l'annulation.
- **Postcondition :** aucune pénalité pour le client (comportement volontaire actuel du système).

### UC-14 / UC-27 — Contestation d'un rejet IA
- **Acteur principal :** Client (UC-14), Administrateur (UC-27)
- **Précondition :** La demande du client a été rejetée par le contrôle IA.
- **Scénario nominal :**
  1. Le client soumet la demande rejetée à une revue manuelle.
  2. L'admin consulte la vidéo, la description, et le motif de rejet IA.
  3. L'admin confirme le rejet (fin) ou l'infirme, auquel cas la demande est publiée manuellement et devient éligible au matching (retour vers l'état "validé" de UC-03).

### UC-15 / UC-26 — Déclaration et traitement d'un litige
- **Acteur principal :** Client ou Transporteur (UC-15), Administrateur (UC-26)
- **Précondition :** Une course existe (en cours ou terminée).
- **Scénario nominal :**
  1. L'utilisateur déclare un litige lié à une course, motif libre (colis endommagé, refus de paiement, etc.).
  2. L'admin consulte l'ensemble des éléments disponibles sur la course (statuts, incidents signalés, historique paiement).
  3. L'admin arbitre : validation en faveur d'une partie, remboursement, ou autre décision.
- **Postcondition :** le statut de la course et/ou de l'escrow est mis à jour en conséquence.

## 5. Notes de couverture

Ce fichier couvre les cas d'utilisation principaux identifiés dans `04-besoins-fonctionnels.md`. Les cas plus secondaires (modification de mot de passe, modification de photo de profil, etc.) ne sont pas détaillés en fiche complète ici car ils suivent un schéma CRUD standard sans règle métier spécifique — ils restent listés en section 2 pour la complétude du diagramme.
