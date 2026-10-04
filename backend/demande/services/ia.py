"""Pipeline de contrôle IA des colis.

Le contrôle s'exécute en trois étapes (cf. `12-pipeline-ia-verification.md`,
section 3) puis produit un verdict global : validé ou rejeté (avec motif).

L'architecture isole le pipeline métier du fournisseur réel via une interface
(`ControleurIA`), conformément au besoin BNF-16 (interfaces isolées par
fournisseur) : on peut changer de fournisseur (Groq, Google Cloud Vision ou
une alternative open-source) sans réécrire la logique métier.

Deux fournisseurs, choisis par IA_FOURNISSEUR dans le .env :
- `SimulationControleurIA` ("simulation", défaut) : déterministe, sans clé
  API, basé sur un référentiel de mots-clés appliqué à la description. Sert au
  développement et aux tests.
- `ControleurIAReel` ("reel") : mots-clés + analyse d'images extraites de la
  vidéo par Groq (détection, cohérence, altération, détails visuels). Google
  Cloud Vision peut s'ajouter pour la détection (IA_DETECTION=google).

Le contrôle s'exécute pendant la requête, dans un budget de IA_BUDGET_SECONDES
(BNF-04). Si un service tiers échoue, une `ServiceExterneErreur` remonte : la
vue renvoie alors une erreur 503 et la demande reste « en cours de contrôle ».
"""

import logging
import time

from django.conf import settings

from onduty_backend.services_externes import ServiceTimeout

from ..models import ControleIA, Demande

logger = logging.getLogger(__name__)


# Référentiel d'objets/substances (simplification d'un jeu de données réel).
# Catégorie "interdit" → rejet automatique (doc 12, 2.1 et 2.2 par défaut).
REFERENTIEL = {
    "interdit": [
        "arme", "armes", "munitions", "munition", "explosif", "explosifs",
        "dynamite", "drogue", "drogues", "stupéfiant", "stupéfiants",
        "cocaïne", "ivoire", "pangolin", "faux billet", "faux billets",
        "fausse monnaie",
    ],
    "sensible": [
        "médicament", "médicaments", "produit chimique", "produits chimiques",
    ],
}


# Étiquettes Google Vision (en anglais, minuscules) correspondant au
# référentiel ci-dessus. Correspondance exacte sur le nom de l'étiquette.
REFERENTIEL_VISION = {
    "interdit": [
        "gun", "firearm", "handgun", "revolver", "rifle", "shotgun",
        "machine gun", "assault rifle", "weapon", "ammunition", "bullet",
        "cartridge", "explosive", "explosive weapon", "grenade", "bomb",
        "dynamite", "cannabis", "hemp", "marijuana", "cocaine", "narcotic",
        "ivory", "tusk", "pangolin",
    ],
    "sensible": [
        "knife", "medicine", "pill", "pharmaceutical drug", "syringe",
        "chemical", "banknote", "cash",
    ],
}


class ControleurIA:
    """Interface commune des fournisseurs de contrôle IA."""

    def executer(self, demande: Demande) -> dict:
        """Exécute le contrôle et retourne un dict structuré :
        {
            "detection_objets": {...},
            "coherence": {...},
            "verdict": "valide" | "rejete",
            "motif_rejet": str | None,
        }
        """
        raise NotImplementedError


class SimulationControleurIA(ControleurIA):
    """Fournisseur de simulation (déterministe, sans API externe)."""

    def _detecter_objets(self, description):
        objets_detectes = []
        rejet = None
        texte = description.lower()
        for categorie, mots in REFERENTIEL.items():
            for mot in mots:
                if mot in texte:
                    objets_detectes.append(
                        {"objet": mot, "categorie": categorie, "confiance": 0.99}
                    )
        # Règle : tout objet « interdit » détecté entraîne un rejet automatique.
        interdits = [o for o in objets_detectes if o["categorie"] == "interdit"]
        if interdits:
            rejet = (
                "Objet interdit ou réglementé détecté : "
                + ", ".join(o["objet"] for o in interdits)
                + "."
            )
        return {"objets_detectes": objets_detectes, "rejet": rejet}

    def _verifier_coherence(self, demande):
        # Simulation : la description est jugée cohérente dès lors qu'aucun
        # objet interdit n'est signalé. Un fournisseur réel (GPT) comparerait
        # réellement la description à la vidéo.
        return {
            "verdict_coherence": "coherent",
            "détails_visuels": None,
        }

    def _detecter_alteration(self, detection, description):
        # Heuristique : certains mots évoquent un emballage suspect/altéré.
        mots_alteration = ["emballage anormal", "état anormal", "scellé anormal"]
        texte = description.lower()
        if any(m in texte for m in mots_alteration):
            return "Altération suspecte détectée (emballage/état anormal)."
        return None

    def executer(self, demande: Demande):
        debut = time.time()

        detection = self._detecter_objets(demande.description)
        coherence = self._verifier_coherence(demande)
        motif_altération = self._detecter_alteration(detection, demande.description)

        # Verdict global : rejet si objet interdit ou altération suspecte.
        if detection["rejet"]:
            verdict = ControleIA.Verdict.REJETE
            motif = detection["rejet"]
        elif motif_altération:
            verdict = ControleIA.Verdict.REJETE
            motif = motif_altération
        else:
            verdict = ControleIA.Verdict.VALIDE
            motif = None

        return {
            "detection_objets": detection,
            "coherence": coherence,
            "verdict": verdict,
            "motif_rejet": motif,
            "duree_traitement_secondes": time.time() - debut,
        }


class ControleurIAReel(SimulationControleurIA):
    """Fournisseur réel : mots-clés sur la description + Google Cloud Vision.

    Les règles déterministes de la simulation (mots-clés, altération) restent
    appliquées : elles sont gratuites et complètent la détection visuelle.
    """

    MOTIF_VIDEO_ILLISIBLE = (
        "La vidéo est illisible ou absente. Merci de filmer à nouveau "
        "l'article et de relancer le contrôle."
    )

    def executer(self, demande: Demande):
        from . import analyse_groq, vision_google
        from .frames import VideoIllisible, extraire_images

        debut = time.monotonic()
        detection = self._detecter_objets(demande.description)

        # Étape 1 — images extraites de la vidéo, analysées par Vision.
        try:
            if not demande.video:
                raise VideoIllisible("aucun fichier vidéo")
            images = extraire_images(demande.video.path, settings.IA_NB_IMAGES)
        except VideoIllisible as exc:
            logger.info("Demande %s : vidéo illisible (%s)", demande.pk, exc)
            return self._resultat(
                detection, None, ControleIA.Verdict.REJETE,
                self.MOTIF_VIDEO_ILLISIBLE, debut,
            )

        detection["nb_images_analysees"] = len(images)

        # Étape 1 (option) — Google Cloud Vision, si activé.
        etiquettes_vision = None
        if settings.IA_DETECTION == "google":
            vision = vision_google.analyser_images(
                images, timeout=self._temps_restant(debut, settings.VISION_TIMEOUT_SECONDS)
            )
            etiquettes_vision = vision["etiquettes"]
            detection["etiquettes_vision"] = etiquettes_vision[:30]
            self._comparer_referentiel_vision(detection, etiquettes_vision)

        # Étapes 1 à 3 — Groq : objets, cohérence, altération, détails visuels.
        analyse = analyse_groq.analyser(
            images,
            demande.description,
            timeout=self._temps_restant(debut, settings.GROQ_TIMEOUT_SECONDS),
            etiquettes_vision=etiquettes_vision,
        )
        self._appliquer_objets_groq(detection, analyse["objets_detectes"])
        coherence = {
            "verdict_coherence": "coherent" if analyse["coherent"] else "incoherent",
            "motif_incoherence": analyse["motif_incoherence"],
            "alteration_suspecte": analyse["alteration_suspecte"],
            "motif_alteration": analyse["motif_alteration"],
            "détails_visuels": analyse["details_visuels"],
            "modele": settings.GROQ_MODEL,
        }

        motif_alteration = self._detecter_alteration(detection, demande.description)
        if not motif_alteration and analyse["alteration_suspecte"]:
            motif_alteration = "Altération suspecte de l'emballage" + (
                f" : {analyse['motif_alteration']}" if analyse["motif_alteration"] else "."
            )

        # Verdict : objet interdit, puis incohérence, puis altération (doc 12).
        if detection["rejet"]:
            verdict, motif = ControleIA.Verdict.REJETE, detection["rejet"]
        elif not analyse["coherent"]:
            verdict = ControleIA.Verdict.REJETE
            motif = "La vidéo ne correspond pas à la description" + (
                f" : {analyse['motif_incoherence']}" if analyse["motif_incoherence"] else "."
            )
        elif motif_alteration:
            verdict, motif = ControleIA.Verdict.REJETE, motif_alteration
        else:
            verdict, motif = ControleIA.Verdict.VALIDE, None
        return self._resultat(detection, coherence, verdict, motif, debut)

    def _comparer_referentiel_vision(self, detection, etiquettes):
        seuil = settings.VISION_SEUIL_CONFIANCE
        interdits = []
        for etiquette in etiquettes:
            if etiquette["score"] < seuil:
                continue
            for categorie, noms in REFERENTIEL_VISION.items():
                if etiquette["nom"] in noms:
                    detection["objets_detectes"].append({
                        "objet": etiquette["nom"],
                        "categorie": categorie,
                        "confiance": etiquette["score"],
                        "source": "vision",
                    })
                    if categorie == "interdit":
                        interdits.append(etiquette["nom"])
        if interdits and not detection["rejet"]:
            detection["rejet"] = (
                "Objet interdit ou réglementé détecté sur la vidéo : "
                + ", ".join(interdits) + "."
            )

    def _appliquer_objets_groq(self, detection, objets):
        seuil = settings.GROQ_SEUIL_CONFIANCE
        interdits = []
        for objet in objets:
            if objet["categorie"] == "autorise":
                continue
            detection["objets_detectes"].append({**objet, "source": "groq"})
            if objet["categorie"] == "interdit" and objet["confiance"] >= seuil:
                interdits.append(objet["objet"])
        if interdits and not detection["rejet"]:
            detection["rejet"] = (
                "Objet interdit ou réglementé détecté sur la vidéo : "
                + ", ".join(interdits) + "."
            )

    @staticmethod
    def _temps_restant(debut, plafond):
        """Timeout à accorder au prochain appel, dans le budget global."""
        restant = settings.IA_BUDGET_SECONDES - (time.monotonic() - debut)
        if restant < 2:
            raise ServiceTimeout("controle_ia", "budget de temps épuisé")
        return min(plafond, restant)

    @staticmethod
    def _resultat(detection, coherence, verdict, motif, debut):
        return {
            "detection_objets": detection,
            "coherence": coherence,
            "verdict": verdict,
            "motif_rejet": motif,
            "duree_traitement_secondes": round(time.monotonic() - debut, 2),
        }


def obtenir_controleur() -> ControleurIA:
    """Retourne le fournisseur de contrôle actif (IA_FOURNISSEUR du .env)."""
    if settings.IA_FOURNISSEUR == "reel":
        return ControleurIAReel()
    if settings.IA_FOURNISSEUR != "simulation":
        logger.warning(
            "IA_FOURNISSEUR=%r inconnu : utilisation de la simulation.",
            settings.IA_FOURNISSEUR,
        )
    return SimulationControleurIA()
