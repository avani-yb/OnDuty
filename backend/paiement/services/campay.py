"""Client de l'API CamPay (paiements MTN MoMo / Orange Money au Cameroun).

Module isolé (BNF-16) : seul ce fichier connaît CamPay. Identifiants dans le
.env uniquement (CAMPAY_USERNAME, CAMPAY_PASSWORD, CAMPAY_WEBHOOK_KEY).

Le SDK Python officiel n'est pas utilisé : il désactive la vérification du
certificat HTTPS (verify=False), n'a pas de délai maximal et attend la fin
du paiement dans une boucle sans fin. Les appels sont donc faits ici :
- POST /api/token/               → jeton temporaire (mis en cache)
- POST /api/collect/             → demande de paiement au client
- GET  /api/transaction/{ref}/   → statut d'une transaction
- POST /api/withdraw/            → envoi d'argent (transporteur, remboursement)
"""

import logging
import re

import jwt
import requests
from django.conf import settings
from django.core.cache import cache

from onduty_backend.services_externes import (
    ReponseInvalide,
    ServiceIndisponible,
    ServiceNonConfigure,
    ServiceSature,
    ServiceTimeout,
)

logger = logging.getLogger(__name__)

SERVICE = "campay"
URLS = {
    "demo": "https://demo.campay.net/api",
    "production": "https://www.campay.net/api",
}
CLE_CACHE_JETON = "campay:jeton"

SUCCES = "SUCCESSFUL"
ECHEC = "FAILED"
EN_ATTENTE = "PENDING"


class PaiementRefuse(Exception):
    """CamPay refuse l'opération (raison affichable, ex. numéro non Mobile Money)."""


class NumeroInvalide(ValueError):
    """Numéro de téléphone qui n'est pas un numéro mobile camerounais."""


def normaliser_numero(numero: str) -> str:
    """Retourne le numéro au format CamPay : 237 + 9 chiffres commençant par 6."""
    chiffres = re.sub(r"\D", "", numero or "")
    if chiffres.startswith("00237"):
        chiffres = chiffres[2:]
    if len(chiffres) == 9:
        chiffres = "237" + chiffres
    if not re.fullmatch(r"2376\d{8}", chiffres):
        raise NumeroInvalide(
            "Numéro Mobile Money invalide : 9 chiffres commençant par 6 (ex. 6XXXXXXXX)."
        )
    return chiffres


def _url():
    if not settings.CAMPAY_USERNAME or not settings.CAMPAY_PASSWORD:
        raise ServiceNonConfigure(SERVICE, "CAMPAY_USERNAME ou CAMPAY_PASSWORD absent du .env")
    return URLS["production" if settings.CAMPAY_ENV == "production" else "demo"]


def _requete(methode, chemin, avec_jeton=True, **kwargs):
    url = f"{_url()}{chemin}"
    entetes = {"Content-Type": "application/json"}
    if avec_jeton:
        entetes["Authorization"] = f"Token {_jeton()}"
    try:
        reponse = requests.request(
            methode, url, headers=entetes, timeout=settings.CAMPAY_TIMEOUT_SECONDS, **kwargs
        )
    except requests.Timeout as exc:
        raise ServiceTimeout(SERVICE, f"pas de réponse de {chemin}") from exc
    except requests.RequestException as exc:
        raise ServiceIndisponible(SERVICE, f"erreur réseau : {exc}") from exc

    if reponse.status_code == 401 and avec_jeton:
        cache.delete(CLE_CACHE_JETON)  # jeton expiré : redemandé au prochain appel
        raise ServiceIndisponible(SERVICE, "jeton refusé, réessayer")
    if reponse.status_code in (401, 403):
        raise ServiceNonConfigure(SERVICE, f"accès refusé ({reponse.status_code}) : {reponse.text[:300]}")
    if reponse.status_code == 429:
        raise ServiceSature(SERVICE, "limite de débit atteinte")
    if reponse.status_code >= 500:
        raise ServiceIndisponible(SERVICE, f"erreur serveur {reponse.status_code}")

    try:
        donnees = reponse.json()
    except ValueError as exc:
        raise ReponseInvalide(SERVICE, f"réponse non JSON : {reponse.text[:200]}") from exc
    if reponse.status_code >= 400:
        # Refus métier (numéro invalide, montant hors limites, solde insuffisant...)
        raise PaiementRefuse(donnees.get("message") or str(donnees)[:300])
    return donnees


def _jeton():
    jeton = cache.get(CLE_CACHE_JETON)
    if jeton:
        return jeton
    donnees = _requete(
        "POST",
        "/token/",
        avec_jeton=False,
        json={"username": settings.CAMPAY_USERNAME, "password": settings.CAMPAY_PASSWORD},
    )
    jeton = donnees.get("token")
    if not jeton:
        raise ReponseInvalide(SERVICE, "jeton absent de la réponse /token/")
    duree = int(donnees.get("expires_in") or 3600)
    cache.set(CLE_CACHE_JETON, jeton, max(60, duree - 60))
    return jeton


def collecter(montant, numero, description, reference_externe) -> dict:
    """Demande au client de valider le paiement sur son téléphone.

    Retourne {"reference", "ussd_code", "operator"}.
    """
    donnees = _requete("POST", "/collect/", json={
        "amount": str(int(montant)),
        "currency": "XAF",
        "from": normaliser_numero(numero),
        "description": description[:100],
        "external_reference": reference_externe,
    })
    if not donnees.get("reference"):
        raise ReponseInvalide(SERVICE, f"référence absente : {donnees}")
    return donnees


def statut_transaction(reference) -> dict:
    """Statut d'une transaction : status = PENDING | SUCCESSFUL | FAILED."""
    donnees = _requete("GET", f"/transaction/{reference}/")
    if donnees.get("status") not in (SUCCES, ECHEC, EN_ATTENTE):
        raise ReponseInvalide(SERVICE, f"statut inattendu : {donnees}")
    return donnees


def envoyer(montant, numero, description, reference_externe) -> dict:
    """Envoie de l'argent sur un numéro Mobile Money. Retourne {"reference", "status"}."""
    donnees = _requete("POST", "/withdraw/", json={
        "amount": str(int(montant)),
        "currency": "XAF",
        "to": normaliser_numero(numero),
        "description": description[:100],
        "external_reference": reference_externe,
    })
    if not donnees.get("reference"):
        raise ReponseInvalide(SERVICE, f"référence absente : {donnees}")
    return donnees


def signature_webhook_valide(signature) -> bool:
    """Vérifie la signature (JWT HS256) envoyée par CamPay avec le webhook.

    Le statut n'est de toute façon jamais pris tel quel : il est toujours
    revérifié auprès de l'API (`statut_transaction`).
    """
    if not settings.CAMPAY_WEBHOOK_KEY or not signature:
        return False
    try:
        jwt.decode(signature, settings.CAMPAY_WEBHOOK_KEY, algorithms=["HS256"])
    except jwt.PyJWTError:
        return False
    return True


def operateur_vers_methode(operateur: str) -> str:
    operateur = (operateur or "").upper()
    if "MTN" in operateur:
        return "mtn_momo"
    if "ORANGE" in operateur:
        return "orange_money"
    return ""
