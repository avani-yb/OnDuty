"""Arbitrage des litiges par l'administrateur (doc 06 §8, séquence doc 08 §4).

Deux décisions possibles :
- livraison validée : la course est terminée et le prix est versé au
  transporteur ;
- course annulée : le prix de la course est remboursé au client.
Les deux parties sont notifiées. Utilisé par le site /gestion/ et l'admin Django.
"""

import logging

from django.db import transaction
from django.utils import timezone

from .models import Litige

logger = logging.getLogger(__name__)

STATUTS_OUVERTS = (Litige.StatutLitige.OUVERT, Litige.StatutLitige.EN_COURS_ANALYSE)

DECISION_VALIDATION = "Livraison validée : le prix de la course est versé au transporteur."
DECISION_REMBOURSEMENT = "Course annulée : le prix de la course est remboursé au client."


class ArbitrageImpossible(Exception):
    """Décision refusée (litige déjà résolu, etc.) ; message affichable."""


def prendre_en_charge(litige, admin):
    if litige.statut != Litige.StatutLitige.OUVERT:
        raise ArbitrageImpossible("Ce litige n'est plus ouvert.")
    litige.statut = Litige.StatutLitige.EN_COURS_ANALYSE
    litige.save(update_fields=["statut"])
    logger.info("Admin %s prend en charge le litige %s", admin.pk, litige.pk)


def _clore(litige, admin, decision, commentaire):
    texte = decision + (f" Commentaire : {commentaire.strip()}" if commentaire and commentaire.strip() else "")
    litige.statut = Litige.StatutLitige.RESOLU
    litige.decision_admin = texte
    litige.date_resolution = timezone.now()
    litige.save(update_fields=["statut", "decision_admin", "date_resolution"])
    logger.info("Admin %s résout le litige %s : %s", admin.pk, litige.pk, texte)

    from notification.models import Notification
    from notification.services.notifier import notifier

    course = litige.course
    for personne in (course.client, course.transporteur):
        notifier(personne, Notification.TypeNotification.LITIGE, "Litige résolu",
                 f"Course #{course.pk} : {texte}", course_id=course.pk)


def valider_livraison(litige, admin, commentaire=""):
    """Le transporteur a fait son travail : course livrée, prix versé."""
    from course.models import Course
    from paiement.services import escrow

    if litige.statut not in STATUTS_OUVERTS:
        raise ArbitrageImpossible("Ce litige est déjà résolu.")
    with transaction.atomic():
        course = Course.objects.select_for_update().get(pk=litige.course_id)
        if course.statut == Course.StatutCourse.ANNULEE:
            raise ArbitrageImpossible("La course est annulée : la livraison ne peut plus être validée.")
        course.statut = Course.StatutCourse.LIVREE
        course.date_livraison = course.date_livraison or timezone.now()
        course.save(update_fields=["statut", "date_livraison"])
    paiement = getattr(course, "paiement", None)
    if paiement is not None:
        escrow.liberer(paiement)
    _clore(litige, admin, DECISION_VALIDATION, commentaire)


def rembourser_client(litige, admin, commentaire=""):
    """La course n'a pas été assurée : annulation et remboursement du prix."""
    from course.models import Course
    from paiement.services import escrow

    if litige.statut not in STATUTS_OUVERTS:
        raise ArbitrageImpossible("Ce litige est déjà résolu.")
    with transaction.atomic():
        course = Course.objects.select_for_update().get(pk=litige.course_id)
        if course.statut == Course.StatutCourse.LIVREE and hasattr(course, "paiement") \
                and course.paiement.statut == "libere":
            raise ArbitrageImpossible("Le prix a déjà été versé au transporteur : remboursement impossible.")
        course.statut = Course.StatutCourse.ANNULEE
        course.motif_annulation = Course.MotifAnnulation.ADMIN
        course.save(update_fields=["statut", "motif_annulation"])
    paiement = getattr(course, "paiement", None)
    if paiement is not None:
        escrow.rembourser(paiement)
    _clore(litige, admin, DECISION_REMBOURSEMENT, commentaire)
