from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils.html import format_html

from comptes.models import Utilisateur
from course.models import Course
from demande.models import ContestationRejet, Demande
from litige.models import Incident, Litige
from paiement.models import Paiement
from trajet.models import Trajet
from verification.models import Verification


# =====================
# Filtres personnalisés
# =====================

class StatutCourseFilter(SimpleListFilter):
    title = "Statut course"
    parameter_name = "statut_course"

    def lookups(self, request, model_admin):
        return Course.StatutCourse.choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(statut=self.value())


class StatutLitigeFilter(SimpleListFilter):
    title = "Statut litige"
    parameter_name = "statut_litige"

    def lookups(self, request, model_admin):
        return Litige.StatutLitige.choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(statut=self.value())


class StatutVerificationFilter(SimpleListFilter):
    title = "Statut vérification"
    parameter_name = "statut_verification"

    def lookups(self, request, model_admin):
        return Verification.StatutVerification.choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(statut=self.value())


class StatutPaiementFilter(SimpleListFilter):
    title = "Statut paiement"
    parameter_name = "statut_paiement"

    def lookups(self, request, model_admin):
        return Paiement.StatutPaiement.choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(statut=self.value())


# =====================
# Actions personnalisées
# =====================

@admin.action(description="Valider les vérifications sélectionnées (KYC)")
def valider_verifications(modeladmin, request, queryset):
    from django.utils import timezone
    from verification.models import Verification
    count = queryset.filter(statut=Verification.StatutVerification.EN_ATTENTE).update(
        statut=Verification.StatutVerification.VALIDEE,
        date_traitement=timezone.now(),
    )
    modeladmin.message_user(request, f"{count} vérification(s) validée(s).")


@admin.action(description="Rejeter les vérifications sélectionnées (KYC)")
def rejeter_verifications(modeladmin, request, queryset):
    from django.utils import timezone
    from verification.models import Verification
    count = queryset.filter(statut=Verification.StatutVerification.EN_ATTENTE).update(
        statut=Verification.StatutVerification.REJETEE,
        date_traitement=timezone.now(),
    )
    modeladmin.message_user(request, f"{count} vérification(s) rejetée(s).")


@admin.action(description="Suspendre les comptes sélectionnés")
def suspendre_comptes(modeladmin, request, queryset):
    count = queryset.update(statut_compte=Utilisateur.StatutCompte.SUSPENDU)
    modeladmin.message_user(request, f"{count} compte(s) suspendu(s).")


@admin.action(description="Réactiver les comptes sélectionnés")
def reactiver_comptes(modeladmin, request, queryset):
    count = queryset.update(statut_compte=Utilisateur.StatutCompte.ACTIF)
    modeladmin.message_user(request, f"{count} compte(s) réactivé(s).")


@admin.action(description="Activer le rôle transporteur")
def activer_role_transporteur(modeladmin, request, queryset):
    count = queryset.update(est_transporteur=True)
    modeladmin.message_user(request, f"Rôle transporteur activé pour {count} utilisateur(s).")


@admin.action(description="Désactiver le rôle transporteur")
def desactiver_role_transporteur(modeladmin, request, queryset):
    count = queryset.update(est_transporteur=False)
    modeladmin.message_user(request, f"Rôle transporteur désactivé pour {count} utilisateur(s).")


from django.utils import timezone


# =====================
# Personnalisation du site admin
# =====================

admin.site.site_header = "OnDuty - Administration"
admin.site.site_title = "OnDuty Admin"
admin.site.index_title = "Tableau de bord administrateur"