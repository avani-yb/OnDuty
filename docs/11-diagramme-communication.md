# 11 — Diagramme de Communication

## 1. Composants du système

- **App Flutter** (client mobile, utilisée par Client et Transporteur)
- **Backend Django/DRF** (cœur applicatif)
- **Base de données PostgreSQL**
- **File d'attente asynchrone** (Celery + Redis, ou équivalent — traitement des tâches longues/coûteuses)
- **Vision API** (Google Cloud Vision / Amazon Rekognition — détection d'objets interdits)
- **Groq** (vérification de cohérence description/image)
- **Smile Identity** (KYC/CNI)
- **API MTN MoMo** / **API Orange Money** (paiement mobile)
- **Service de notifications push** (Firebase Cloud Messaging)

## 2. Flux de communication

### 2.1 App Flutter ↔ Backend
- **Nature :** synchrone (requêtes HTTP REST via DRF)
- **Contenu :** authentification, CRUD profil/trajet/demande, consultation matching, paiement, statuts de course.
- **Fréquence :** à la demande de l'utilisateur (actions manuelles) + polling ou souscription pour le suivi temps réel (voir 2.8).

### 2.2 Backend ↔ Base de données
- **Nature :** synchrone (ORM Django)
- **Contenu :** toutes les opérations de lecture/écriture sur les entités du fichier 10.

### 2.3 Backend ↔ File d'attente asynchrone (contrôle IA)
- **Nature :** **asynchrone**
> **Décision d'implémentation (03/10/2026) :** dans la version actuelle, le contrôle IA s'exécute **pendant la requête HTTP** (synchrone), dans un budget de 30 s (`IA_BUDGET_SECONDES`) avec des timeouts stricts par fournisseur. En cas de panne d'un service tiers, le client reçoit une erreur **503** avec un message explicite, la demande reste `en_cours_controle` et peut être relancée (`POST /api/demandes/{id}/relancer/`). Le passage à Celery décrit ci-dessous reste l'évolution prévue si la charge l'exige (BNF-09).

- **Justification (cible) :** le contrôle IA enchaîne deux appels externes successifs (Vision API puis Groq), avec une contrainte de délai de 30 secondes (BNF-04). Pour absorber une charge simultanée sans dégrader ce délai (BNF-09), le traitement est délégué à une tâche de file d'attente (Celery + Redis) dès la soumission de la demande, plutôt que traité en ligne dans la requête HTTP.
- **Déroulé :**
  1. Backend reçoit la demande → crée un enregistrement `Demande` en statut `en_cours_controle`.
  2. Backend publie une tâche dans la file d'attente.
  3. Le worker asynchrone appelle Vision API puis Groq séquentiellement.
  4. Le worker met à jour le statut de la `Demande`/`ControleIA` en base.
  5. Le backend notifie le client via push (voir 2.8) une fois le verdict disponible — l'app Flutter n'attend pas la réponse en direct sur la requête initiale, elle est notifiée en asynchrone.

### 2.4 Backend/Worker ↔ Vision API
- **Nature :** synchrone (appel API externe, mais initié depuis un contexte asynchrone — cf. 2.3)
- **Contenu :** envoi de la vidéo/frames extraites → réception de la liste d'objets détectés.

### 2.5 Backend/Worker ↔ Groq
- **Nature :** synchrone (appel API externe, initié depuis le worker)
- **Contenu :** envoi de la description + frames/vidéo → réception du verdict de cohérence et des détails sur l'objet.

### 2.6 Backend ↔ Smile Identity
- **Nature :** **asynchrone** (recommandé) — la vérification KYC n'a pas la contrainte de délai serrée du contrôle IA (30 secondes), un traitement en file d'attente avec notification différée est acceptable et plus robuste.
- **Contenu :** envoi des documents CNI → réception du résultat de vérification (validé/rejeté/à revoir).

### 2.7 Backend ↔ API MTN MoMo / API Orange Money
- **Nature :** synchrone pour l'initiation (le client doit voir une confirmation immédiate de la demande de paiement), **asynchrone pour la confirmation finale** (les providers mobile money confirment généralement via callback/webhook après validation côté opérateur, pas instantanément).
- **Déroulé :**
  1. App Flutter → Backend : demande de paiement.
  2. Backend → API Mobile Money : initie la transaction (synchrone, réponse immédiate = "transaction initiée").
  3. Client confirme sur son téléphone (USSD/notification opérateur, hors système OnDuty).
  4. API Mobile Money → Backend : callback de confirmation (asynchrone).
  5. Backend : crée/actualise l'enregistrement `Paiement` en base, statut "bloqué escrow".
  6. Backend → App Flutter : notifie la confirmation (push).

### 2.8 Backend ↔ Service de notifications push (FCM) ↔ App Flutter
- **Nature :** asynchrone
- **Contenu :** tous les événements différés doivent remonter par notification push plutôt que par attente active côté app : résultat du contrôle IA, résultat KYC, confirmation de paiement, mise à jour de statut de course (départ/arrivée/livré), résultat de litige/contestation.
- **Justification :** cohérent avec BNF-06 (mises à jour reflétées en temps quasi réel) et BNF-07 (tolérance aux réseaux dégradés — le push évite au client de devoir maintenir une connexion active en continu).

## 3. Synthèse — synchrone vs asynchrone

| Flux | Nature |
|---|---|
| App Flutter ↔ Backend (actions utilisateur classiques) | Synchrone |
| Backend ↔ Base de données | Synchrone |
| Backend → File d'attente → Vision API / Groq | **Asynchrone** (mise en file, traitement différé, notification en retour) |
| Backend → Smile Identity | **Asynchrone** (recommandé) |
| Backend → API Mobile Money (initiation) | Synchrone |
| API Mobile Money → Backend (confirmation) | **Asynchrone** (callback) |
| Backend → App Flutter (notifications d'événements) | **Asynchrone** (push FCM) |

## 4. Implication pour l'architecture

Ce découpage synchrone/asynchrone confirme la nécessité, dès le squelette backend (cf. `02-objectifs.md` — approche "squelette complet dès le départ"), de prévoir :
- Une intégration Celery + Redis (ou équivalent) opérationnelle dès les premiers modules, même si peu de tâches y transitent au début.
- Une intégration Firebase Cloud Messaging fonctionnelle tôt dans le développement, car elle conditionne l'expérience de plusieurs flux critiques (IA, paiement, suivi).

Ces points seront repris et détaillés techniquement dans `13-architecture-technique.md`.
