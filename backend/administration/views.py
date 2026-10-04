from django.contrib.admin.views.decorators import staff_member_required
from django.db import models
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from comptes.models import Utilisateur
from course.models import Course
from demande.models import Demande
from litige.models import Litige
from paiement.models import Paiement
from trajet.models import Trajet
from verification.models import Verification


@staff_member_required
@require_http_methods(["GET"])
def dashboard_stats(request):
    """Retourne les statistiques pour le tableau de bord admin.

    Doc 06 §11 : stats pour le dashboard admin.
    """
    # Courses
    courses_actives = Course.objects.exclude(
        statut__in=[
            Course.StatutCourse.LIVREE,
            Course.StatutCourse.ANNULEE,
            Course.StatutCourse.EN_LITIGE,
        ]
    ).count()
    courses_terminees = Course.objects.filter(statut=Course.StatutCourse.LIVREE).count()
    courses_annulees = Course.objects.filter(statut=Course.StatutCourse.ANNULEE).count()

    # Escrow (paiements bloqués)
    escrow_en_cours = Paiement.objects.filter(
        statut=Paiement.StatutPaiement.BLOQUE_ESCROW
    ).count()
    escrow_total_montant = (
        Paiement.objects.filter(statut=Paiement.StatutPaiement.BLOQUE_ESCROW).aggregate(
            total=models.Sum("montant")
        )["total"]
        or 0
    )

    # Demandes IA
    demandes_rejetees_ia = Demande.objects.filter(statut=Demande.StatutDemande.REJETEE).count()
    contestations_en_attente = (
        Demande.objects.filter(statut=Demande.StatutDemande.REJETEE)
        .filter(controles__contestations__statut="en_attente")
        .distinct()
        .count()
    )

    # Litiges
    litiges_ouverts = Litige.objects.filter(statut=Litige.StatutLitige.OUVERT).count()
    litiges_en_cours = Litige.objects.filter(
        statut=Litige.StatutLitige.EN_COURS_ANALYSE
    ).count()
    litiges_resolus = Litige.objects.filter(statut=Litige.StatutLitige.RESOLU).count()

    # KYC en attente
    kyc_en_attente = Verification.objects.filter(
        statut__in=[
            Verification.StatutVerification.EN_ATTENTE,
            Verification.StatutVerification.A_REVOIR,
        ]
    ).count()

    # Transporteurs en attente de validation KYC (est_transporteur=True mais pas de CNI validée)
    transporteurs_sans_kyc = Utilisateur.objects.filter(
        est_transporteur=True
    ).exclude(
        verifications__type_verification=Verification.TypeVerification.CNI,
        verifications__statut=Verification.StatutVerification.VALIDEE,
    ).count()

    data = {
        "courses": {
            "actives": courses_actives,
            "terminees": courses_terminees,
            "annulees": courses_annulees,
        },
        "escrow": {
            "en_cours": escrow_en_cours,
            "montant_total": float(escrow_total_montant),
        },
        "demandes_ia": {
            "rejetees": demandes_rejetees_ia,
            "contestations_en_attente": contestations_en_attente,
        },
        "litiges": {
            "ouverts": litiges_ouverts,
            "en_cours": litiges_en_cours,
            "resolus": litiges_resolus,
        },
        "kyc": {
            "en_attente": kyc_en_attente,
            "transporteurs_sans_kyc": transporteurs_sans_kyc,
        },
    }
    return JsonResponse(data)