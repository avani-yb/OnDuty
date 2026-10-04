# 04 — Besoins Fonctionnels

Ce document liste les besoins fonctionnels par acteur, avec les règles métier associées. Chaque besoin est identifié par un code (`BF-XX`) réutilisable dans les diagrammes UML (fichiers 07 à 11).

## 1. Visiteur

| Code | Besoin |
|---|---|
| BF-01 | Le système doit permettre à un visiteur de consulter une page de branding présentant l'application en trois étapes scrollables. |
| BF-02 | Le système doit permettre à un visiteur de créer un compte (email/téléphone + mot de passe, ou équivalent). |

## 2. Client (rôle expéditeur / destinataire)

### 2.1 Gestion de demande d'expédition

| Code | Besoin |
|---|---|
| BF-03 | Le système doit permettre à un client d'initier une demande d'expédition en filmant l'article à expédier et en fournissant une description. |
| BF-04 | Le système doit soumettre systématiquement chaque nouvelle demande au module de contrôle IA avant toute publication ou mise en matching. |
| BF-05 | Si le contrôle IA valide la demande, celle-ci devient éligible au matching intelligent. |
| BF-06 | Si le contrôle IA rejette la demande (objet interdit, incohérence description/image, altération suspecte), la demande n'est **pas émise** : elle n'est ni publiée, ni transmise au matching. |
| BF-07 | En cas de rejet par l'IA, le client peut reprendre le processus depuis le début (nouvelle vidéo, nouvelle description) autant de fois que nécessaire. |
| BF-08 | En cas de rejet qu'il estime injustifié, le client peut soumettre la demande rejetée à une **revue manuelle par l'administrateur**, qui peut confirmer ou infirmer la décision de l'IA. |
| BF-09 | Le système doit conserver une trace de chaque tentative de validation (acceptée, rejetée, rejetée puis contestée) à des fins d'audit et de litige. |

### 2.2 Matching et sélection

| Code | Besoin |
|---|---|
| BF-10 | Le système doit présenter au client une **liste de transporteurs proposés**, classés du plus optimal au moins optimal selon les critères de matching (voir `12-pipeline-ia-verification.md` / `06-fonctionnalites-detaillees.md` pour les critères). |
| BF-11 | Tout transporteur figurant dans la liste doit garantir qu'il effectue le trajet demandé dans les prochains jours (fenêtre de validité du trajet publié). |
| BF-12 | Le client peut sélectionner un transporteur dans la liste pour initier une réservation. |

### 2.3 Paiement

| Code | Besoin |
|---|---|
| BF-13 | Le système doit permettre au client de consulter l'historique de ses paiements. |
| BF-14 | Le système doit permettre au client de payer une course via mobile money (MTN MoMo / Orange Money). |
| BF-15 | Le paiement effectué par le client est placé en **escrow** (statut "en attente") jusqu'à confirmation de livraison. |

### 2.4 Suivi

| Code | Besoin |
|---|---|
| BF-16 | Le système doit permettre au client de suivre la progression de son colis en temps réel. |
| BF-17 | Le système doit permettre au client de confirmer la réception du colis, ce qui déclenche la libération des fonds escrow vers le transporteur. |

### 2.5 Profil

| Code | Besoin |
|---|---|
| BF-18 | Le système doit permettre au client de modifier son mot de passe. |
| BF-19 | Le système doit permettre au client de consulter son profil. |
| BF-20 | Le système doit permettre au client de modifier sa photo de profil. |
| BF-21 | Le système doit permettre au client de vérifier sa CNI (KYC). |
| BF-22 | Le système doit permettre à un client d'activer le rôle Transporteur sur son compte existant. |

### 2.6 Réservation

| Code | Besoin |
|---|---|
| BF-23 | Le système doit permettre au client d'annuler une réservation, **sans condition ni pénalité** dans la version actuelle du projet. |
| BF-24 | Une annulation doit entraîner le remboursement automatique du **prix de la course** au client ; la commission OnDuty et les frais de paiement ne sont pas remboursés (décision du 04/10/2026). |

## 3. Transporteur

### 3.1 Gestion des trajets

| Code | Besoin |
|---|---|
| BF-25 | Le système doit permettre au transporteur d'ajouter un nouveau trajet (départ, arrivée, date, capacité disponible). |
| BF-26 | Le système doit permettre au transporteur de supprimer un trajet existant. |
| BF-27 | Le système doit permettre au transporteur de consulter les demandes issues du matching correspondant à son trajet, et d'en choisir une (ou plusieurs, selon capacité restante). |

### 3.2 Gestion de course

| Code | Besoin |
|---|---|
| BF-28 | Le système doit permettre au transporteur de signaler un incident sur une course en cours. |
| BF-29 | Le système doit permettre au transporteur de mettre à jour le statut de la course : départ, arrivé à destination, livré. |

### 3.3 Paiement

| Code | Besoin |
|---|---|
| BF-30 | Le système doit permettre au transporteur de consulter l'historique de ses paiements, avec distinction claire des statuts : **en attente** (escrow bloqué, course non finalisée) et **payé** (course finalisée, fonds libérés). |

### 3.4 Profil

| Code | Besoin |
|---|---|
| BF-31 | Le système doit permettre au transporteur les mêmes actions de profil que le client (BF-18 à BF-21), avec en complément la gestion des informations de son véhicule et une vérification renforcée. |

## 4. Administrateur

| Code | Besoin |
|---|---|
| BF-32 | Le système doit permettre à l'admin de gérer les comptes utilisateurs (consultation, suspension, validation). |
| BF-33 | Le système doit permettre à l'admin de visualiser un tableau de bord d'activité de la plateforme. |
| BF-34 | Le système doit permettre à l'admin de traiter les litiges entre clients et transporteurs. |
| BF-35 | Le système doit permettre à l'admin de traiter les demandes de revue manuelle soumises par un client suite à un rejet IA (BF-08), avec possibilité de valider ou confirmer le rejet. |

## 5. Règles métier transverses

- **RM-01 — Rejet IA non contournable automatiquement** : aucune demande rejetée par l'IA ne peut être mise en matching sans validation explicite de l'admin suite à une contestation.
- **RM-02 — Annulation libre** : dans la version actuelle, l'annulation d'une réservation par le client n'entraîne aucune pénalité ; le prix de la course lui est remboursé, la commission OnDuty et les frais de paiement restant acquis (décision du 04/10/2026). Ce point est identifié comme évolution possible (ex. pénalité en cas d'annulations répétées) mais **hors périmètre actuel**.
- **RM-03 — Classement du matching** : la liste de transporteurs proposée au client est ordonnée par pertinence décroissante ; l'appartenance à la liste garantit que le trajet a lieu dans un horizon proche (à définir précisément en jours dans `06-fonctionnalites-detaillees.md`).
- **RM-04 — Double rôle** : les besoins fonctionnels Client et Transporteur peuvent coexister sur un même compte sans restriction (cf. `03-acteurs-parties-prenantes.md`).
