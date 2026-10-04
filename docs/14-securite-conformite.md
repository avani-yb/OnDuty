# 14 — Sécurité et Conformité

## 1. Objectif du document

Ce fichier détaille les mesures de sécurité **système** (authentification, chiffrement, gestion des accès, rétention des données) qui complètent la sécurité **fonctionnelle** déjà couverte par le pipeline de contrôle IA (`12-pipeline-ia-verification.md`). L'aspect sécuritaire est traité comme une priorité forte du projet, conformément à `02-objectifs.md`.

## 2. Authentification et gestion des comptes

| Mesure | Détail |
|---|---|
| Hashing des mots de passe | Aucun mot de passe stocké en clair. Utilisation du hashing intégré à Django (PBKDF2 par défaut, ou Argon2 via `django-argon2` pour un niveau de sécurité supérieur — recommandé si le temps le permet). |
| Authentification API | Tokens JWT (via `djangorestframework-simplejwt`) avec expiration courte du token d'accès et mécanisme de refresh token, pour limiter la fenêtre d'exploitation en cas de vol de token. |
| Compte administrateur | Authentification renforcée (mot de passe fort imposé + possibilité d'ajouter une authentification à deux facteurs si le temps le permet) — justifié par le fait qu'un compte admin unique concentre un pouvoir de décision important (validation KYC, arbitrage litiges, accès à l'ensemble des données). |
| Verrouillage après tentatives échouées | Blocage temporaire du compte après un nombre défini de tentatives de connexion échouées (protection contre le brute-force), via une librairie comme `django-axes`. |

## 3. Chiffrement et transport des données

| Mesure | Détail |
|---|---|
| Chiffrement en transit | HTTPS obligatoire sur l'ensemble des échanges Backend ↔ App Flutter ↔ APIs tierces. Aucun endpoint HTTP non chiffré exposé en production. Les hébergeurs proposés (Render/Railway, cf. `13-architecture-technique.md`) fournissent un certificat TLS géré automatiquement. |
| Chiffrement au repos | Chiffrement au niveau du disque/volume PostgreSQL fourni nativement par l'hébergeur managé. Pour les champs particulièrement sensibles (numéro de CNI, données de vérification KYC brutes), envisager un chiffrement applicatif additionnel au niveau du champ (ex. `django-cryptography` ou chiffrement symétrique appliqué avant écriture en base), en complément du chiffrement disque. |
| Stockage des médias sensibles | Les vidéos de contrôle et documents CNI sont stockés sur Cloudinary avec des URLs signées et à accès restreint (pas d'URL publique devinable), plutôt qu'un accès direct sans contrôle. |
| Clés et secrets | Aucune clé API (Vision API, Groq, Smile Identity, MTN MoMo, Orange Money) ne doit être codée en dur dans le code source. Utilisation de variables d'environnement, gérées via un fichier `.env` non versionné (exclu par `.gitignore`) en développement, et via les mécanismes de secrets de l'hébergeur en production. |

## 4. Gestion des accès

| Mesure | Détail |
|---|---|
| Accès administrateur | Un seul compte admin fonctionnel (cf. `03-acteurs-parties-prenantes.md`) — pas de système de permissions granulaire à mettre en place dans le périmètre actuel. L'accès à l'interface web admin (Django Admin personnalisé, cf. `13-architecture-technique.md`) est protégé par l'authentification renforcée décrite en section 2. |
| Accès aux données personnelles | Un client/transporteur ne peut accéder qu'à ses propres données (profil, historique, courses) — contrôle appliqué systématiquement au niveau des permissions DRF (`IsAuthenticated` + vérification de propriété sur chaque objet, via des permissions personnalisées). |
| Accès aux vidéos de contrôle et données KYC | Restreint au propriétaire de la donnée, à l'administrateur (en cas de contestation ou de litige), et aux services IA externes le temps strict du traitement — aucun autre utilisateur ne peut consulter la vidéo ou les documents CNI d'un tiers. |

## 5. Rétention et suppression des données

| Type de donnée | Durée de conservation | Justification |
|---|---|---|
| Vidéos de contrôle IA (demandes d'expédition) | **1 mois** après traitement, puis suppression définitive | Fenêtre suffisante pour couvrir un éventuel litige ou contestation post-livraison, sans conserver indéfiniment des données visuelles sensibles sur le contenu des colis. |
| Documents CNI (KYC) | **Conservation permanente** | Nécessaire pour la traçabilité à long terme des transporteurs vérifiés, la prévention de la fraude à l'identité (ex. réutilisation d'un compte suspendu) et en cas de nécessité légale de justifier l'identité d'un utilisateur ayant opéré sur la plateforme. |
| Données de transaction (paiements, escrow) | Conservation permanente (registre financier) | Nécessaire pour l'audit, la comptabilité, et la résolution de litiges financiers, même longtemps après la course. |
| Historique des courses, évaluations, litiges | Conservation permanente | Alimente le score de fiabilité (`10-diagramme-classes.md`) et sert d'historique en cas de récidive ou de litige. |

**Point de vigilance :** la suppression automatique des vidéos après un mois doit être implémentée comme une tâche planifiée (Celery Beat, ou tâche cron) plutôt que comme une suppression manuelle — sans quoi le risque d'oubli rend la politique de rétention inopérante en pratique.

## 6. Conformité légale (cadre camerounais)

Le Cameroun dispose d'un cadre juridique de référence en matière de cybersécurité et de protection des données personnelles :

- **Loi n° 2010/012 du 21 décembre 2010** relative à la cybersécurité et à la cybercriminalité au Cameroun — pose les bases de la protection des systèmes d'information et des données électroniques.
- Le pays a engagé des travaux vers une loi spécifique de protection des données à caractère personnel (processus législatif suivi de près par les acteurs numériques camerounais), dans la ligne des standards régionaux (CEMAC) et internationaux (inspirés du RGPD européen) — ce cadre étant en évolution, une veille reste nécessaire pour ajuster la politique de rétention et de traitement si une loi dédiée entre en vigueur avant ou après la soutenance.

**Implications concrètes pour OnDuty :**
- Recueillir le **consentement explicite** de l'utilisateur au moment de la collecte de sa CNI et de la vidéo de contrôle (mention claire dans le parcours d'inscription/de demande, pas seulement dans des CGU non lues).
- Informer clairement l'utilisateur de la durée de conservation de chaque type de donnée (section 5), idéalement via une politique de confidentialité accessible depuis l'application.
- Limiter la collecte au strict nécessaire (principe de minimisation) : le contrôle IA n'a besoin que de la vidéo et de la description, pas de données additionnelles non pertinentes.

## 7. Journalisation et auditabilité

| Mesure | Détail |
|---|---|
| Journal des décisions IA | Chaque verdict de `ControleIA` (validé/rejeté, motif) est conservé de manière durable même après suppression de la vidéo source (1 mois) — seule la donnée visuelle brute est supprimée, pas la trace de la décision. |
| Journal des actions admin | Chaque action de l'administrateur (validation KYC manuelle, arbitrage de litige, confirmation/infirmation d'un rejet IA) doit être horodatée et attribuée, pour permettre un audit a posteriori en cas de contestation sur une décision admin elle-même. |
| Journal des accès aux données sensibles | Recommandé : tracer les accès aux documents CNI par l'admin (qui a consulté quoi, quand), utile en cas de doute sur un usage abusif de l'accès admin. |

## 8. Synthèse des priorités pour l'implémentation

Compte tenu du délai, voici un ordre de priorité recommandé si tout ne peut pas être implémenté en profondeur :
1. HTTPS + hashing mots de passe + JWT (non négociable, base de toute sécurité applicative).
2. Contrôle d'accès aux données personnelles (permissions DRF par propriété).
3. Authentification renforcée du compte admin unique.
4. Chiffrement applicatif des champs les plus sensibles (CNI) — si le temps le permet.
5. Tâche planifiée de suppression des vidéos après 1 mois.
6. Journalisation des actions admin.
