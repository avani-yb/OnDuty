# 09 — Diagrammes d'Activité

Ce fichier décrit les processus clés sous forme de séquences d'étapes uniques, avec l'acteur responsable indiqué à chaque étape et les points de décision explicites.

## 1. Activité — Processus de validation IA d'une demande

| Étape | Acteur | Action / Décision |
|---|---|---|
| 1 | Client | Renseigne les informations de la demande (trajet, description) |
| 2 | Client | Filme l'article à expédier |
| 3 | Système | Lance le contrôle IA (détection objets interdits + cohérence + altération) |
| 4 | Système | **Décision :** verdict IA ? |
| 4a | Système | → Si **validé** : passe à l'étape 5 |
| 4b | Système | → Si **rejeté** : passe à l'étape 8 |
| 5 | Système | Publie la demande |
| 6 | Système | Rend la demande éligible au matching |
| 7 | — | **Fin (branche validée)** |
| 8 | Système | Informe le client du rejet et du motif |
| 9 | Client | **Décision :** que fait le client ? |
| 9a | Client | → Recommencer : retour à l'étape 1 |
| 9b | Client | → Contester : passe à l'étape 10 |
| 9c | Client | → Abandonner : **Fin (branche abandonnée)** |
| 10 | Client | Soumet une demande de revue manuelle à l'admin |
| 11 | Administrateur | Consulte la vidéo, la description et le motif de rejet IA |
| 12 | Administrateur | **Décision :** confirme ou infirme le rejet ? |
| 12a | Administrateur | → Confirme le rejet : **Fin (branche rejet confirmé)**, retour possible à l'étape 9 |
| 12b | Administrateur | → Infirme le rejet : passe à l'étape 5 (publication manuelle) |

## 2. Activité — Cycle de vie complet d'une course

| Étape | Acteur | Action / Décision |
|---|---|---|
| 1 | Système | Demande validée par l'IA, matching calculé |
| 2 | Client | Consulte la liste de transporteurs classés |
| 3 | Client | Sélectionne un transporteur |
| 4 | Transporteur | **Décision :** accepte la demande ? |
| 4a | Transporteur | → Non / pas de réponse : retour à l'étape 2 (autre proposition) |
| 4b | Transporteur | → Oui : passe à l'étape 5 |
| 5 | Système | Confirme la réservation (client + transporteur) |
| 6 | Client | Paie la course via mobile money |
| 7 | Système | Crée l'enregistrement escrow (statut "en attente") |
| 8 | Client | **Décision :** annule la réservation ? *(possible à tout moment avant livraison)* |
| 8a | Client | → Oui : passe à l'étape 9 |
| 8b | Client | → Non : passe à l'étape 10 |
| 9 | Système | Débloque intégralement l'escrow, notifie le transporteur — **Fin (branche annulée)** |
| 10 | Transporteur | Met à jour le statut : Départ |
| 11 | Transporteur | **Décision :** incident pendant le trajet ? |
| 11a | Transporteur | → Oui : signale l'incident (champ texte libre), poursuite du processus |
| 11b | Transporteur | → Non : poursuite du processus |
| 12 | Transporteur | Met à jour le statut : Arrivé à destination |
| 13 | Transporteur | Met à jour le statut : Livré |
| 14 | Client | **Décision :** confirme la réception ou déclare un litige ? |
| 14a | Client | → Confirme la réception : passe à l'étape 15 |
| 14b | Client | → Déclare un litige : passe à l'étape 16 |
| 15 | Système | Libère les fonds escrow au transporteur (statut "payé") — **Fin (branche nominale)** |
| 16 | Administrateur | Consulte le dossier complet de la course (statuts, incidents, paiement) |
| 17 | Administrateur | Arbitre le litige (décision : libération, remboursement, autre) |
| 18 | Système | Applique la décision, met à jour les statuts | 
| 19 | — | **Fin (branche litige résolu)** |

## 3. Notes de couverture

Ces deux diagrammes couvrent les processus à embranchements significatifs. Les activités linéaires sans décision (ex : ajout d'un trajet, modification de profil) ne nécessitent pas de diagramme d'activité dédié et sont déjà couvertes dans `04-besoins-fonctionnels.md`.
