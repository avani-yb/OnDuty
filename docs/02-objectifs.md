# 02 — Objectifs

## 1. Objectif général

Faciliter et sécuriser l'expédition de colis et de marchandises sur tout le territoire camerounais en connectant expéditeurs et transporteurs via une plateforme intelligente.

## 2. Approche de réalisation

Le projet est conçu pour couvrir **l'intégralité du périmètre fonctionnel dès la conception de l'architecture** (backend et frontend), même si l'implémentation se fait ensuite module par module. Concrètement :

- L'arborescence backend (apps Django, modèles de données, endpoints DRF) est structurée dès le départ pour accueillir *toutes* les fonctionnalités décrites dans `06-fonctionnalites-detaillees.md`, y compris celles qui seront implémentées en dernier.
- Le frontend Flutter suit la même logique : les écrans et la navigation sont prévus pour l'ensemble du parcours utilisateur, avec des modules développés et branchés progressivement.
- Cette approche "squelette complet, implémentation incrémentale" évite les refactorings lourds en cours de projet et permet de démontrer une architecture cohérente même si certains modules sont encore partiellement fonctionnels au moment de la soutenance.

## 3. Objectifs spécifiques

### 3.1 Gestion des comptes et profils
- Permettre à tout visiteur de créer un compte (client par défaut, avec possibilité de devenir transporteur).
- Permettre la vérification d'identité (CNI) pour sécuriser les comptes, en particulier les transporteurs.
- Offrir une gestion de profil complète (mot de passe, photo, informations véhicule pour les transporteurs).

### 3.2 Gestion des demandes d'expédition
- Permettre à un client d'initier une demande d'expédition avec contrôle et validation automatique par IA avant publication.
- Garantir qu'aucune demande ne soit exposée au matching tant qu'elle n'a pas été validée par le module de contrôle IA.

### 3.3 Matching intelligent
- Mettre en relation automatiquement les demandes d'expédition avec les trajets disponibles déclarés par les transporteurs, sur la base de critères de pertinence (itinéraire, capacité, dates).
- Présenter au client une liste de propositions issues de ce matching, et au transporteur les demandes compatibles avec son trajet.

### 3.4 Paiement et escrow
- Sécuriser chaque transaction via un compte séquestre (escrow) : les fonds sont bloqués au moment de la réservation et libérés au transporteur uniquement après confirmation de livraison.
- Intégrer les deux principaux opérateurs de mobile money du pays (MTN MoMo, Orange Money) pour maximiser l'accessibilité, y compris en zones peu bancarisées.
- Fournir à chaque acteur un historique clair de ses paiements (statuts : en attente / payé).

### 3.5 Suivi et traçabilité
- Permettre un suivi en temps réel de la progression du colis, du dépôt à la livraison.
- Permettre au transporteur de signaler un incident et de mettre à jour le statut de la course à chaque étape clé (départ, arrivée à destination, livré).
- Permettre au client de confirmer la réception, déclenchant la libération de l'escrow.

### 3.6 Sécurité et confiance (priorité forte)
- Faire du contrôle IA à la création de la demande une étape non contournable, avec un niveau d'exigence élevé sur la fiabilité de la détection (objets/substances interdits, cohérence description/image, détection d'altération).
- Garantir l'intégrité du processus KYC pour toute personne souhaitant devenir transporteur.
- Donner à l'administrateur les outils nécessaires pour superviser, auditer et arbitrer les litiges.

### 3.7 Administration
- Fournir un tableau de bord permettant à l'admin de visualiser l'activité de la plateforme.
- Permettre la gestion des comptes utilisateurs (suspension, validation, etc.) et la résolution des litiges entre clients et transporteurs.

## 4. Niveau d'exigence

Le souhait explicite pour la soutenance est que **l'ensemble des fonctionnalités décrites soit opérationnel**, et non une simple démonstration partielle. Cet objectif est ambitieux compte tenu du délai, et sera piloté avec une priorisation stricte des modules (voir `06-fonctionnalites-detaillees.md` pour le détail par acteur et la logique de dépendance entre modules).
