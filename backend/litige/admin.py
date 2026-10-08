from django.contrib import admin

from .models import Incident, Litige

from . import services


@admin.action(description="Résoudre : livraison validée, prix versé au transporteur")
def resoudre_validation(modeladmin, request, queryset):
    nombre = 0
    for litige in queryset.filter(statut__in=services.STATUTS_OUVERTS).select_related("course"):
        try:
            services.valider_livraison(litige, request.user)
            nombre += 1
        except services.ArbitrageImpossible as exc:
            modeladmin.message_user(request, f"Litige {litige.pk} : {exc}", level="error")
    modeladmin.message_user(request, f"{nombre} litige(s) résolu(s) en faveur du transporteur.")


@admin.action(description="Résoudre : course annulée, prix remboursé au client")
def resoudre_remboursement(modeladmin, request, queryset):
    nombre = 0
    for litige in queryset.filter(statut__in=services.STATUTS_OUVERTS).select_related("course"):
        try:
            services.rembourser_client(litige, request.user)
            nombre += 1
        except services.ArbitrageImpossible as exc:
            modeladmin.message_user(request, f"Litige {litige.pk} : {exc}", level="error")
    modeladmin.message_user(request, f"{nombre} litige(s) résolu(s) avec remboursement du client.")


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ("id", "course", "transporteur", "date_signalement")
    list_filter = ("date_signalement",)
    search_fields = ("course__id", "transporteur__telephone", "description")
    readonly_fields = ("date_signalement",)
    date_hierarchy = "date_signalement"


@admin.register(Litige)
class LitigeAdmin(admin.ModelAdmin):
    list_display = ("id", "course", "declarant", "statut", "date_declaration", "date_resolution")
    list_filter = ("statut", "date_declaration")
    search_fields = ("course__id", "declarant__telephone", "motif", "decision_admin")
    readonly_fields = ("date_declaration", "date_resolution")
    date_hierarchy = "date_declaration"
    actions = [resoudre_validation, resoudre_remboursement]