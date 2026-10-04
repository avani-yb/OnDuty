from django.contrib import admin

from .models import Trajet


@admin.register(Trajet)
class TrajetAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "transporteur",
        "origine",
        "destination",
        "date_depart",
        "capacite_disponible_kg",
        "statut",
        "date_creation",
    )
    list_filter = ("statut", "origine", "destination")
    search_fields = ("transporteur__telephone", "origine", "destination")
    list_editable = ("statut", "capacite_disponible_kg")
