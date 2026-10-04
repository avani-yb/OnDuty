# 06 — Fonctionnalités Détaillées

Ce document détaille le fonctionnement précis de chaque fonctionnalité majeure, en complément des besoins fonctionnels listés dans `04-besoins-fonctionnels.md`.

## 1. Branding page (Visiteur)

Présentation de l'application en **trois étapes scrollables**, affichée avant inscription. Contenu suggéré (à ajuster) :
1. Le problème : camions/véhicules qui roulent à vide, expéditions non sécurisées.
2. La solution : matching intelligent + paiement sécurisé par escrow.
3. La confiance : vérification CNI, contrôle IA des colis, suivi en temps réel.

## 2. Création de demande d'expédition (Client)

**Déroulé :**
1. Le client renseigne les informations du trajet souhaité (origine, destination, date) et une description de l'objet/marchandise.
2. Le client filme l'article (vidéo courte, obligatoire).
3. La vidéo et la description sont transmises au module de contrôle IA (`12-pipeline-ia-verification.md`).
4. Résultat sous 30 secondes maximum (BNF-04) :
   - **Validé** → la demande devient active et éligible au matching.
   - **Rejeté** → la demande n'est pas émise. Le client voit le motif de rejet et peut :
     - recommencer le processus (nouvelle vidéo/description),
     - ou soumettre le rejet à une **revue manuelle par l'administrateur** s'il estime que l'IA s'est trompée.

## 3. Matching intelligent

### 3.1 Critères de scoring (par ordre de priorité décroissante)

| Ordre | Critère | Description |
|---|---|---|
| 1 | **Note de fiabilité du transporteur** | Score basé sur l'historique du transporteur (courses menées à bien, incidents, ponctualité, avis). Un transporteur peu fiable est pénalisé dans le classement même s'il correspond parfaitement au trajet. |
| 2 | **Proximité géographique** | Correspondance entre le trajet déclaré par le transporteur (origine/destination) et celui demandé par le client — y compris tolérance de détour à définir. |
| 3 | **Compatibilité de date** | Le trajet du transporteur doit avoir lieu dans une fenêtre proche compatible avec le besoin du client (cf. RM-03, fichier 04 : appartenir à la liste garantit un trajet dans les prochains jours). |
| 4 | **Capacité disponible** | Le volume/poids restant disponible sur le véhicule du transporteur doit être suffisant pour la marchandise du client. |

Le score final combine ces quatre critères pondérés dans cet ordre de priorité (le détail de la formule de pondération sera précisé lors de l'implémentation — ce fichier documente la logique métier, pas l'algorithme exact).

### 3.2 Résultat du matching

- Le client reçoit une **liste de transporteurs classés** du plus optimal au moins optimal.
- Le transporteur reçoit la liste des **demandes compatibles** avec son trajet publié, et choisit celle(s) qu'il accepte.
- La sélection est bilatérale : le client choisit un transporteur dans la liste, **et** le transporteur doit accepter la demande pour que la réservation soit confirmée (cf. `03-acteurs-parties-prenantes.md` : "lorsque le transporteur accepte la course").

## 4. Réservation

- Créée lorsque le client sélectionne une proposition **et** que le transporteur accepte.
- Peut être **annulée par le client à tout moment, sans condition ni pénalité** (RM-02).
- Une annulation rembourse au client le prix de la course si un paiement avait déjà été effectué ; la commission OnDuty et les frais de paiement ne sont pas remboursés.

## 5. Paiement et escrow

**Cycle de vie d'un paiement :**
1. Le client paie la course via MTN MoMo ou Orange Money (agrégateur **CamPay**). Montant payé = prix convenu + commission OnDuty (5 % jusqu'à 10 000 FCFA, 10 % au-delà) + frais CamPay (2 × le taux CamPay, calculés sur le prix, pour couvrir l'encaissement et le versement au transporteur).
2. Les fonds sont placés en **escrow** — statut "en attente" côté transporteur, "payé (bloqué)" côté client.
3. Le transporteur exécute la course et met à jour les statuts (départ, arrivée, livré).
4. Le client confirme la réception → les fonds sont libérés au transporteur, statut passe à **"payé"**.
5. En cas de litige avant confirmation, les fonds restent bloqués jusqu'à arbitrage admin.

## 6. Suivi de course

- Le client suit la progression du colis en temps réel (statuts mis à jour par le transporteur + géolocalisation si disponible).
- Statuts standards : **En attente de départ → Départ → En route → Arrivé à destination → Livré**.
- Le client confirme la réception, ce qui clôture la course et déclenche la libération escrow.

## 7. Signalement d'incident

- Le transporteur peut signaler un incident à tout moment pendant une course, via un **champ texte libre** décrivant la situation (pas de catégories prédéfinies dans la version actuelle).
- L'incident est visible par l'admin et peut servir de pièce en cas de litige ultérieur.

## 8. Gestion des litiges

- **Déclencheur :** tout utilisateur (client ou transporteur) peut déclarer un litige concernant une course, **quel qu'en soit le motif** (colis endommagé, refus de paiement, non-livraison, désaccord sur l'état du colis à la livraison, etc.). Il n'y a pas de liste fermée de motifs — le litige est un signalement libre adressé à l'admin.
- **Traitement :** l'admin consulte les éléments disponibles (statuts de la course, éventuel signalement d'incident du transporteur, historique de paiement, résultat du contrôle IA initial) et arbitre : validation de la livraison, remboursement, ou toute autre décision.
- **Lien avec le contrôle IA :** un cas particulier de "litige" est la contestation d'un rejet IA (BF-08) — celle-ci suit un circuit dédié déjà décrit au fichier 04, mais reste conceptuellement un sous-cas du mécanisme général de recours à l'admin.

## 9. Vérification d'identité (KYC/CNI)

- Disponible pour tout utilisateur souhaitant sécuriser son profil.
- **Obligatoire** pour activer le rôle Transporteur (cf. BF-22, `03-acteurs-parties-prenantes.md`).
- Détail technique du processus dans `12-pipeline-ia-verification.md`.

## 10. Devenir transporteur

- Depuis son profil Client, l'utilisateur déclenche l'activation du rôle Transporteur.
- Étapes : renseignement des informations véhicule + vérification CNI/KYC renforcée.
- Une fois validé, le rôle Transporteur est actif en permanence aux côtés du rôle Client (cf. `03-acteurs-parties-prenantes.md`).

## 11. Tableau de bord admin

Contenu suggéré à valider avec toi lors du fichier dédié à l'architecture/sécurité — a minima :
- Nombre de courses actives / terminées / annulées.
- Volume de transactions escrow en cours.
- Nombre de demandes rejetées par l'IA / nombre de contestations en attente.
- Litiges ouverts / résolus.
- Nouveaux comptes transporteurs en attente de validation KYC.

## 12. Gestion des comptes (admin)

- Consultation de tout profil (client/transporteur).
- Suspension/réactivation de compte.
- Validation manuelle de KYC en cas de doute (complémentaire à Smile Identity).
