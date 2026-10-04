# AGENTS.md — Projet OnDuty

Ce fichier guide tout agent IA (Claude Code ou équivalent) travaillant sur ce dépôt. Il indique **quoi faire**, **comment travailler**, et **quels fichiers de `docs/` consulter selon la tâche en cours**. Toute décision de conception non couverte ici doit se référer à `docs/`, jamais être inventée.

## 1. Présentation du projet

OnDuty est une application mobile (Flutter + Django/DRF + PostgreSQL) mettant en relation des expéditeurs de colis/marchandises avec des transporteurs disposant d'une capacité de transport disponible, sur tout le territoire camerounais. Fonctionnalités clés : matching intelligent, contrôle IA des colis ("douane numérique"), paiement mobile sécurisé par escrow, vérification d'identité (KYC).

La documentation complète du projet se trouve dans `docs/` (14 fichiers, `01-introduction-contexte.md` à `14-securite-conformite.md`). **Ne jamais modifier ces fichiers** sans validation explicite de l'utilisateur — ce sont des documents de référence, pas des artefacts de travail.

> **Phase actuelle du projet : BACKEND.** Le développement démarre par le backend Django/DRF (modèle de données, logique métier, endpoints), avant tout travail sur les écrans Flutter. Le frontend ne démarre qu'une fois le backend suffisamment avancé, idéalement après validation d'une maquette (Figma ou équivalent) — voir section 5.

## 2. Carte de navigation documentaire

Avant d'implémenter une tâche, consulter le(s) fichier(s) pertinent(s) selon la nature du travail :

| Type de tâche | Fichier(s) à consulter en priorité |
|---|---|
| Comprendre le contexte général, la vision du produit | `01-introduction-contexte.md`, `02-objectifs.md` |
| Comprendre un acteur (client/transporteur/admin) et ses droits | `03-acteurs-parties-prenantes.md` |
| Implémenter une règle métier précise (annulation, statuts, permissions) | `04-besoins-fonctionnels.md` |
| Respecter une contrainte de performance/disponibilité | `05-besoins-non-fonctionnels.md` |
| Comprendre le détail fonctionnel d'un écran ou d'un flux | `06-fonctionnalites-detaillees.md` |
| Comprendre les cas d'usage et leurs variantes | `07-diagramme-cas-utilisation.md` |
| Comprendre l'enchaînement exact des interactions (ordre des appels) | `08-diagrammes-sequence.md` |
| Comprendre un processus avec embranchements/décisions | `09-diagrammes-activite.md` |
| Créer ou modifier un modèle de données (Django ou classes Dart) | `10-diagramme-classes.md` |
| Comprendre comment les composants communiquent (sync/async) | `11-diagramme-communication.md` |
| Implémenter le contrôle IA (upload vidéo, vérification, KYC) | `12-pipeline-ia-verification.md` |
| Choisir une techno, une lib, une structure de dossier | `13-architecture-technique.md` |
| Implémenter authentification, chiffrement, gestion des accès | `14-securite-conformite.md` |

**Règle générale :** en cas de doute entre deux fichiers, privilégier celui qui décrit le comportement observable (fonctionnel) plutôt que la structure technique — le comportement attendu prime sur l'implémentation.

## 3. Conventions de code (Flutter)

- **Fichiers :** `snake_case` (ex. `create_shipment_screen.dart`)
- **Classes/Widgets :** `PascalCase` (ex. `CreateShipmentScreen`)
- **Variables/fonctions :** `camelCase` (ex. `selectedTransporter`)
- **Structure de dossiers** (cf. `13-architecture-technique.md`, section 4) :
  ```
  lib/
    screens/
      onboarding/
      auth/
      client/
      transporter/
      shared/
    services/
    models/
    theme/
    localization/
    widgets/        (composants réutilisables)
  ```
- Un écran = un fichier dans `screens/<domaine>/`. Les widgets réutilisables (boutons custom, cartes, etc.) vont dans `widgets/`, jamais dupliqués entre écrans.

## 4. Design system

### 4.1 Palette de couleurs

Palette de base : **marron / blanc / noir**, déclinée en thème clair et sombre.

| Rôle | Thème clair | Thème sombre |
|---|---|---|
| Fond principal (background) | `#FFFFFF` | `#121212` |
| Surface (cartes, champs) | `#F5F0EC` | `#2B211D` |
| Couleur primaire (marron) | `#6F4E37` | `#A97155` |
| Couleur d'accent (marron clair) | `#A97155` | `#8B5E3C` |
| Texte principal | `#1A1A1A` | `#F5F5F5` |
| Texte secondaire | `#5C5C5C` | `#BFBFBF` |

Ces valeurs sont une proposition de départ — ajustables si le rendu visuel ne convient pas une fois testé sur un premier écran. Implémenter via `ThemeData` (light/dark) dans `lib/theme/`, avec bascule accessible depuis le profil utilisateur.

### 4.2 Langue

- Langue par défaut au premier lancement : **Français**.
- Langue secondaire disponible : **Anglais**, sélectionnable dans le profil.
- Implémentation via `flutter_localizations` + fichiers `.arb` (`lib/localization/app_fr.arb`, `app_en.arb`). Ne jamais coder de texte en dur dans un widget — toujours passer par les clés de traduction, même pour les premiers écrans, pour éviter un refactoring de masse plus tard.

## 5. Architecture de navigation frontend (proposition provisoire — à valider après maquette)

**Statut : provisoire.** Cette structure sert de repère pour ne pas partir dans tous les sens, mais elle doit idéalement être validée/ajustée après conception d'une maquette (Figma ou équivalent) avant implémentation réelle. Ne pas considérer cette liste comme figée.

### 5.1 Navigation principale (onglets)

Un compte pouvant cumuler les rôles Client et Transporteur (cf. `03-acteurs-parties-prenantes.md`), la navigation principale reste **unique**, pas de bascule entre deux jeux d'onglets séparés :

1. **Accueil** — vue d'ensemble : demande(s) en cours (client), trajet(s) actif(s) si rôle transporteur activé, accès rapide aux actions principales ("Expédier un colis", "Publier un trajet").
2. **Activité** — historique et suivi de toutes les courses, avec un filtre interne "En tant que client" / "En tant que transporteur".
3. **Trajets** — visible uniquement si le rôle Transporteur est activé ; gestion des trajets publiés.
4. **Profil** — profil, vérification CNI, activation du rôle transporteur, paramètres (langue, thème).

### 5.2 Écrans/flux secondaires (atteints via une action, pas des onglets)

Ces écrans sont déclenchés par un bouton ou une étape de parcours, pas accessibles directement depuis la navigation principale :

- Splash / Branding (3 étapes scrollables) — avant connexion
- Inscription / Connexion
- Nouvelle demande d'expédition (formulaire + capture vidéo) — depuis Accueil
- Résultat du contrôle IA (validé / rejeté + option "contester") — étape du flux de demande
- Liste des propositions de matching — étape suivante du flux de demande
- Détail d'une course (statuts, suivi en temps réel, paiement, confirmation réception) — depuis Activité ou une notification
- Paiement d'une course — étape du flux de réservation
- Ajouter un trajet — depuis l'onglet Trajets
- Demandes compatibles avec un trajet publié — depuis un trajet dans l'onglet Trajets
- Vérification CNI (KYC) — depuis Profil
- Devenir transporteur (formulaire véhicule) — depuis Profil
- Déclarer un litige — depuis le détail d'une course

**Hors périmètre Flutter :** le tableau de bord admin et la gestion des litiges/comptes côté admin sont une interface **web** (Django Admin personnalisé), pas un écran Flutter — cf. `13-architecture-technique.md`, section 4.

## 6. Méthode de travail avec l'agent

**Règle non négociable : un module/écran à la fois, avec arrêt et validation systématiques.**

### Phase 1 — Backend (phase actuelle)

Ordre d'implémentation suggéré, app par app (cf. `13-architecture-technique.md`, section 3) :

1. `accounts` (utilisateurs, rôles, authentification JWT)
2. `vehicles` (informations véhicule transporteur)
3. `verification` (entité KYC/CNI)
4. `trips` (trajets transporteurs)
5. `requests` (demandes d'expédition + intégration pipeline IA)
6. `matching` (moteur de scoring)
7. `bookings` (entité Course, cycle de vie)
8. `payments` (escrow, intégration mobile money)
9. `disputes` (incidents, litiges)
10. `ratings` (évaluations, score de fiabilité)
11. `notifications` (Firebase Cloud Messaging)

Pour chaque app, l'agent implémente dans cet ordre : modèles → migrations → serializers → vues/permissions → routes. Une fois une app complète et testable (via Browsable API ou Postman), l'agent **s'arrête** et fournit :
- Le code produit.
- Un résumé court expliquant les choix faits (structure des modèles, permissions appliquées, points de vigilance).
- Des exemples de requêtes pour tester manuellement l'app (ex. commande `curl` ou capture Postman).

L'agent **attend une validation explicite** avant de passer à l'app suivante.

### Phase 2 — Frontend (démarre après un backend suffisamment avancé, idéalement après maquette)

Une fois cette phase démarrée, même règle : **un écran à la fois** parmi ceux listés en section 5, avec arrêt et résumé après chaque écran, avant de passer au suivant.

**Objectif pédagogique explicite (valable pour les deux phases) :** l'utilisateur doit être capable de comprendre et d'expliquer chaque ligne de code produite (préparation à une soutenance académique). L'agent doit donc privilégier la clarté et la lisibilité du code à la concision ou aux optimisations avancées, sauf demande contraire.

## 7. Ce que l'agent ne doit PAS faire

- Ne pas modifier les fichiers de `docs/`.
- Ne pas implémenter plusieurs apps backend (ou plusieurs écrans en phase frontend) d'un coup sans validation intermédiaire.
- Ne pas introduire de nouvelle dépendance/librairie non mentionnée dans `13-architecture-technique.md` sans le signaler explicitement et demander confirmation.
- Ne pas commencer le frontend tant que la Phase 1 (backend) n'est pas explicitement déclarée suffisamment avancée par l'utilisateur.
- Une fois en Phase 2, ne pas coder de texte en dur dans les écrans Flutter (toujours passer par les clés de traduction `.arb`).
- Ne pas inventer de règle métier non documentée : en cas de zone grise, poser la question à l'utilisateur plutôt que de supposer.
