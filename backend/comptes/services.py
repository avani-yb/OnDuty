"""Gestion des comptes par l'administrateur : blocage et suppression.

Un compte bloqué est aussi désactivé (`is_active=False`) : la connexion et
toutes les requêtes avec un jeton déjà émis sont refusées immédiatement.

Suppression (décision du 07/10/2026) :
- sans aucune activité : suppression réelle ;
- avec un historique (demandes, trajets, courses, paiements, KYC, litiges) :
  le compte est fermé et anonymisé, l'historique est conservé (audit,
  registre financier — doc 14, section 5) ;
- une course en cours bloque la suppression.
"""

import logging

from django.db import transaction
from django.db.models import Q

from .models import Utilisateur

logger = logging.getLogger(__name__)


class ActionCompteImpossible(Exception):
    """Action refusée ; message affichable."""


def bloquer(utilisateur, admin):
    if utilisateur.est_admin:
        raise ActionCompteImpossible("Un compte administrateur ne peut pas être bloqué.")
    utilisateur.statut_compte = Utilisateur.StatutCompte.SUSPENDU
    utilisateur.is_active = False
    utilisateur.save(update_fields=["statut_compte", "is_active"])
    _oublier_appareils(utilisateur)
    logger.info("Admin %s bloque le compte %s", admin.pk, utilisateur.pk)


def debloquer(utilisateur, admin):
    if utilisateur.telephone.startswith("supprime-"):
        raise ActionCompteImpossible("Ce compte a été supprimé : il ne peut pas être débloqué.")
    utilisateur.statut_compte = Utilisateur.StatutCompte.ACTIF
    utilisateur.is_active = True
    utilisateur.save(update_fields=["statut_compte", "is_active"])
    logger.info("Admin %s débloque le compte %s", admin.pk, utilisateur.pk)


def _oublier_appareils(utilisateur):
    from notification.models import FCMToken

    FCMToken.objects.filter(utilisateur=utilisateur).update(actif=False)


def courses_en_cours(utilisateur):
    from course.models import Course

    return Course.objects.filter(
        Q(client=utilisateur) | Q(transporteur=utilisateur)
    ).exclude(statut__in=[Course.StatutCourse.LIVREE, Course.StatutCourse.ANNULEE])


def a_un_historique(utilisateur):
    from course.models import Course

    return any((
        Course.objects.filter(Q(client=utilisateur) | Q(transporteur=utilisateur)).exists(),
        utilisateur.demandes.exists(),
        utilisateur.trajets.exists(),
        utilisateur.verifications.exists(),
        utilisateur.litiges_declares.exists(),
    ))


def supprimer(utilisateur, admin):
    """Supprime ou anonymise le compte. Retourne "supprime" ou "anonymise"."""
    if utilisateur.est_admin:
        raise ActionCompteImpossible("Un compte administrateur ne peut pas être supprimé.")
    if courses_en_cours(utilisateur).exists():
        raise ActionCompteImpossible(
            "Ce compte a une course en cours : attendez sa fin ou son annulation avant de le supprimer."
        )

    if not a_un_historique(utilisateur):
        pk = utilisateur.pk
        utilisateur.delete()
        logger.info("Admin %s supprime le compte %s (sans historique)", admin.pk, pk)
        return "supprime"

    from demande.models import Demande
    from trajet.models import Trajet

    with transaction.atomic():
        # Plus rien de visible des autres utilisateurs.
        utilisateur.demandes.exclude(statut=Demande.StatutDemande.SUPPRIMEE).update(
            statut=Demande.StatutDemande.SUPPRIMEE
        )
        utilisateur.trajets.filter(statut=Trajet.StatutTrajet.ACTIF).update(statut=Trajet.StatutTrajet.SUPPRIME)
        Demande.objects.filter(destinataire=utilisateur).update(destinataire=None)

        if utilisateur.photo_profil:
            utilisateur.photo_profil.delete(save=False)
        utilisateur.nom = "supprimé"
        utilisateur.prenom = "Utilisateur"
        utilisateur.telephone = f"supprime-{utilisateur.pk}"
        utilisateur.email = ""
        utilisateur.numero_mobile_money = ""
        utilisateur.est_transporteur = False
        utilisateur.statut_compte = Utilisateur.StatutCompte.SUSPENDU
        utilisateur.is_active = False
        utilisateur.set_unusable_password()
        utilisateur.save()
        _oublier_appareils(utilisateur)

    logger.info("Admin %s anonymise le compte %s (historique conservé)", admin.pk, utilisateur.pk)
    return "anonymise"
