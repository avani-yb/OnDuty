import logging
import mimetypes

from django.contrib import admin
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join

from .models import Verification

logger = logging.getLogger(__name__)

CHAMPS_DOCUMENTS = ("cni_recto", "cni_verso", "selfie")
STATUTS_A_TRAITER = (
    Verification.StatutVerification.EN_ATTENTE,
    Verification.StatutVerification.A_REVOIR,
)


@admin.action(description="Valider les vérifications sélectionnées (KYC)")
def valider(modeladmin, request, queryset):
    count = queryset.filter(statut__in=STATUTS_A_TRAITER).update(
        statut=Verification.StatutVerification.VALIDEE,
        motif="Votre identité a été vérifiée.",
        date_traitement=timezone.now(),
    )
    modeladmin.message_user(request, f"{count} vérification(s) validée(s).")


@admin.action(description="Rejeter les vérifications sélectionnées (KYC)")
def rejeter(modeladmin, request, queryset):
    count = queryset.filter(statut__in=STATUTS_A_TRAITER).update(
        statut=Verification.StatutVerification.REJETEE,
        motif="La vérification a été refusée. Recommencez avec des photos nettes.",
        date_traitement=timezone.now(),
    )
    modeladmin.message_user(request, f"{count} vérification(s) rejetée(s).")


@admin.register(Verification)
class VerificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "utilisateur",
        "type_verification",
        "statut",
        "fournisseur",
        "numero_tentative",
        "date_soumission",
        "date_traitement",
    )
    list_filter = ("type_verification", "statut", "fournisseur")
    search_fields = ("utilisateur__telephone", "utilisateur__nom", "utilisateur__prenom")
    readonly_fields = ("date_soumission", "documents", "fournisseur", "job_id_fournisseur")
    actions = (valider, rejeter)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "utilisateur",
                    "type_verification",
                    "statut",
                    "motif",
                    "numero_tentative",
                )
            },
        ),
        ("Documents", {"fields": ("documents",)}),
        (
            "Résultat fournisseur",
            {
                "fields": (
                    "fournisseur",
                    "job_id_fournisseur",
                    "resultat_brut",
                    "date_traitement",
                    "date_soumission",
                )
            },
        ),
    )

    @admin.display(description="Photos")
    def documents(self, obj):
        liens = [
            (reverse("admin:verification_document", args=[obj.pk, champ]), champ)
            for champ in CHAMPS_DOCUMENTS
            if getattr(obj, champ)
        ]
        if not liens:
            return "Aucune photo"
        return format_html_join(" · ", '<a href="{}" target="_blank">{}</a>', liens)

    def get_urls(self):
        return [
            path(
                "<int:pk>/document/<str:champ>/",
                self.admin_site.admin_view(self.voir_document),
                name="verification_document",
            ),
        ] + super().get_urls()

    def voir_document(self, request, pk, champ):
        """Photos servies uniquement aux comptes admin (stockage privé)."""
        verification = get_object_or_404(Verification, pk=pk)
        if champ not in CHAMPS_DOCUMENTS or not getattr(verification, champ):
            raise Http404
        logger.info(
            "Accès admin %s au document %s de la vérification %s",
            request.user.pk, champ, verification.pk,
        )
        fichier = getattr(verification, champ)
        type_mime = mimetypes.guess_type(fichier.name)[0] or "application/octet-stream"
        return FileResponse(fichier.open("rb"), content_type=type_mime)
