"""Détection d'objets via Google Cloud Vision (étape 1 du pipeline, doc 12).

Module isolé (BNF-16) : seul ce fichier connaît le SDK Google. Il reçoit des
images JPEG et retourne une liste d'étiquettes normalisées ; toute erreur du
fournisseur est traduite en exception de `onduty_backend.services_externes`.

Authentification : compte de service Google dont le chemin de la clé JSON est
donné par GOOGLE_APPLICATION_CREDENTIALS dans le .env (jamais dans le code).
"""

import logging
from pathlib import Path

from django.conf import settings

from onduty_backend.services_externes import (
    ReponseInvalide,
    ServiceIndisponible,
    ServiceNonConfigure,
    ServiceSature,
    ServiceTimeout,
)

logger = logging.getLogger(__name__)

SERVICE = "google_vision"
MAX_RESULTATS_PAR_IMAGE = 15

_client = None


def _obtenir_client():
    """Client Vision créé une seule fois par processus (connexion réutilisée)."""
    global _client
    if _client is not None:
        return _client

    chemin = settings.GOOGLE_APPLICATION_CREDENTIALS
    if not chemin:
        raise ServiceNonConfigure(SERVICE, "GOOGLE_APPLICATION_CREDENTIALS absent du .env")
    chemin = Path(chemin)
    if not chemin.is_absolute():
        chemin = Path(settings.BASE_DIR) / chemin
    if not chemin.is_file():
        raise ServiceNonConfigure(SERVICE, f"clé de compte de service introuvable : {chemin}")

    from google.cloud import vision

    try:
        _client = vision.ImageAnnotatorClient.from_service_account_file(str(chemin))
    except (ValueError, OSError) as exc:
        raise ServiceNonConfigure(SERVICE, f"clé de compte de service invalide : {exc}") from exc
    return _client


def analyser_images(images: list[bytes], timeout: float) -> dict:
    """Analyse les images et retourne les étiquettes détectées.

    Retour :
    {
        "etiquettes": [{"nom": "gun", "score": 0.93}, ...],  # score max sur toutes les images
        "nb_images_analysees": 5,
    }
    """
    from google.api_core import exceptions as gexc
    from google.auth import exceptions as auth_exc
    from google.cloud import vision

    client = _obtenir_client()
    fonctions = [
        vision.Feature(type_=vision.Feature.Type.LABEL_DETECTION, max_results=MAX_RESULTATS_PAR_IMAGE),
        vision.Feature(type_=vision.Feature.Type.OBJECT_LOCALIZATION, max_results=MAX_RESULTATS_PAR_IMAGE),
    ]
    requetes = [
        vision.AnnotateImageRequest(image=vision.Image(content=image), features=fonctions)
        for image in images
    ]

    try:
        # Un seul appel groupé pour toutes les images ; pas de nouvelle
        # tentative automatique du SDK, pour maîtriser le budget de 30 s.
        reponse = client.batch_annotate_images(requests=requetes, retry=None, timeout=timeout)
    except gexc.DeadlineExceeded as exc:
        raise ServiceTimeout(SERVICE, f"pas de réponse en {timeout:.0f} s") from exc
    except (gexc.Unauthenticated, gexc.PermissionDenied, auth_exc.GoogleAuthError) as exc:
        raise ServiceNonConfigure(SERVICE, f"authentification refusée : {exc}") from exc
    except gexc.ResourceExhausted as exc:
        raise ServiceSature(SERVICE, f"quota dépassé : {exc}") from exc
    except gexc.GoogleAPICallError as exc:
        raise ServiceIndisponible(SERVICE, str(exc)) from exc
    except Exception as exc:  # erreurs réseau bas niveau (gRPC, socket...)
        raise ServiceIndisponible(SERVICE, f"erreur inattendue : {exc!r}") from exc

    scores = {}
    nb_ok = 0
    for resultat in reponse.responses:
        if resultat.error.message:
            logger.warning("Vision : erreur sur une image : %s", resultat.error.message)
            continue
        nb_ok += 1
        for annotation in resultat.label_annotations:
            _garder_max(scores, annotation.description, annotation.score)
        for objet in resultat.localized_object_annotations:
            _garder_max(scores, objet.name, objet.score)

    if nb_ok == 0:
        raise ReponseInvalide(SERVICE, "aucune image n'a pu être analysée")

    etiquettes = sorted(
        ({"nom": nom, "score": round(score, 3)} for nom, score in scores.items()),
        key=lambda e: e["score"],
        reverse=True,
    )
    return {"etiquettes": etiquettes, "nb_images_analysees": nb_ok}


def _garder_max(scores: dict, nom: str, score: float):
    nom = nom.strip().lower()
    if nom and score > scores.get(nom, 0):
        scores[nom] = float(score)
