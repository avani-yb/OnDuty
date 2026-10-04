from django.contrib import admin

from .models import ContestationRejet, ControleIA, Demande


@admin.register(Demande)
class DemandeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "client",
        "origine",
        "destination",
        "date_souhaitee",
        "poids_estime_kg",
        "statut",
        "date_creation",
    )
    list_filter = ("statut", "origine", "destination")
    search_fields = (
        "client__telephone",
        "client__nom",
        "client__prenom",
        "description",
        "origine",
        "destination",
    )
    readonly_fields = ("date_creation",)


@admin.register(ControleIA)
class ControleIAAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "demande",
        "numero_tentative",
        "verdict",
        "date_execution",
        "duree_traitement_secondes",
    )
    list_filter = ("verdict",)
    search_fields = ("demande__client__telephone", "motif_rejet")


@admin.register(ContestationRejet)
class ContestationRejetAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "controle_ia",
        "client",
        "statut",
        "date_soumission",
        "date_traitement",
    )
    list_filter = ("statut",)
    search_fields = ("client__telephone",)
    readonly_fields = ("date_soumission",)
