# 03 — Acteurs et Parties Prenantes

## 1. Vue d'ensemble

OnDuty distingue trois types d'acteurs : **Visiteur**, **Utilisateur authentifié** (avec deux rôles cumulables : Client et Transporteur), et **Administrateur**. Un même utilisateur authentifié peut détenir simultanément le rôle Client et le rôle Transporteur — il n'y a pas de bascule exclusive entre les deux : un utilisateur peut, au même moment, avoir une demande d'expédition en cours en tant que Client et un trajet publié en tant que Transporteur.

## 2. Visiteur

**Définition :** toute personne non authentifiée consultant l'application.

**Actions possibles :**
- Consulter la page de branding (présentation de l'application en trois étapes, scrollable).
- Créer un compte.

**Notes :** le visiteur n'a accès à aucune fonctionnalité métier (pas de consultation de trajets, de demandes, etc.) avant inscription/authentification.

## 3. Utilisateur authentifié

Tout compte créé sur OnDuty est, par défaut, un compte **Client**. Le rôle **Transporteur** s'active en complément via l'action "devenir transporteur" (déclenchant les vérifications spécifiques : informations véhicule, KYC renforcé). Une fois activé, le rôle Transporteur reste actif en permanence aux côtés du rôle Client — l'utilisateur navigue entre les deux espaces fonctionnels de la même application, avec un seul compte, un seul profil, une seule identité vérifiée.

### 3.1 Rôle Client (expéditeur ou destinataire)

**Définition :** utilisateur souhaitant faire expédier un colis/marchandise (expéditeur) ou en réceptionner un (destinataire). Le même compte peut jouer l'un ou l'autre rôle selon le sens de la transaction — ce n'est pas un rôle système distinct, mais une position contextuelle sur une course donnée.

**Responsabilités et actions :**
- **Gérer une demande** : initier une demande d'expédition (avec contrôle/validation IA obligatoire), consulter la liste des propositions issues du matching intelligent.
- **Gérer les paiements** : consulter l'historique, payer la course (déclenchant le blocage escrow).
- **Suivre la progression** : suivre le colis en temps réel, confirmer la réception (déclenchant la libération de l'escrow).
- **Gérer son profil** : modifier mot de passe, consulter profil, modifier photo de profil, vérifier sa CNI, activer le rôle transporteur.
- **Gérer une réservation** : une fois qu'il a sélectionné un trajet issu du matching et que le transporteur a accepté, il peut annuler la réservation (selon les règles d'annulation à définir dans `06-fonctionnalites-detaillees.md`).

### 3.2 Rôle Transporteur

**Définition :** utilisateur, particulier (aucune restriction professionnelle — ouvert à tout particulier disposant d'un véhicule : camion, pick-up, voiture), disposant d'un véhicule et proposant sa capacité de transport disponible sur un trajet donné. Un compte Transporteur correspond à une personne physique unique associée à un seul véhicule déclaré à la fois (pas de gestion de flotte multi-véhicules/multi-chauffeurs dans le périmètre actuel).

**Responsabilités et actions :**
- **Gérer ses trajets** : ajouter un nouveau trajet, supprimer un trajet.
- **Sélectionner une demande** : parmi les demandes issues du matching sur son trajet, choisir celle(s) qu'il accepte de transporter.
- **Gérer une course / suivre l'état de progression** : signaler un incident, mettre à jour le statut (départ, arrivé à destination, livré).
- **Gérer ses paiements** : consulter l'historique avec distinction des statuts (en attente — fonds en escrow / payé — course déjà réglée).
- **Gérer son profil** : mêmes fonctions que le Client, avec en plus les informations sur son véhicule et une vérification renforcée (documents véhicule, CNI).

## 4. Administrateur

**Définition :** unique niveau d'administration sur la plateforme — pas de hiérarchie de rôles admin (pas de modérateur séparé du super-admin) dans le périmètre actuel.

**Responsabilités et actions :**
- **Gérer les comptes utilisateurs** : validation, suspension, consultation des profils.
- **Visualiser le tableau de bord** : vue d'ensemble de l'activité de la plateforme (courses en cours, volumes, incidents, alertes IA, etc. — à détailler dans `06-fonctionnalites-detaillees.md`).
- **Gérer les litiges** : arbitrage entre client et transporteur en cas de désaccord (colis non conforme, non-livraison, contestation de l'escrow, etc.).

## 5. Synthèse des rôles

| Acteur | Authentification requise | Rôles cumulables | Vérification d'identité |
|---|---|---|---|
| Visiteur | Non | — | Aucune |
| Client | Oui | Peut aussi être Transporteur | CNI (facultative au départ, requise pour certaines actions sensibles) |
| Transporteur | Oui | Est toujours aussi Client | CNI + informations véhicule (obligatoire) |
| Admin | Oui (compte dédié) | Rôle unique, non cumulé avec Client/Transporteur | Interne (hors périmètre KYC public) |

## 6. Point à trancher plus tard

La question de savoir si le compte Admin doit lui-même être un compte "utilisateur" classique promu, ou un compte totalement séparé au niveau du modèle de données, sera précisée dans `10-diagramme-classes.md` — pour l'instant on retient qu'il n'y a qu'un seul admin fonctionnel, ce qui simplifie ce choix (pas besoin d'un système de rôles/permissions granulaire côté admin).
