from django.contrib import admin

from .models import InformationsVehicule


@admin.register(InformationsVehicule)
class InformationsVehiculeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "utilisateur",
        "type_vehicule",
        "marque",
        "modele",
        "immatriculation",
        "capacite_max_kg",
    )
    list_filter = ("type_vehicule",)
    search_fields = ("marque", "modele", "immatriculation", "utilisateur__telephone")
