# AGENT.md — Fonctionnalités majeures d'OnDuty (phase d'intégration)

Ce fichier **complète** `AGENTS.md` (règles générales de travail) : il décrit la prochaine étape du projet — remplacer les **simulations** actuelles par de vraies fonctionnalités. Lis d'abord `AGENTS.md`, puis ce fichier. En cas de contradiction, ce fichier prévaut pour les tâches listées ici.

> La mention « Phase actuelle : BACKEND » de `AGENTS.md` est **dépassée** : backend (11 apps Django) et application Flutter existent déjà et sont connectés. On travaille désormais sur les deux côtés, **une tâche à la fois**.

---

## 0. Règles de travail (rappel + ajouts)

1. **Une tâche (T1…T4) à la fois.** À la fin de chacune : arrête-toi, résume (choix faits, fichiers touchés, comment tester), attends la validation de l'utilisateur.
2. **Ne modifie jamais `docs/`** sans validation. Si une règle métier change, *propose* le texte à ajouter (ex. nouveaux BF) au lieu de l'écrire.
3. **Aucune clé/secret dans le code ni dans git.** Backend : variables d'environnement (`.env`, avec un `.env.example` sans valeurs réelles). Mobile : `--dart-define` ou placeholders de manifeste, jamais de clé en dur.
4. **Isole chaque API tierce derrière une interface interne** (BNF-16, `docs/05`) : un module `services/<fournisseur>.py` implémentant une interface commune, avec un mode « simulé » conservé pour les tests et le développement sans clé. Comportement dégradé défini si l'API est indisponible (BNF-10).
5. **Le code doit rester explicable ligne par ligne** : l'utilisateur le défendra devant un jury. Privilégie la clarté, commente le « pourquoi ».
6. **Ne casse pas l'existant.** Avant de rendre la main : `python manage.py check`, tests/scénarios backend, `flutter analyze` sans erreur.
7. **Zone grise = question** à l'utilisateur, pas d'invention de règle métier. Aucune nouvelle dépendance hors `docs/13-architecture-technique.md` sans la signaler et demander confirmation.
8. Textes de l'interface : le code actuel mélange clés `.arb` et chaînes françaises en dur. Pour les nouveaux écrans, suis la pratique de l'écran que tu modifies ; ne refactorise pas l'existant sans demande.

---

## 1. État actuel (à connaître avant de coder)

### Flux implémenté et testé de bout en bout
`Demande` (vidéo + **montant proposé**) → contrôle IA **simulé** → `matching` → le client choisit un trajet → `Course` (`reservee`, `montant_convenu` = montant proposé) → le transporteur **accepte** *ou* **propose un autre montant** (`proposition_montant`) → le client **valide** le nouveau montant → `en_attente_paiement` → **paiement** (escrow) → `payee` → `depart` → `en_route` → `arrivee` → le client confirme (`livree`, escrow libéré). Annulation client possible avant livraison (remboursement automatique, RM-02).

### Règle de paiement (décidée par l'utilisateur — ne pas changer)
> Le client paie **uniquement** quand le transporteur a accepté la course, **ou** quand il a modifié la somme puis que le client a validé cette nouvelle somme. Le montant payé est **toujours** `Course.montant_convenu`.

Le backend refuse déjà tout paiement hors statut `en_attente_paiement` (`paiement/views.py`).

### Ce qui est encore simulé (ta mission)
| Élément | Où | Simulation actuelle |
|---|---|---|
| Contrôle IA | `backend/demande/services/ia.py` | Règles sur le texte de description, **la vidéo n'est pas analysée** |
| Matching | `backend/matching/services/matching.py` | Comparaison **de chaînes** origine/destination (pas de distance réelle) |
| Paiement | `paiement/views.py`, `paiement/permissions.py`, `mobile/lib/services/payment_service.dart` | Webhook accessible à **n'importe quel utilisateur authentifié** ; le mobile appelle lui-même le webhook « SUCCESS » juste après l'initiation |
| Suivi | `mobile/lib/screens/shared/tracking_screen.dart` | Frise de statuts uniquement, **aucune position GPS** |

### Points techniques déjà réglés (ne pas défaire)
- `REST_FRAMEWORK["COERCE_DECIMAL_TO_STRING"] = False` : les décimaux sortent en **nombres JSON** (le Dart fait des `as num`).
- Vidéo de demande : champ fichier `Demande.video` (multipart), `video_url` généré côté serveur. Sur PaaS le disque est **éphémère** : prévoir un stockage externe avant production.
- Client Dio (`auth_service.dart`) : `Connection: close` + keep-alive désactivé (contournement des resets avec `runserver`). Ne pas retirer sans test.
- Android : AGP 8.13.0 / Gradle 8.14 / Kotlin 2.2.20 / compileSdk 36 / NDK 28.2.13676358 — **ne pas mettre à jour** sans demande, la chaîne a été difficile à stabiliser.
- Navigation : `context.push` pour les écrans secondaires (bouton retour), `context.go` uniquement pour les remplacements de flux (login, déconnexion). Utiliser `safePop(context)` pour « Annuler ».
- Erreurs réseau affichées via `friendlyError(e)` (`lib/utils/error_helper.dart`), jamais `e.toString()`.
- Dev sur téléphone physique : `runserver 0.0.0.0:8000`, IP du PC dans `DJANGO_ALLOWED_HOSTS`, app lancée avec `--dart-define=API_BASE_URL=http://<ip>:8000/api` (**le port est obligatoire**).

---

## 2. Tâches (dans cet ordre)

### T1 — Algorithme de matching réel

**Références :** `docs/06` §3 (critères et priorités), `docs/04` (BF-10, BF-27), `backend/matching/services/matching.py`.

**Objectif :** remplacer l'égalité de chaînes par une **proximité géographique réelle**, en gardant l'ordre de priorité documenté (fiabilité > proximité > date > capacité) et le filtre d'éligibilité (capacité suffisante).

**À faire :**
1. Ajouter des coordonnées (`origine_lat/lng`, `destination_lat/lng`) sur `Demande` et `Trajet` (champs nullables + migration, rétrocompatible).
2. Géocoder les villes saisies (service isolé `services/geocodage.py`, interface + implémentation Mapbox ; cache en base pour ne pas re-géocoder la même ville). Côté mobile, idéalement une autocomplétion de villes sur les formulaires « Nouvelle expédition » / « Nouveau trajet ».
3. Score de proximité = fonction décroissante de la **distance** (haversine) entre origines et entre destinations, avec seuils documentés en constantes (ex. plein score < X km). Un trajet dont l'itinéraire n'est pas compatible reste exclu.
4. Ajouter un critère **prix** *optionnel et de faible poids* : écart entre `Demande.montant_propose` et une estimation (distance × tarif de référence) — **demande d'abord à l'utilisateur** s'il le veut et avec quel poids (zone grise, non documentée).
5. Conserver un repli sans coordonnées (comparaison de chaînes actuelle) si le géocodage échoue.
6. Tests : cas identiques, villes voisines, capacité insuffisante, date hors fenêtre, absence de coordonnées.

**Critères d'acceptation :** deux villes proches mais écrites différemment (« Douala »/« Douala Bonabéri ») sont rapprochées ; classement stable et expliqué dans la réponse (`score` + détail par critère si utile).

### T2 — Contrôle IA avant publication

**Références :** `docs/12-pipeline-ia-verification.md` (**lire en entier**), `docs/11` §2.3, BNF-04 (verdict ≤ 30 s), BNF-10, BNF-16, `backend/demande/services/ia.py`, modèle `ControleIA`.

**Objectif :** analyser réellement la **vidéo** avant qu'une demande passe de `en_cours_controle` à `publiee` ou `rejetee`.

**À faire :**
1. **Asynchrone (Celery + Redis)** : `POST /demandes/` enregistre la demande (`en_cours_controle`) et lance la tâche ; la réponse ne bloque pas sur l'IA. Le mobile affiche l'état « analyse en cours » puis le verdict (polling court ou notification FCM).
2. Extraction de **frames** de la vidéo (ex. 1 image/seconde, plafonnées ; `ffmpeg` ou OpenCV — signale la dépendance avant de l'ajouter).
3. Étape 1 — détection d'objets/substances interdits via **Google Cloud Vision** (référentiel `docs/12` §2 : rejet auto pour 2.1 et 2.2, vigilance pour 2.3).
4. Étape 2 — cohérence description ↔ images + extraction de détails (marque, état, couleur, contenant) via un modèle vision-langage. **Groq** (décision validée le 03/10/2026, remplace GPT-4o mini).
5. Étape 3 — signaux d'altération suspecte déduits des sorties 1 et 2 (pas de modèle dédié en v1).
6. Verdict agrégé (`validée` / `rejetée` + motif précis : objet interdit / incohérence / altération). Rejet → motif communiqué au client.
7. **Transmission au transporteur** des détails extraits : visibles dans la fiche de demande **avant acceptation** (matching côté transporteur) **et** dans le détail de la course après acceptation (`docs/12` §5). Exposer ces champs dans les serializers concernés + écrans Flutter (`trip_detail_screen.dart`, `matching_trips_screen.dart`).
8. Interface `FournisseurVision` / `FournisseurCoherence` avec implémentation **simulée** conservée (mode par défaut sans clé) et bascule par variable d'environnement.
9. Comportement dégradé : API indisponible → tâche remise en file avec délai, demande laissée `en_cours_controle`, message explicite ; jamais de publication « par défaut ».

**Critères d'acceptation :** une vidéo montrant un objet de la liste interdite est rejetée avec motif ; une description incohérente est rejetée avec motif ; une vidéo conforme est publiée et ses détails apparaissent côté transporteur ; sans clés, le mode simulé fonctionne toujours.

### T3 — API de paiement mobile money (MTN MoMo / Orange Money)

**Références :** `docs/04` (BF-14 à BF-17, BF-24, BF-30, RM-02), `docs/11` §2.7, BNF-11, `backend/paiement/`.

**Objectif :** vrai paiement avec escrow, confirmé **par le fournisseur** (callback), plus par le mobile.

**À faire :**
1. Interface `FournisseurPaiement` (`initier`, `verifier_statut`, `rembourser`, `verser_au_transporteur`) + implémentations `MtnMomo` et `OrangeMoney` (sandbox d'abord) + `Simule` (conservé).
2. **Initiation synchrone** : le client saisit son **numéro mobile money** (nouveau champ dans `payment_screen.dart`), le backend appelle « request to pay » et renvoie `en_attente`. Le montant vient **uniquement** de `Course.montant_convenu`.
3. **Confirmation asynchrone** : endpoint callback du fournisseur ; **vérifier l'authenticité** (signature/secret/rappel de vérification du statut auprès du fournisseur). Remplacer la permission actuelle `EstWebhookPaiement` (qui accepte tout utilisateur connecté) — c'est une faille à corriger.
4. Supprimer l'appel « SUCCESS » simulé de `PaymentService.initiatePayment` côté mobile : l'écran affiche « en attente de confirmation sur votre téléphone » et **interroge** le statut jusqu'à `bloque_escrow` ou échec/expiration.
5. Libération de l'escrow à la confirmation de réception → **versement au transporteur** (API de décaissement du fournisseur) ; remboursement réel à l'annulation. Chaque transaction interrompue doit être traçable et rejouable (BNF-11) : journal des tentatives + commande admin de réconciliation.
6. Idempotence : un même callback rejoué ne doit pas doubler une opération. Références de transaction uniques, générées côté serveur.
7. Historique des paiements (`payment_history_screen.dart`) : afficher « en attente » vs « payé » comme en BF-30.

**Décision à demander à l'utilisateur avant de coder :** MTN/Orange en direct exigent un compte marchand/entreprise pour la production. Si ce n'est pas possible pour la soutenance, proposer un agrégateur (CinetPay, Flutterwave, Campay, etc.) — **non prévu dans `docs/13`**, donc validation obligatoire.

**Critères d'acceptation :** en sandbox, un paiement passe `en_attente` → `bloque_escrow` uniquement via le callback ; un callback falsifié est rejeté ; annulation → remboursement ; livraison confirmée → versement transporteur.

### T4 — Géolocalisation et suivi en temps réel

**Références :** `docs/06` (suivi), `docs/13`, `backend/course/`, `mobile/lib/screens/shared/tracking_screen.dart`.

**Objectif :** le client voit la position du transporteur sur une carte pendant `depart`/`en_route`.

**À faire :**
1. Backend : modèle `PositionCourse` (course, latitude, longitude, précision, horodatage) ; `POST /courses/{id}/position/` (transporteur de la course uniquement, course en `depart`/`en_route`) ; `GET /courses/{id}/position/` (dernière position, client de la course). Limiter la fréquence (rate limiting) et purger l'historique ancien.
2. Mobile transporteur : envoi périodique de la position (package de géolocalisation ; `permission_handler` est déjà présent) **pendant** la course, avec permission « en cours d'utilisation » et service de premier plan Android si l'envoi doit continuer écran éteint. Expliquer clairement la demande de permission à l'utilisateur.
3. Mobile client : carte (Mapbox ou Google Maps SDK — **demande l'avis de l'utilisateur**) avec marqueur de position, origine/destination, mise à jour automatique.
4. Transport de la donnée : commence par du **polling** (toutes les 5–10 s, simple à expliquer) ; ne passe à Django Channels/WebSocket que si l'utilisateur le demande (Firebase Realtime n'est pas dans `docs/13`).
5. Gestion des cas limites : GPS désactivé, permission refusée, pas de réseau (file locale des positions), course terminée (arrêt de l'envoi).

**Critères d'acceptation :** la position du transporteur se met à jour sur l'écran du client ; l'envoi s'arrête à `arrivee` ; un autre utilisateur ne peut ni lire ni écrire la position d'une course qui n'est pas la sienne.

### T5 (optionnel, à proposer avant de commencer) — Notifications push de la négociation
Le backend a déjà les modèles FCM (`notification`). Événements utiles à notifier : réservation reçue (transporteur), contre-proposition de montant (client), montant validé / course acceptée (transporteur / client), verdict IA (client), paiement confirmé. Nécessite l'ajout de `firebase_messaging` côté Flutter et un projet Firebase (`google-services.json`). **Ne le fais que si l'utilisateur confirme.**

---

## 3. Ce que l'utilisateur doit faire lui-même (clés, comptes, achats)

Tu ne peux ni créer ces comptes ni payer à sa place. **Avant chaque tâche, rappelle-lui précisément ce qui lui est demandé**, et code d'abord en mode simulé pour ne pas être bloqué en attendant. Les tarifs/quotas évoluent : **vérifie les pages officielles** avant de lui donner un montant.

| Tâche | Ce que l'utilisateur doit obtenir | Coût indicatif | Variables / emplacement |
|---|---|---|---|
| **T1** géocodage + carte | Compte **Mapbox** → jeton d'accès public (`pk.…`) ; pour la carte Flutter, un jeton secret de téléchargement du SDK | Offre gratuite mensuelle suffisante pour un projet étudiant (à vérifier) | `MAPBOX_ACCESS_TOKEN` (backend `.env`) ; jeton public via `--dart-define` côté mobile |
| **T2** Vision | Projet **Google Cloud** + activation de l'API **Cloud Vision** + clé de compte de service (JSON). Le compte de facturation doit être activé (carte bancaire demandée) même pour l'usage gratuit | Quota mensuel gratuit puis payant (à vérifier) ; crédits d'essai possibles | `GOOGLE_APPLICATION_CREDENTIALS` (chemin du JSON, **hors du dépôt**) |
| **T2** cohérence texte/image | Compte **Groq** (console.groq.com) → clé API ; choisir un modèle vision-langage disponible | Offre gratuite avec limites de débit (à vérifier) | `GROQ_API_KEY`, `GROQ_MODEL` |
| **T3** paiement | Compte **CamPay** (demo.campay.net pour les tests, puis www.campay.net) → identifiants de l'application (App Username / App Password) et clé webhook ; activer les retraits (versements) sur le compte. Décision du 04/10/2026 : CamPay remplace l'intégration directe MTN MoMo / Orange Money | Démo gratuite ; production = validation du compte marchand et frais par transaction | `CAMPAY_USERNAME`, `CAMPAY_PASSWORD`, `CAMPAY_WEBHOOK_KEY`, `CAMPAY_ENV`, `CAMPAY_FRAIS_POURCENT` |
| **T3** callback | URL **publique HTTPS** du backend pour que le fournisseur rappelle (backend hébergé, ou tunnel type ngrok en test) | Gratuit (tunnel) | `PUBLIC_BASE_URL` |
| **T4** carte | Jeton **Mapbox** (déjà obtenu en T1) **ou** clé **Google Maps SDK** (facturation à activer, crédit mensuel gratuit) | Voir T1 | Manifeste Android / `--dart-define` |
| **T5** (si retenu) | Projet **Firebase** + `google-services.json` | Gratuit | Fichier dans `mobile/android/app/` |
| **Redis** (T2) | Redis en local via `docker-compose up -d` (déjà dans le projet) ; en hébergement, add-on Redis (Render/Railway) ou Upstash | Offre gratuite possible | `REDIS_HOST`, `REDIS_PORT` (ou URL) |

**Conseil à donner à l'utilisateur :** pour la soutenance, le mode sandbox/simulé bien démontré vaut mieux qu'une production à moitié configurée. Priorité suggérée : T2 (cœur de la « douane numérique »), puis T3, T1, T4.

---

## 4. Définition de « terminé » pour chaque tâche
- Code backend + mobile livré, `manage.py check` et `flutter analyze` sans erreur.
- Mode simulé toujours utilisable sans clé ; bascule documentée dans `.env.example`.
- Scénario de test manuel décrit (commandes `curl`/étapes dans l'app) + tests automatisés backend.
- Résumé court : choix de conception, points de vigilance, ce qui reste à la charge de l'utilisateur.
- Arrêt et attente de validation avant la tâche suivante.
