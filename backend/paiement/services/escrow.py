"""Logique métier du paiement sécurisé (escrow), indépendante des vues.

1. `initier` : le client demande à payer → CamPay lui envoie une demande de
   validation sur son téléphone (paiement « en attente »).
2. `appliquer_statut` / `actualiser` : CamPay confirme (webhook ou
   interrogation) → fonds bloqués en escrow, course « payée ».
3. `liberer` : réception confirmée → le prix est versé au transporteur.
   `rembourser` : course annulée → le prix est rendu au client.
   Commission et frais restent à OnDuty (décision du 04/10/2026).

Tout appel réseau est fait hors transaction ; un versement qui échoue est
conservé et peut être relancé par l'administrateur.
"""

import logging
import uuid
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from notification.models import Notification
from notification.services.notifier import notifier
from onduty_backend.services_externes import ServiceExterneErreur

from ..models import Paiement, Versement
from . import campay, tarification

logger = logging.getLogger(__name__)


class PaiementImpossible(Exception):
    """Action refusée pour une raison métier (message affichable)."""


def _reference(prefixe, pk):
    return f"onduty-{prefixe}{pk}-{uuid.uuid4().hex[:10]}"


def _fcfa(valeur):
    return f"{int(valeur):,}".replace(",", " ") + " FCFA"


# ---------------------------------------------------------------------------
# Encaissement
# ---------------------------------------------------------------------------

def devis(course) -> dict:
    return tarification.calculer(course.montant_convenu)


def initier(course, numero) -> Paiement:
    """Demande le paiement au client via CamPay.

    Lève PaiementImpossible, campay.NumeroInvalide, campay.PaiementRefuse ou
    ServiceExterneErreur (service indisponible → 503).
    """
    from course.models import Course

    if course.statut != Course.StatutCourse.EN_ATTENTE_PAIEMENT:
        raise PaiementImpossible("La course ne peut pas être payée dans son état actuel.")

    existant = Paiement.objects.filter(course=course).first()
    if existant and existant.statut == Paiement.StatutPaiement.EN_ATTENTE:
        raise PaiementImpossible(
            "Un paiement est déjà en attente de validation sur votre téléphone."
        )
    if existant and existant.statut != Paiement.StatutPaiement.ECHOUE:
        raise PaiementImpossible("Cette course est déjà payée.")

    numero = campay.normaliser_numero(numero)
    calcul = devis(course)
    reference = _reference("c", course.pk)
    reponse = campay.collecter(
        calcul["total"], numero, f"OnDuty - course #{course.pk}", reference
    )

    with transaction.atomic():
        paiement = Paiement.objects.select_for_update().filter(course=course).first()
        if paiement is None:
            paiement = Paiement(course=course)
        elif paiement.reference_campay:
            paiement.historique = paiement.historique + [{
                "reference_campay": paiement.reference_campay,
                "statut": paiement.statut,
                "message": paiement.message_erreur,
                "date": paiement.date_creation.isoformat() if paiement.date_creation else None,
            }]
        paiement.montant_course = calcul["montant_course"]
        paiement.commission = calcul["commission"]
        paiement.frais = calcul["frais"]
        paiement.montant = calcul["total"]
        paiement.numero_payeur = numero
        paiement.statut = Paiement.StatutPaiement.EN_ATTENTE
        paiement.reference_transaction = reference
        paiement.reference_campay = reponse["reference"]
        paiement.code_ussd = reponse.get("ussd_code") or ""
        paiement.methode = campay.operateur_vers_methode(reponse.get("operator"))
        paiement.message_erreur = ""
        paiement.save()
    logger.info("Paiement %s initié (CamPay %s)", paiement.pk, paiement.reference_campay)
    return paiement


def actualiser(paiement) -> bool:
    """Interroge CamPay pour un paiement en attente. True si son statut a changé."""
    if paiement.statut != Paiement.StatutPaiement.EN_ATTENTE or not paiement.reference_campay:
        return False
    return appliquer_statut(paiement.pk, campay.statut_transaction(paiement.reference_campay))


def appliquer_statut(paiement_id, donnees: dict) -> bool:
    """Applique le statut CamPay d'un encaissement (idempotent)."""
    from course.models import Course

    statut = donnees.get("status")
    if statut == campay.EN_ATTENTE:
        return False

    with transaction.atomic():
        paiement = Paiement.objects.select_for_update().select_related("course").get(pk=paiement_id)
        if paiement.statut != Paiement.StatutPaiement.EN_ATTENTE:
            return False
        course = Course.objects.select_for_update().get(pk=paiement.course_id)

        if statut == campay.SUCCES:
            montant_recu = donnees.get("amount")
            if montant_recu is not None and Decimal(str(montant_recu)) < paiement.montant:
                logger.error("Paiement %s : montant reçu %s < attendu %s", paiement.pk, montant_recu, paiement.montant)
                paiement.statut = Paiement.StatutPaiement.ECHOUE
                paiement.message_erreur = "Montant reçu inférieur au montant attendu."
                paiement.save(update_fields=["statut", "message_erreur"])
                return True
            paiement.statut = Paiement.StatutPaiement.BLOQUE_ESCROW
            paiement.date_paiement = timezone.now()
            paiement.methode = campay.operateur_vers_methode(donnees.get("operator")) or paiement.methode
            paiement.save(update_fields=["statut", "date_paiement", "methode"])
            course_annulee = course.statut == Course.StatutCourse.ANNULEE
            if not course_annulee:
                course.marquer_payee()
        else:
            paiement.statut = Paiement.StatutPaiement.ECHOUE
            paiement.message_erreur = donnees.get("reason") or "Paiement refusé ou non validé."
            paiement.save(update_fields=["statut", "message_erreur"])

    if statut == campay.SUCCES:
        if course_annulee:
            # Le client a annulé pendant que le paiement était en attente.
            rembourser(paiement)
        else:
            _notifier_paiement_recu(paiement, course)
    else:
        notifier(
            course.client, Notification.TypeNotification.PAIEMENT,
            "Paiement échoué",
            "Le paiement n'a pas abouti. Vous pouvez réessayer depuis la course.",
            course_id=course.pk,
        )
    return True


def _notifier_paiement_recu(paiement, course):
    notifier(
        course.client, Notification.TypeNotification.PAIEMENT,
        "Paiement effectué",
        f"Votre paiement de {_fcfa(paiement.montant)} est confirmé. Les fonds sont "
        "sécurisés jusqu'à la livraison.",
        course_id=course.pk,
    )
    notifier(
        course.transporteur, Notification.TypeNotification.PAIEMENT,
        "Course payée",
        f"La course #{course.pk} est payée ({_fcfa(paiement.montant_course)}). Vous "
        "recevrez l'argent une fois la livraison confirmée.",
        course_id=course.pk,
    )
    destinataire = course.demande.destinataire
    if destinataire and destinataire.pk != course.client_id:
        notifier(
            destinataire, Notification.TypeNotification.COURSE_STATUT,
            "Un colis vous est destiné",
            f"{course.client.prenom} {course.client.nom} vous envoie un colis "
            f"({course.demande.origine} → {course.demande.destination}). "
            "Vous pourrez confirmer sa réception dans l'application.",
            course_id=course.pk,
        )


# ---------------------------------------------------------------------------
# Sortie des fonds
# ---------------------------------------------------------------------------

def liberer(paiement) -> Versement | None:
    """Réception confirmée (ou décision admin) : prix versé au transporteur."""
    with transaction.atomic():
        paiement = Paiement.objects.select_for_update().select_related("course__transporteur").get(pk=paiement.pk)
        if paiement.statut != Paiement.StatutPaiement.BLOQUE_ESCROW:
            return None
        paiement.statut = Paiement.StatutPaiement.LIBERE
        paiement.date_liberation = timezone.now()
        paiement.save(update_fields=["statut", "date_liberation"])
        transporteur = paiement.course.transporteur
        versement = Versement.objects.create(
            paiement=paiement,
            type_versement=Versement.TypeVersement.TRANSPORTEUR,
            beneficiaire=transporteur,
            numero=transporteur.numero_versement,
            montant=paiement.montant_course,
            reference_externe=_reference("v", paiement.pk),
        )
    executer_versement(versement)
    return versement


def rembourser(paiement) -> Versement | None:
    """Course annulée (ou décision admin) : prix de la course rendu au client."""
    with transaction.atomic():
        paiement = Paiement.objects.select_for_update().select_related("course__client").get(pk=paiement.pk)
        if paiement.statut != Paiement.StatutPaiement.BLOQUE_ESCROW:
            return None
        paiement.statut = Paiement.StatutPaiement.REMBOURSE
        paiement.date_liberation = timezone.now()
        paiement.save(update_fields=["statut", "date_liberation"])
        client = paiement.course.client
        versement = Versement.objects.create(
            paiement=paiement,
            type_versement=Versement.TypeVersement.REMBOURSEMENT,
            beneficiaire=client,
            numero=client.numero_versement,
            montant=paiement.montant_course,
            reference_externe=_reference("r", paiement.pk),
        )
    executer_versement(versement)
    return versement


def executer_versement(versement) -> Versement:
    """Envoie l'argent via CamPay ; un échec est enregistré, jamais propagé."""
    versement.nb_tentatives += 1
    try:
        reponse = campay.envoyer(
            versement.montant,
            versement.numero,
            f"OnDuty - {versement.get_type_versement_display()} #{versement.paiement.course_id}",
            versement.reference_externe,
        )
    except (ServiceExterneErreur, campay.PaiementRefuse, campay.NumeroInvalide) as exc:
        logger.error("Versement %s échoué : %s", versement.pk, exc)
        versement.statut = Versement.StatutVersement.ECHOUE
        versement.message_erreur = str(exc)[:500]
        versement.save(update_fields=["statut", "message_erreur", "nb_tentatives"])
        return versement

    versement.reference_campay = reponse["reference"]
    versement.save(update_fields=["reference_campay", "nb_tentatives"])
    _appliquer_statut_versement(versement, reponse.get("status"), reponse.get("reason"))
    return versement


def actualiser_versement(versement) -> bool:
    if versement.statut != Versement.StatutVersement.EN_COURS or not versement.reference_campay:
        return False
    donnees = campay.statut_transaction(versement.reference_campay)
    return _appliquer_statut_versement(versement, donnees.get("status"), donnees.get("reason"))


def relancer_versement(versement) -> Versement:
    """Nouvel essai d'un versement échoué (action admin)."""
    if versement.statut != Versement.StatutVersement.ECHOUE:
        raise PaiementImpossible("Seul un versement échoué peut être relancé.")
    versement.statut = Versement.StatutVersement.EN_COURS
    versement.numero = versement.beneficiaire.numero_versement
    versement.reference_externe = _reference("v", versement.paiement_id)
    versement.reference_campay = ""
    versement.message_erreur = ""
    versement.save(update_fields=["statut", "numero", "reference_externe", "reference_campay", "message_erreur"])
    return executer_versement(versement)


def _appliquer_statut_versement(versement, statut, raison=None) -> bool:
    if statut == campay.SUCCES:
        versement.marquer_effectue()
        if versement.type_versement == Versement.TypeVersement.TRANSPORTEUR:
            titre, corps = "Paiement reçu", (
                f"{_fcfa(versement.montant)} ont été envoyés sur votre Mobile Money "
                f"pour la course #{versement.paiement.course_id}."
            )
        else:
            titre, corps = "Remboursement effectué", (
                f"{_fcfa(versement.montant)} vous ont été remboursés pour la course "
                f"#{versement.paiement.course_id}."
            )
        notifier(versement.beneficiaire, Notification.TypeNotification.PAIEMENT, titre, corps,
                 course_id=versement.paiement.course_id)
        return True
    if statut == campay.ECHEC:
        versement.statut = Versement.StatutVersement.ECHOUE
        versement.message_erreur = raison or "Versement refusé par l'opérateur."
        versement.save(update_fields=["statut", "message_erreur"])
        return True
    return False
