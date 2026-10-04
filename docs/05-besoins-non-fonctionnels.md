# 05 — Besoins Non Fonctionnels

## 1. Disponibilité

| Code | Besoin |
|---|---|
| BNF-01 | Le service de matching doit être disponible **24/7**, sans fenêtre de maintenance bloquant la publication de trajets ou de demandes. |
| BNF-02 | Le système doit viser une disponibilité globale minimale de 99% en usage normal (hors incidents majeurs d'infrastructure ou de connectivité réseau nationale, hors du contrôle de l'application). |
| BNF-03 | En cas d'indisponibilité d'un service tiers (API IA, API mobile money), le système doit informer clairement l'utilisateur plutôt que de rester silencieux ou de planter (voir BNF-10 sur la gestion des pannes de dépendances externes).

## 2. Performance

| Code | Besoin |
|---|---|
| BNF-04 | Le contrôle IA d'une demande d'expédition (détection objets interdits + vérification de cohérence + détection d'altération) doit retourner un résultat en **30 secondes maximum** après soumission de la vidéo et de la description. |
| BNF-05 | Le calcul du matching (liste de transporteurs classés) doit s'afficher en moins de 5 secondes après validation de la demande par l'IA, dans des conditions réseau normales. |
| BNF-06 | Les mises à jour de statut de course (départ, arrivée, livré) doivent être reflétées côté client en temps quasi réel (délai cible < 10 secondes), via notification push. |
| BNF-07 | L'application doit rester utilisable en connexion réseau dégradée (2G/3G), fréquente hors des grandes villes camerounaises — dégradation progressive plutôt que blocage total (ex : cache local, retry automatique).

## 3. Scalabilité

| Code | Besoin |
|---|---|
| BNF-08 | L'architecture doit pouvoir absorber une croissance progressive du nombre d'utilisateurs et de trajets sans refonte majeure (voir `13-architecture-technique.md` pour les choix techniques associés : découplage des services IA, files d'attente éventuelles pour le traitement asynchrone du contrôle IA). |
| BNF-09 | Le module de contrôle IA, potentiellement coûteux en traitement, doit pouvoir être traité de manière asynchrone/en file d'attente si le volume de demandes simultanées augmente, sans dégrader le délai cible de 30 secondes pour un usage normal. |

## 4. Fiabilité et gestion des pannes

| Code | Besoin |
|---|---|
| BNF-10 | Si une API externe (Vision API, Groq, Smile Identity, MTN MoMo, Orange Money) est indisponible, le système doit basculer vers un comportement dégradé défini (message d'erreur explicite, mise en file d'attente, ou solution de repli technique — voir `12-pipeline-ia-verification.md` pour les alternatives prévues par API). |
| BNF-11 | Aucune perte de fonds escrow ne doit pouvoir survenir suite à une panne technique : toute transaction interrompue doit être traçable et récupérable (réconciliation manuelle possible par l'admin). |

## 5. Utilisabilité

| Code | Besoin |
|---|---|
| BNF-12 | L'application doit être utilisable par un public non technophile (langage simple, parcours guidé, feedback visuel clair à chaque étape du contrôle IA et du paiement). |
| BNF-13 | La page de branding (3 étapes scrollables) doit permettre à un nouvel utilisateur de comprendre le principe de l'application sans lecture de documentation externe. |

## 6. Portabilité

| Code | Besoin |
|---|---|
| BNF-14 | L'application mobile doit être compatible avec les versions Android majoritairement utilisées au Cameroun (à confirmer, cible large : Android 8+). |

## 7. Maintenabilité

| Code | Besoin |
|---|---|
| BNF-15 | Le backend doit être structuré en modules/apps Django découplés par domaine fonctionnel (utilisateurs, trajets, matching, paiement, contrôle IA, litiges), conformément à l'approche "squelette complet dès le départ" définie dans `02-objectifs.md`. |
| BNF-16 | Chaque intégration à une API tierce (Vision API, Groq, Smile Identity, MTN MoMo, Orange Money) doit être isolée derrière une interface interne, pour permettre un remplacement par une alternative (modèle open-source, autre fournisseur) sans impact sur le reste du système. |

## 8. Sécurité et conformité

Les exigences de sécurité (protection des données personnelles, chiffrement, gestion des accès, conformité à la réglementation camerounaise sur les données à caractère personnel et la cybersécurité) seront traitées en détail dans un **fichier dédié à la sécurité**, à ajouter à la suite du fichier `12-pipeline-ia-verification.md`. Ce point est identifié ici comme non-fonctionnel critique, mais volontairement non détaillé dans ce fichier pour éviter la redondance.

> **Action de suivi :** ajouter un fichier `14-securite-conformite.md` à la liste initiale pour couvrir ce point en profondeur (le pipeline IA au fichier 12 couvrira la sécurité *fonctionnelle* liée au contrôle des objets/KYC, tandis que le fichier 14 couvrira la sécurité *système* : authentification, chiffrement, gestion des accès admin, conformité légale).
