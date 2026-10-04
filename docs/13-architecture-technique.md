# 13 — Architecture Technique

## 1. Vue d'ensemble de la stack

| Couche | Technologie | Version cible |
|---|---|---|
| Mobile (client) | Flutter | 3.44.x (stable) |
| Langage mobile | Dart | 3.10.x |
| Backend | Django + Django REST Framework | Django 5.2 LTS |
| Langage backend | Python | 3.12 |
| Base de données | PostgreSQL | 16.x |
| Traitement asynchrone | Celery + Redis (contrôle IA synchrone dans la version actuelle, cf. fichier 11 §2.3) | Dernières versions stables au moment de l'implémentation |
| Stockage médias (vidéos de contrôle, photos profil) | Cloudinary | — |
| Notifications push | Firebase Cloud Messaging | — |
| Détection objets interdits | Groq par défaut ; Google Cloud Vision en complément (`IA_DETECTION=google`) | — |
| Vérification cohérence | Groq (modèle vision-langage, API compatible OpenAI) | — |
| KYC/CNI | Smile Identity | — |
| Paiement mobile | CamPay (agrégateur MTN MoMo et Orange Money) | — |

**Justification des choix de version :** Django 5.2 est la version LTS actuelle (support sécurité jusqu'à fin 2028), un choix plus sûr qu'une version "standard" à cycle de support court (16 mois) pour un projet dont l'entretien pourrait se prolonger après la soutenance. Flutter 3.44 est la dernière branche stable au moment de la rédaction — cohérente avec les versions déjà utilisées sur tes projets précédents (My Week était en 3.41.x). PostgreSQL 16 est une version stable largement supportée par les hébergeurs cloud visés ci-dessous.

## 2. Architecture applicative (vue logique)

```
[App Flutter] 
      │  HTTPS / REST (DRF)
      ▼
[Backend Django/DRF] ── ORM ──> [PostgreSQL]
      │
      ├──> [File d'attente Celery/Redis] ──> [Google Cloud Vision]
      │                                  ──> [Groq]
      │                                  ──> [Smile Identity]
      │
      ├──> [API MTN MoMo / Orange Money]
      │
      └──> [Firebase Cloud Messaging] ──> [App Flutter] (notifications push)
```

Cette architecture respecte le découpage synchrone/asynchrone détaillé dans `11-diagramme-communication.md`, et l'approche "squelette complet dès le départ" définie dans `02-objectifs.md` : chaque app Django (utilisateurs, trajets, demandes, matching, paiements, litiges) est créée dès le début du projet, même si son contenu métier est implémenté progressivement.

## 3. Organisation du backend (apps Django proposées)

- `accounts` : gestion des utilisateurs, profils, rôles (client/transporteur), authentification.
- `vehicles` : informations véhicule des transporteurs.
- `verification` : entité `Verification` (KYC/CNI), intégration Smile Identity.
- `trips` : gestion des trajets transporteurs.
- `requests` : gestion des demandes d'expédition, intégration du pipeline IA (`12-pipeline-ia-verification.md`).
- `matching` : moteur de scoring et de mise en relation.
- `bookings` : entité `Course` (fusion réservation/suivi), statuts, cycle de vie.
- `payments` : gestion des paiements et de l'escrow, intégration MTN MoMo / Orange Money.
- `disputes` : gestion des litiges et incidents.
- `ratings` : évaluations et calcul du score de fiabilité.
- `notifications` : intégration Firebase Cloud Messaging, envoi centralisé des notifications.
- `administration` : tableau de bord et outils admin (peut s'appuyer largement sur Django Admin personnalisé plutôt qu'une interface entièrement custom, pour gagner du temps de développement).

## 4. Organisation du frontend Flutter (structure proposée)

Suivant la logique de squelette complet, l'arborescence Flutter prévoit dès le départ les modules suivants (même vides ou partiellement implémentés) :
- `screens/onboarding` (branding page)
- `screens/auth` (inscription, connexion)
- `screens/client` (demandes, matching, paiements, suivi)
- `screens/transporter` (trajets, courses, paiements)
- `screens/shared` (profil, vérification CNI, litiges)
- `services/` (appels API, gestion des notifications, gestion de l'état)
- `models/` (structures de données correspondant aux entités du fichier 10)


## 5. Solution d'hébergement et déploiement (proposition pour la soutenance)

| Composant | Solution proposée | Justification |
|---|---|---|
| Backend Django/DRF | **Render** (ou Railway en alternative) | Déploiement simple depuis Git, offre gratuite/à faible coût suffisante pour une démo, support PostgreSQL managé natif |
| Base de données PostgreSQL | Instance PostgreSQL managée fournie par Render/Railway | Évite la gestion d'un serveur DB séparé |
| Redis (file d'attente Celery) | Add-on Redis Render/Railway, ou Upstash (offre gratuite) | Cohérent avec l'hébergement backend |
| Application mobile | Build **APK Android** distribué directement (lien de téléchargement ou transfert direct) pour la soutenance | Pas besoin de publication sur le Play Store pour une démo académique — plus rapide et sans délai de validation |
| Stockage vidéos/photos | Cloudinary (offre gratuite) | Cohérent avec ton usage déjà établi sur OnMyCamp |
| Nom de domaine backend | Sous-domaine gratuit fourni par Render (ex. `onduty-api.onrender.com`) | Suffisant pour une démo, pas de coût de domaine à engager dans les délais |

**Point de vigilance pour la démo :** les hébergeurs gratuits (Render notamment) mettent en veille les services inactifs, ce qui peut provoquer un temps de démarrage ("cold start") de plusieurs secondes lors de la première requête après une période d'inactivité. Pour la soutenance, il est recommandé de faire une requête de "réveil" du backend quelques minutes avant la démonstration, ou de passer sur une offre payante à faible coût le jour J pour éviter tout aléa.

## 6. Environnement de développement

- **Backend :** Python 3.12, environnement virtuel (`venv`), Django 5.2 LTS, DRF (dernière version stable compatible), Celery + Redis en local via Docker (optionnel mais recommandé pour reproduire fidèlement l'environnement de prod).
- **Frontend :** Flutter 3.44.x, Dart 3.10.x, Android Studio ou VS Code avec extensions Flutter/Dart.
- **Gestion de versions :** Git, avec une convention de branches à définir (ex. `main`, `develop`, une branche par module backend listé en section 3).

## 7. Points de vigilance techniques transverses

- **Isolation des intégrations tierces** (BNF-16, fichier 05) : chaque appel à une API externe (Vision API, Groq, Smile Identity, MTN MoMo, Orange Money) doit passer par une interface interne dédiée dans le backend, pour permettre un remplacement par une alternative sans casser le reste du système.
- **Traitement asynchrone dès le départ** : Celery + Redis doivent être opérationnels dès les premiers modules développés (contrôle IA), pas ajoutés en fin de projet — c'est une dépendance structurante, pas un détail d'optimisation tardive.
- **Gestion du réseau dégradé** (BNF-07) : prévoir un cache local léger côté Flutter (ex. `shared_preferences` ou `hive` pour les données non sensibles) pour absorber les coupures réseau fréquentes hors des grandes villes.
