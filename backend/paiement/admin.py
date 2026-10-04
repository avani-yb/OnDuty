from django.contrib import admin, messages

from onduty_backend.services_externes import ServiceExterneErreur

from .models import Paiement, Versement
from .services import escrow


class VersementInline(admin.TabularInline):
    model = Versement
    extra = 0
    can_delete = False
    fields = ("type_versement", "beneficiaire", "numero", "montant", "statut", "nb_tentatives", "message_erreur", "date_effectue")
    readonly_fields = fields


@admin.action(description="Vérifier le statut auprès de CamPay")
def verifier_statut(modeladmin, request, queryset):
    for paiement in queryset.filter(statut=Paiement.StatutPaiement.EN_ATTENTE):
        try:
            escrow.actualiser(paiement)
        except ServiceExterneErreur as exc:
            modeladmin.message_user(request, f"Paiement {paiement.pk} : {exc}", messages.ERROR)


@admin.action(description="Litige : verser le prix au transporteur")
def liberer(modeladmin, request, queryset):
    nombre = sum(1 for p in queryset if escrow.liberer(p) is not None)
    modeladmin.message_user(request, f"{nombre} paiement(s) libéré(s) au transporteur.")


@admin.action(description="Litige : rembourser le prix au client")
def rembourser(modeladmin, request, queryset):
    nombre = sum(1 for p in queryset if escrow.rembourser(p) is not None)
    modeladmin.message_user(request, f"{nombre} paiement(s) remboursé(s) au client.")


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "course",
        "montant_course",
        "commission",
        "frais",
        "montant",
        "methode",
        "statut",
        "date_paiement",
        "date_liberation",
    )
    list_filter = ("statut", "methode", "date_creation")
    search_fields = (
        "course__id",
        "course__client__telephone",
        "course__transporteur__telephone",
        "reference_transaction",
        "reference_campay",
    )
    readonly_fields = [f.name for f in Paiement._meta.fields]
    inlines = [VersementInline]
    actions = [verifier_statut, liberer, rembourser]
    date_hierarchy = "date_creation"

    def has_add_permission(self, request):
        return False


@admin.action(description="Relancer les versements échoués")
def relancer(modeladmin, request, queryset):
    for versement in queryset.filter(statut=Versement.StatutVersement.ECHOUE):
        versement = escrow.relancer_versement(versement)
        niveau = messages.SUCCESS if versement.statut != Versement.StatutVersement.ECHOUE else messages.ERROR
        modeladmin.message_user(
            request, f"Versement {versement.pk} : {versement.get_statut_display()} {versement.message_erreur}", niveau
        )


@admin.action(description="Vérifier le statut auprès de CamPay")
def verifier_versements(modeladmin, request, queryset):
    for versement in queryset.filter(statut=Versement.StatutVersement.EN_COURS):
        try:
            escrow.actualiser_versement(versement)
        except ServiceExterneErreur as exc:
            modeladmin.message_user(request, f"Versement {versement.pk} : {exc}", messages.ERROR)


@admin.register(Versement)
class VersementAdmin(admin.ModelAdmin):
    list_display = ("id", "type_versement", "beneficiaire", "numero", "montant", "statut", "nb_tentatives", "date_creation")
    list_filter = ("statut", "type_versement")
    search_fields = ("numero", "beneficiaire__telephone", "reference_campay", "reference_externe")
    readonly_fields = [f.name for f in Versement._meta.fields]
    actions = [relancer, verifier_versements]

    def has_add_permission(self, request):
        return False
