"""Règles métier des trajets qui touchent d'autres modules (courses, paiements)."""

import logging

from django.db import transaction

from notification.models import Notification
from notification.services.notifier import notifier

from .models import Trajet

logger = logging.getLogger(__name__)


def type_vehicule(transporteur):
    """Type du véhicule déclaré (camion, pick-up, voiture) ou None."""
    vehicule = getattr(transporteur, "informations_vehicule", None)
    return getattr(vehicule, "type_vehicule", None)


def supprimer(trajet: Trajet) -> int:
    """Suppression d'un trajet par son transporteur (décision du 04/10/2026).

    - toutes les courses non livrées et hors litige sont annulées ;
    - les clients ayant payé sont remboursés du prix de la course ;
    - chaque client est notifié, et sa demande redevient visible au matching ;
    - le transporteur perd 5 points de fiabilité par course annulée.

    Retourne le nombre de courses annulées.
    """
    from course.models import Course
    from evaluation.services.fiabilite import calculer_score_fiabilite
    from paiement.services import escrow

    with transaction.atomic():
        courses = list(
            trajet.courses.select_for_update()
            .select_related("client", "demande", "demande__destinataire")
            .exclude(statut__in=[
                Course.StatutCourse.ANNULEE,
                Course.StatutCourse.LIVREE,
                Course.StatutCourse.EN_LITIGE,
            ])
        )
        for course in courses:
            course.annuler(None, motif=Course.MotifAnnulation.SUPPRESSION_TRAJET)
        trajet.statut = Trajet.StatutTrajet.SUPPRIME
        trajet.save(update_fields=["statut"])

    for course in courses:
        paiement = getattr(course, "paiement", None)
        rembourse = paiement is not None and escrow.rembourser(paiement) is not None
        message = (
            f"Le transporteur a supprimé son trajet {trajet.origine} → {trajet.destination}. "
            f"Votre course #{course.pk} est annulée."
        )
        if rembourse:
            message += f" Le prix de la course ({int(paiement.montant_course)} FCFA) vous est remboursé."
        message += " Votre demande est de nouveau visible par les autres transporteurs."
        notifier(course.client, Notification.TypeNotification.COURSE_STATUT,
                 "Course annulée par le transporteur", message, course_id=course.pk)

    if courses:
        calculer_score_fiabilite(trajet.transporteur)
        logger.info("Trajet %s supprimé : %s course(s) annulée(s)", trajet.pk, len(courses))
    return len(courses)
