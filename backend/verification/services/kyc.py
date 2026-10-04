"""Orchestration de la vérification KYC, indépendante du fournisseur.

Fournisseur choisi par KYC_FOURNISSEUR dans le .env :
- "manuel" (défaut) : la vérification reste « en attente » et l'administrateur
  la traite depuis l'admin Django ;
- "smile" : la CNI et le selfie sont envoyés à Smile Identity, le résultat
  arrive par callback ou par `manage.py actualiser_kyc`.

Les documents véhicule restent toujours en validation manuelle.
"""

import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from ..models import Verification
from . import smile_identity

logger = logging.getLogger(__name__)


def soumettre(verification: Verification):
    """Transmet une nouvelle vérification au fournisseur actif.

    Lève une `ServiceExterneErreur` si le fournisseur est injoignable.
    """
    fournisseur = settings.KYC_FOURNISSEUR
    if fournisseur not in ("manuel", "smile"):
        logger.warning("KYC_FOURNISSEUR=%r inconnu : validation manuelle.", fournisseur)

    if fournisseur == "smile" and verification.type_verification == Verification.TypeVerification.CNI:
        verification.job_id_fournisseur = smile_identity.soumettre(verification)
        verification.fournisseur = Verification.Fournisseur.SMILE
        verification.motif = smile_identity.MOTIFS["a_revoir"]
    else:
        verification.fournisseur = Verification.Fournisseur.MANUEL
        verification.motif = "Vos documents seront examinés par notre équipe."
    verification.save(update_fields=["job_id_fournisseur", "fournisseur", "motif"])


def appliquer_resultat(verification_id: int, resultat: dict) -> bool:
    """Enregistre le résultat du fournisseur (callback ou job_status).

    Idempotent : un résultat n'est appliqué qu'une fois, sur une vérification
    encore en attente. Retourne True si la vérification a été mise à jour.
    """
    with transaction.atomic():
        verification = Verification.objects.select_for_update().get(pk=verification_id)
        if verification.statut != Verification.StatutVerification.EN_ATTENTE:
            return False
        statut, motif = smile_identity.interpreter(resultat)
        verification.statut = statut
        verification.motif = motif
        verification.resultat_brut = resultat
        if statut != Verification.StatutVerification.A_REVOIR:
            verification.date_traitement = timezone.now()
        verification.save(update_fields=["statut", "motif", "resultat_brut", "date_traitement"])

    logger.info("KYC %s : résultat %s (code %s)", verification.pk, statut, resultat.get("ResultCode"))
    _notifier(verification)
    return True


def actualiser(verification: Verification) -> bool:
    """Interroge le fournisseur pour une vérification Smile encore en attente."""
    if (
        verification.fournisseur != Verification.Fournisseur.SMILE
        or verification.statut != Verification.StatutVerification.EN_ATTENTE
        or not verification.job_id_fournisseur
    ):
        return False
    resultat = smile_identity.consulter_statut(verification)
    if resultat is None:
        return False
    return appliquer_resultat(verification.pk, resultat)


def _notifier(verification):
    """Notification du résultat ; un échec n'interrompt jamais le KYC."""
    from notification.models import Notification
    from notification.services.notifier import notifier

    notifier(
        verification.utilisateur,
        Notification.TypeNotification.KYC,
        "Vérification d'identité",
        verification.motif,
        verification_id=verification.pk,
        statut=verification.statut,
    )
