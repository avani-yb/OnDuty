"""Vérification d'identité via Smile Identity — Document Verification (job 6).

Module isolé (BNF-16) : seul ce fichier connaît Smile Identity. Les clés
(SMILE_PARTNER_ID, SMILE_API_KEY) viennent du .env, jamais du code.

Le SDK officiel `smile-id-core` effectue ses appels HTTP sans délai maximal.
On n'en réutilise donc que les fonctions locales (signature HMAC, archive zip)
et les trois appels réseau sont faits ici avec un timeout explicite :
1. POST {serveur}/upload      → URL d'envoi + SmileJobID
2. PUT  {url d'envoi}         → archive zip (info.json + images en base64)
3. POST {serveur}/job_status  → résultat (en secours du callback)

Le résultat arrive de façon asynchrone par callback (SMILE_CALLBACK_URL), ou
par interrogation de job_status (commande `actualiser_kyc`).
"""

import base64
import logging
import uuid

import requests
from django.conf import settings
from smile_id_core.constants import ImageTypes, JobType, sid_server_map
from smile_id_core.image_upload import generate_zip_file
from smile_id_core.Signature import Signature
from smile_id_core.Utilities import get_version

from onduty_backend.services_externes import (
    ReponseInvalide,
    ServiceIndisponible,
    ServiceNonConfigure,
    ServiceSature,
    ServiceTimeout,
)

logger = logging.getLogger(__name__)

SERVICE = "smile_identity"
PAYS = "CM"
TYPE_DOCUMENT = "IDENTITY_CARD"

# Codes de résultat Document Verification (documentation Smile ID).
# Règle prudente : seul un succès explicite valide, seuls les échecs explicites
# rejettent ; tout le reste (provisoire, revue en cours, code inconnu) part en
# revue manuelle par l'administrateur.
CODES_VALIDES = {"0810"}
CODES_REJETES = {"0811", "0813", "0816"}

MOTIFS = {
    "validee": "Votre identité a été vérifiée.",
    "rejetee": (
        "La vérification a échoué : document illisible, non pris en charge ou "
        "ne correspondant pas au selfie. Recommencez avec des photos nettes, "
        "bien éclairées et sans reflet."
    ),
    "a_revoir": "Votre dossier est en cours d'examen par notre équipe.",
}


def _config():
    if not settings.SMILE_PARTNER_ID or not settings.SMILE_API_KEY:
        raise ServiceNonConfigure(SERVICE, "SMILE_PARTNER_ID ou SMILE_API_KEY absent du .env")
    serveur = 1 if settings.SMILE_ENV == "production" else 0
    return settings.SMILE_PARTNER_ID, settings.SMILE_API_KEY, sid_server_map[serveur]


def _signature():
    partner_id, api_key, _ = _config()
    return dict(Signature(partner_id, api_key).generate_signature())


def signature_valide(timestamp, signature) -> bool:
    """Vérifie la signature d'un callback ou d'une réponse Smile Identity."""
    if not timestamp or not signature:
        return False
    partner_id, api_key, _ = _config()
    return Signature(partner_id, api_key).confirm_signature(str(timestamp), str(signature))


def _requete(methode, url, **kwargs):
    """Appel HTTP avec timeout ; erreurs traduites en erreurs internes."""
    try:
        reponse = requests.request(
            methode, url, timeout=settings.SMILE_TIMEOUT_SECONDS, **kwargs
        )
    except requests.Timeout as exc:
        raise ServiceTimeout(SERVICE, f"pas de réponse de {url}") from exc
    except requests.RequestException as exc:
        raise ServiceIndisponible(SERVICE, f"erreur réseau : {exc}") from exc

    if reponse.status_code in (401, 403):
        raise ServiceNonConfigure(SERVICE, f"accès refusé ({reponse.status_code}) : {reponse.text[:300]}")
    if reponse.status_code == 429:
        raise ServiceSature(SERVICE, "limite de débit atteinte")
    if reponse.status_code >= 500:
        raise ServiceIndisponible(SERVICE, f"erreur serveur {reponse.status_code}")
    if reponse.status_code >= 400:
        # Requête refusée : paramètres invalides (pays, type de document, callback...).
        raise ServiceNonConfigure(SERVICE, f"requête refusée ({reponse.status_code}) : {reponse.text[:300]}")
    return reponse


def _json(reponse):
    try:
        return reponse.json()
    except ValueError as exc:
        raise ReponseInvalide(SERVICE, f"réponse non JSON : {reponse.text[:200]}") from exc


def _base64(fichier):
    fichier.open("rb")
    try:
        return base64.b64encode(fichier.read()).decode()
    finally:
        fichier.close()


def soumettre(verification) -> str:
    """Envoie la CNI et le selfie à Smile Identity.

    Retourne le job_id OnDuty transmis (à conserver pour job_status).
    """
    partner_id, _, url = _config()
    job_id = f"onduty-{verification.pk}-{uuid.uuid4().hex[:8]}"
    partner_params = {
        "job_id": job_id,
        "user_id": f"onduty-user-{verification.utilisateur_id}",
        "job_type": int(JobType.DOCUMENT_VERIFICATION),
    }
    images = [
        {"image_type_id": int(ImageTypes.SELFIE_IMAGE_STRING), "image": _base64(verification.selfie)},
        {"image_type_id": int(ImageTypes.ID_CARD_IMAGE_STRING), "image": _base64(verification.cni_recto)},
    ]
    if verification.cni_verso:
        images.append(
            {"image_type_id": int(ImageTypes.ID_CARD_BACK_STRING), "image": _base64(verification.cni_verso)}
        )
    id_info = {"country": PAYS, "id_type": TYPE_DOCUMENT}
    signature = _signature()

    preparation = _json(_requete("POST", f"{url}/upload", json={
        "file_name": "selfie.zip",
        "smile_client_id": partner_id,
        "partner_params": partner_params,
        "model_parameters": {},
        "callback_url": settings.SMILE_CALLBACK_URL,
        "use_enrolled_image": False,
        "source_sdk": "Python",
        "source_sdk_version": get_version(),
        **signature,
    }))
    url_envoi = preparation.get("upload_url")
    if not url_envoi:
        raise ReponseInvalide(SERVICE, f"upload_url absent : {preparation}")

    archive = generate_zip_file(
        partner_id=partner_id,
        callback_url=settings.SMILE_CALLBACK_URL,
        upload_url=url_envoi,
        partner_params=partner_params,
        image_params=images,
        id_info_params=id_info,
        signature_params=signature,
    )
    _requete("PUT", url_envoi, data=archive, headers={"Content-type": "application/zip"})

    logger.info(
        "KYC %s soumise à Smile Identity (job %s, SmileJobID %s)",
        verification.pk, job_id, preparation.get("smile_job_id"),
    )
    return job_id


def consulter_statut(verification):
    """Interroge job_status ; retourne le résultat si le traitement est fini, sinon None."""
    partner_id, _, url = _config()
    reponse = _json(_requete("POST", f"{url}/job_status", json={
        **_signature(),
        "partner_id": partner_id,
        "job_id": verification.job_id_fournisseur,
        "user_id": f"onduty-user-{verification.utilisateur_id}",
        "image_links": False,
        "history": False,
    }))
    if not signature_valide(reponse.get("timestamp"), reponse.get("signature")):
        raise ReponseInvalide(SERVICE, "signature de la réponse job_status invalide")
    if not reponse.get("job_complete"):
        return None
    resultat = reponse.get("result")
    if not isinstance(resultat, dict):
        raise ReponseInvalide(SERVICE, f"résultat inattendu : {resultat!r:.200}")
    return resultat


def interpreter(resultat: dict):
    """Traduit un résultat Smile Identity en (statut, motif affichable)."""
    code = str(resultat.get("ResultCode", "")).strip()
    if code in CODES_VALIDES:
        statut = "validee"
    elif code in CODES_REJETES:
        statut = "rejetee"
    else:
        statut = "a_revoir"
    return statut, MOTIFS[statut]
