# 08 — Diagrammes de Séquence

Ce fichier décrit textuellement les séquences d'interaction les plus riches du système. Chaque séquence liste les participants, puis le déroulé chronologique des messages échangés.

## 1. Séquence — Création de demande + contrôle IA

**Participants :** Client, Application (Frontend), Backend, Système IA (Vision API + Groq), Administrateur (branche alternative)

**Déroulé nominal :**
1. Client → Frontend : renseigne origine, destination, date, description.
2. Client → Frontend : filme l'article (vidéo).
3. Frontend → Backend : envoie la demande (métadonnées + vidéo + description).
4. Backend → Système IA : transmet la vidéo pour détection d'objets interdits (Vision API).
5. Système IA → Backend : retourne la liste d'objets détectés + score de conformité.
6. Backend → Système IA : transmet vidéo + description pour vérification de cohérence (Groq).
7. Système IA → Backend : retourne un verdict de cohérence + détails sur l'objet (pour usage transporteur).
8. Backend : agrège les deux verdicts → décision finale (validé/rejeté), sous 30 secondes au total (BNF-04).
9. Backend → Frontend : notifie le résultat.
10. Frontend → Client : affiche "Demande publiée" (cas validé).

**Branche alternative — Rejet :**
9a. Backend → Frontend : notifie "Demande rejetée" + motif.
9b. Frontend → Client : affiche le motif, propose "Recommencer" ou "Contester".
9c. [si contestation] Client → Frontend → Backend : soumission de la contestation.
9d. Backend → Administrateur : notifie une revue en attente.
9e. Administrateur → Backend : décision (confirme rejet / infirme rejet).
9f. [si infirmé] Backend → Frontend → Client : "Demande publiée" (publication manuelle, contourne le score IA initial).

## 2. Séquence — Matching et réservation

**Participants :** Client, Backend (moteur de matching), Transporteur

**Déroulé nominal :**
1. Backend (déclenché après validation IA) : calcule le score de chaque trajet transporteur compatible selon les critères ordonnés (fiabilité, proximité, date, capacité — cf. `06-fonctionnalites-detaillees.md`).
2. Backend → Client : transmet la liste de transporteurs classés.
3. Client → Backend : sélectionne un transporteur dans la liste.
4. Backend → Transporteur : notifie une nouvelle demande compatible.
5. Transporteur → Backend : accepte la demande.
6. Backend → Client : confirme la réservation.
7. Backend → Transporteur : confirme la réservation.

**Branche alternative — Refus/non-réponse du transporteur :**
5a. Transporteur → Backend : ne répond pas / refuse.
5b. Backend → Client : la demande reste visible pour les autres transporteurs de la liste ; le client peut sélectionner une autre proposition (retour à l'étape 3 avec un autre candidat).

## 3. Séquence — Paiement, escrow et livraison

**Participants :** Client, Backend, Système de paiement mobile (fonctionnel, sans détail technique provider), Transporteur

**Déroulé nominal :**
1. Client → Backend : initie le paiement de la course.
2. Backend → Système de paiement mobile (CamPay) : demande le prélèvement sur le numéro MTN MoMo ou Orange Money choisi par le client, qui valide sur son téléphone.
3. Système de paiement mobile → Backend : confirme la transaction.
4. Backend : crée l'enregistrement escrow, statut "en attente".
5. Backend → Client : confirme le paiement (course réservée et sécurisée).
6. Backend → Transporteur : confirme que la course est payée et sécurisée (statut "en attente" côté historique transporteur).
7. Transporteur → Backend : met à jour le statut "Départ".
8. Backend → Client : notifie "Départ" en temps réel.
9. Transporteur → Backend : met à jour le statut "Arrivé à destination".
10. Backend → Client : notifie "Arrivé à destination".
11. Transporteur → Backend : met à jour le statut "Livré".
12. Backend → Client : notifie "Livré", invite à confirmer la réception.
13. Client → Backend : confirme la réception.
14. Backend : libère les fonds escrow → statut "payé" côté transporteur.
15. Backend → Transporteur : notifie la libération des fonds.

**Branche alternative — Annulation (avant livraison) :**
7a. Client → Backend : annule la réservation.
7b. Backend : rembourse au client le prix de la course via CamPay (RM-02 ; commission et frais non remboursés), statut "remboursé".
7c. Backend → Transporteur : notifie l'annulation.

## 4. Séquence — Déclaration et traitement d'un litige

**Participants :** Client ou Transporteur (déclarant), Backend, Administrateur, autre partie (notifiée)

**Déroulé nominal :**
1. Déclarant → Backend : déclare un litige sur une course (motif libre).
2. Backend : rassemble les éléments contextuels (statuts de course, incidents signalés, historique de paiement, résultat du contrôle IA initial).
3. Backend → Administrateur : notifie un litige en attente, avec dossier complet.
4. Administrateur → Backend : consulte le dossier, arbitre.
5. Backend : applique la décision (ex : libération ou remboursement de l'escrow, mise à jour du statut de la course).
6. Backend → Client : notifie la décision.
7. Backend → Transporteur : notifie la décision.

## 5. Notes de couverture

Les séquences CRUD simples (gestion de profil, ajout/suppression de trajet) ne sont pas détaillées ici — elles suivent un échange direct Frontend ↔ Backend sans logique métier complexe, et sont déjà couvertes fonctionnellement dans `04-besoins-fonctionnels.md` et `06-fonctionnalites-detaillees.md`.
