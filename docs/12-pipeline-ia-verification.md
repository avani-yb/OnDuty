# 12 — Pipeline IA de Vérification ("Douane Numérique")

## 1. Objectif du module

Ce module constitue le point de contrôle central de la confiance sur OnDuty. Chaque demande d'expédition doit passer par ce pipeline avant publication et mise en matching (cf. `04-besoins-fonctionnels.md`, BF-04 à BF-09). Il remplit trois fonctions distinctes :

1. **Détecter** les objets ou substances dont le transport est interdit ou fortement réglementé sur le territoire camerounais.
2. **Vérifier la cohérence** entre ce que le client déclare (description texte) et ce que la vidéo montre réellement.
3. **Prévenir la fraude par altération** et **informer le transporteur** des caractéristiques précises de l'objet qu'il va transporter.

## 2. Référentiel des objets/substances interdits ou sensibles

Cette liste sert de base de référence pour le paramétrage de la détection Vision API. Elle s'appuie sur la réglementation camerounaise applicable au transport et à la circulation de marchandises sur le territoire, et sera affinée au fil du projet.

### 2.1 Strictement interdits (rejet automatique, sans ambiguïté)
- Armes chimiques et substances assimilées.
- Stupéfiants et drogues illicites.
- Faux billets / fausse monnaie.
- Matériel pédopornographique.
- Explosifs, dynamite ou substances à usage destructeur assimilé.

### 2.2 Réglementés / soumis à autorisation (rejet par défaut, sauf preuve de conformité)
- Armes à feu et munitions (détention, port et acquisition soumis à autorisation préalable du ministère de l'Administration territoriale — Loi n°2016/015 du 14 décembre 2016) — leur transport via une plateforme grand public comme OnDuty est traité comme interdit par défaut, la vérification d'une autorisation légale sortant du périmètre du contrôle automatisé.
- Produits fauniques issus d'espèces protégées : ivoire, écailles de pangolin, peaux de félins protégés, trophées d'animaux sauvages — trafics activement combattus au Cameroun, avec des sanctions pouvant aller de 15 à 20 ans de prison depuis la loi sur les forêts et la faune de juillet 2024.
- Marchandises figurant sur la liste des produits prohibés à l'échelle nationale (classification douanière camerounaise, qui distingue produits libérés / produits sous autorisation / produits prohibés).

### 2.3 Sensibles (déclenchent une vigilance renforcée, pas nécessairement un rejet)
- Produits pharmaceutiques en grande quantité (risque de marché parallèle du médicament).
- Produits chimiques industriels non identifiés clairement.

**Note méthodologique :** cette liste n'est pas exhaustive et ne remplace pas un avis juridique. Elle sera révisée avec un point de vigilance particulier sur les catégories 2.1 et 2.2, qui sont les plus documentées et les plus consensuelles pour un rejet automatique. La catégorie 2.3 pourra évoluer vers une simple alerte admin plutôt qu'un rejet, selon les retours d'usage.

## 3. Architecture du pipeline

Le pipeline s'exécute de manière asynchrone (cf. `11-diagramme-communication.md`, section 2.3), en trois étapes séquentielles :

### Étape 1 — Détection d'objets/substances interdits (Vision API)

> **Décision (03/10/2026) :** faute de compte Google Cloud (carte bancaire exigée), la détection est assurée par défaut par **Groq**, dans le même appel que l'étape 2 (`IA_DETECTION=groq`). Google Cloud Vision reste intégré et s'ajoute à Groq avec `IA_DETECTION=google`. Limite connue de l'offre gratuite Groq : environ 1 contrôle par minute (7 000 jetons d'entrée par minute, ~1 300 jetons par image) — un palier payant sera nécessaire au-delà d'une démonstration.
- **Fournisseur principal :** Google Cloud Vision (alternative : Amazon Rekognition).
- **Entrée :** frames extraites de la vidéo soumise par le client.
- **Sortie :** liste d'objets/étiquettes détectés avec score de confiance.
- **Traitement :** comparaison des étiquettes détectées avec le référentiel (section 2). Si une correspondance dépasse un seuil de confiance défini, la demande est marquée "rejet potentiel — objet interdit".

### Étape 2 — Vérification de cohérence description ↔ image (Groq)

> **Décision (03/10/2026) :** Groq remplace GPT-4o mini prévu initialement. Groq expose une API compatible OpenAI et des modèles vision-langage (ex. Llama 4 Scout) ; le modèle exact est configuré par `GROQ_MODEL` dans le `.env`.
- **Entrée :** description texte du client + frames/vidéo.
- **Sortie :** verdict de cohérence (cohérent / incohérent) + extraction de détails visuels sur l'objet (marque, état, couleur, contenant — ex. "sac LVBOSHI vide, sans étiquette visible").
- **Traitement selon décision validée :**
  - Si **incohérence détectée** : **rejet automatique**, et le motif d'incohérence est communiqué au client (comportement confirmé : "le système rejette et signale l'incohérence au client").
  - Si **cohérent** : les détails extraits sont conservés pour être transmis au transporteur (voir section 5).

### Étape 3 — Détection d'altération suspecte
- **Objectif :** repérer des indices qu'un objet aurait été modifié pour dissimuler son contenu réel (emballage anormal, signes de manipulation récente, incohérence entre le poids déclaré et le volume apparent, etc.).
- **Mise en œuvre :** combinaison des sorties des étapes 1 et 2 plutôt qu'un modèle dédié séparé dans une première version — un signal d'altération peut découler d'une incohérence entre étiquettes visuelles détectées et description, ou d'un objet dont l'apparence ne correspond pas à un état "neuf/scellé" alors que le client le déclare comme tel.
- **Évolution possible :** un modèle spécialisé pourra être entraîné ultérieurement si ce signal s'avère insuffisant en pratique.

### Étape 4 — Verdict global et publication
- Le backend agrège les résultats des trois étapes en un verdict final : **validé** ou **rejeté** (avec motif précis : objet interdit / incohérence / altération suspecte).
- Le verdict doit être disponible en 30 secondes maximum au total (BNF-04).

## 4. Vérification d'identité (KYC/CNI)

- **Fournisseur principal :** Smile Identity.
- **Entrée :** photo/scan de la CNI + éventuellement un selfie de vérification (liveness check, si le forfait Smile Identity choisi l'inclut).
- **Sortie :** statut de vérification (validée / rejetée / à revoir manuellement).
- **Traitement asynchrone** (cf. fichier 11) — pas de contrainte de délai aussi stricte que le contrôle de demande (30 secondes), car le KYC est réalisé en amont, lors de l'inscription ou de l'activation du rôle transporteur, pas dans le flux temps-réel d'une expédition.
- **Historisation :** chaque tentative est enregistrée dans l'entité `Verification` (cf. `10-diagramme-classes.md`), permettant de gérer plusieurs essais en cas d'échec (photo floue, document illisible, etc.).

## 5. Transmission des détails au transporteur

Conformément à ta décision, les détails extraits par l'IA sur l'objet (ex. "sac LVBOSHI vide, sans étiquette") sont visibles par le transporteur à **deux moments** :
1. **Avant acceptation** : dans la fiche de la demande présentée au moment du matching, pour lui permettre de juger de la nature de ce qu'il transportera avant de s'engager.
2. **Après acceptation** : à nouveau accessible dans le détail de la course, pour lui servir de repère concret au moment de la prise en charge effective (ex. reconnaître le bon sac/colis parmi plusieurs).

Cette transparence descendante (IA → transporteur) est un mécanisme de prévention de la fraude à la substitution : si l'objet remis physiquement ne correspond pas à ce que l'IA a validé et décrit, le transporteur dispose d'un référentiel objectif pour refuser la prise en charge ou signaler un incident (cf. `06-fonctionnalites-detaillees.md`, section 7).

## 6. Alternatives en cas de coût ou d'indisponibilité des API

Conformément à ton souhait de prévoir un plan B pour chaque API payante, voici les alternatives identifiées :

| Fonction | API principale | Alternative open-source |
|---|---|---|
| Détection d'objets/substances interdits | Google Cloud Vision / Amazon Rekognition | Modèle de détection d'objets fine-tuné (ex. YOLOv8) entraîné sur un jeu de données ciblé (armes, substances, produits fauniques) |
| Vérification de cohérence description/image | Groq (initialement GPT-4o mini) | Modèle vision-langage open-source (ex. LLaVA) auto-hébergé |
| KYC/CNI | Smile Identity | Pipeline OCR (Tesseract/EasyOCR) + règles de cohérence manuelles (format CNI camerounaise, champs attendus) + validation manuelle admin en fallback |

Ce choix d'architecture (interfaces isolées par fournisseur, cf. BNF-16 dans `05-besoins-non-fonctionnels.md`) permet de basculer vers ces alternatives sans réécrire la logique métier du pipeline.

## 7. Sources (référentiel légal)

- Loi n° 2016/015 du 14 décembre 2016 portant régime général des armes et munitions au Cameroun.
- Loi n° 2016/004 du 18 avril 2016 régissant le commerce extérieur au Cameroun (article 9 : interdictions strictes).
- Loi camerounaise sur les forêts et la faune (juillet 2024) — renforcement des sanctions sur le trafic d'espèces protégées.
- Classification douanière camerounaise (produits libérés / sous autorisation / prohibés) — Organisme de recherche et d'information sur la logistique et le transport (logistiqueconseil.org).
- LeFisk — [Importation Cameroun 2026 : produits interdits](https://www.lefisk.cm/blog/procedure-importation-marchandises-cameroun-dedouanement-sgs-anor)
- KOACI — [Trafic d'espèces protégées, saisies d'ivoire et de pangolin](https://www.koaci.com/article/2025/02/26/cameroun/societe/cameroun-trafic-despeces-protegees-saisie-record-en-france-de-17-kg-de-pangolin-en-provenance-du-cameroun_184800.html)
