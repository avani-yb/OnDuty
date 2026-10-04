# 01 — Introduction et Contexte

## 1. Présentation générale

**OnDuty** est une application mobile de mise en relation entre **expéditeurs/destinataires** de colis ou marchandises et **transporteurs** disposant d'une capacité de transport disponible (camion, pick-up, véhicule léger) sur un trajet donné, à l'échelle du **territoire camerounais**.

Le principe : au lieu qu'un camion ou un véhicule circule à vide ou sous-rempli sur un trajet interurbain, OnDuty permet à ce véhicule d'embarquer des colis ou marchandises appartenant à des clients situés sur ce même trajet, moyennant une rémunération sécurisée par mobile money.

## 2. Contexte sectoriel

### 2.1 Un secteur dominé par la route, mais fragmenté

Le transport routier reste le mode dominant de mouvement de marchandises au Cameroun, la route représentant la grande majorité des flux interurbains de marchandises dans le pays. Le secteur logistique camerounais est décrit comme dominé par quelques grands acteurs (transport aérien, fret maritime), le transport routier restant largement assuré par une multitude de petits transporteurs indépendants (camions, véhicules légers) peu ou pas digitalisés.

Le paysage actuel de l'expédition de colis repose largement sur des **agences de voyage traditionnelles** (ex. United Express, Touristique Express, General Express Voyages, Transcam) qui combinent transport de passagers et expédition de colis sur des lignes fixes, avec des points de collecte physiques dans les grandes villes. Ce modèle fonctionne, mais reste contraint par des horaires fixes, des trajets prédéfinis, et une couverture qui s'amenuise fortement dès qu'on s'éloigne des grands axes (Douala–Yaoundé notamment). En parallèle, une part importante des échanges de colis entre particuliers et petits commerçants continue de passer par le **bouche-à-oreille** (chauffeurs de connaissance, groupes WhatsApp informels), sans garantie de sécurité, de suivi, ni de recours en cas de perte ou de litige.

### 2.2 Le problème du retour à vide

Un phénomène structurel touche le transport de marchandises en Afrique centrale : une proportion significative des camions effectue son trajet retour à vide, faute de fret disponible ou d'organisation permettant de le trouver — un problème documenté à l'échelle de la sous-région, avec des taux de retour à vide atteignant plusieurs dizaines de pourcents selon les corridors. Cette inefficience pèse directement sur la rentabilité des transporteurs (carburant, péages, temps immobilisé) et se répercute sur le prix final payé par les expéditeurs.

Le Cameroun a d'ailleurs entamé une démarche de digitalisation du fret terrestre (dématérialisation de la lettre de voiture, taxe à l'essieu) sur les grands corridors internationaux, signe que la fluidification numérique du secteur est déjà une priorité nationale reconnue — mais ces initiatives ciblent le fret international lourd, pas le transport interurbain domestique de colis et petites marchandises, qui reste le terrain d'OnDuty.

### 2.3 Un terrain favorable au paiement mobile

Le Cameroun affiche un des taux d'adoption du mobile money les plus élevés d'Afrique centrale : environ 43 % de la population adulte utilise activement le mobile money, porté par un duopole MTN MoMo / Orange Money qui totalise à eux deux plus de 67 000 points d'agents à travers les dix régions du pays. Le volume de transactions mobile money continue de croître fortement d'une année sur l'autre. Cette infrastructure est un atout majeur pour un modèle reposant sur le paiement et l'escrow mobile : la barrière à l'adoption côté paiement est déjà largement levée, y compris en zone rurale où la bancarisation classique reste très faible.

## 3. Problématique

De ce contexte se dégagent trois problèmes concrets qu'OnDuty cherche à adresser :

1. **Sous-exploitation de la capacité de transport existante** : des trajets sont effectués à vide ou partiellement chargés, alors qu'une demande d'expédition existe sur les mêmes axes.
2. **Absence de confiance structurée** entre particuliers/commerçants et transporteurs indépendants en dehors des agences établies : pas de vérification d'identité systématique, pas de garantie sur les fonds, pas de traçabilité de ce qui est transporté.
3. **Rigidité de l'offre existante** : les agences de voyage classiques imposent des horaires et trajets fixes, avec une couverture qui décroît fortement hors des grands axes urbains, ne serait-ce que par la nature du modèle (véhicules dédiés, réseau de gares).

## 4. Vision du projet

OnDuty vise à devenir la plateforme de référence pour la mise en relation expéditeurs/transporteurs à l'échelle nationale, en s'appuyant sur :

- Un **matching intelligent** entre les besoins d'expédition et les trajets disponibles publiés par les transporteurs.
- Un **module de contrôle par IA** au moment de la création de la demande, jouant le rôle d'une "douane numérique" : détection d'objets/substances interdits, vérification de cohérence entre la description du client et l'image filmée, détection d'altération suspecte.
- Un système de **paiement mobile sécurisé par escrow**, où les fonds sont bloqués jusqu'à confirmation de livraison.
- Une **vérification d'identité (KYC/CNI)** des utilisateurs, en particulier des transporteurs.

## 5. Périmètre géographique

Le périmètre visé par OnDuty couvre **l'ensemble du territoire camerounais**, sans restriction à un axe ou une région particulière. Cette couverture nationale est un choix assumé dès la conception (voir `13-architecture-technique.md` pour les implications techniques de ce choix : latence réseau en zones peu couvertes, mode dégradé, etc.).

## 6. Sources

- Digital Business Africa / Simiz — [Guide Paiement Mobile Cameroun 2026](https://simiz.io/blog/guide-paiement-mobile-cameroun-2026)
- Simiz — [Marché Paiement Mobile CEMAC 2026](https://simiz.io/blog/marche-paiement-mobile-cemac-2026)
- Cameroun24.net — [Mobile Money : quatorze ans après, le Cameroun tient sa révolution financière](https://cameroun24.net/index.php?id=71320&pg=actu&pp=1&ppg=1)
- PagesJaunes Cameroun — [Perspectives d'avenir pour le secteur logistique et transport au Cameroun à l'horizon 2030](https://www.pagesjaunes.online/blog/perspectives-d%E2%80%99avenir-pour-le-secteur-logistique-et-transport-au-cameroun-%C3%A0-l%E2%80%99horizon-2030)
- Banque mondiale — Rapport sur la facilitation du transport et du commerce (statistiques retours à vide, Congo/Cameroun)
- Cameroun24.net — [Corridor Douala-N'Djamena : le Cameroun numérise le fret](https://cameroun24.net/article/72926-corridor-doualandjamena-le-cameroun-numerise-le-fret-et-veut-en-finir-avec-l-asphyxie-logistique.html)
- Maligah — fiches agences United Express, Transcam, General Express Voyages, Touristique Express
