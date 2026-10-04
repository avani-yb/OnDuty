from django.contrib import admin
from django.utils import timezone

from .models import Incident, Litige

STATUTS_OUVERTS = (Litige.StatutLitige.OUVERT, Litige.StatutLitige.EN_COURS_ANALYSE)


def _resoudre(litige, decision):
    litige.statut = Litige.StatutLitige.RESOLU
    litige.decision_admin = decision
    litige.date_resolution = timezone.now()
    litige.save(update_fields=["statut", "decision_admin", "date_resolution"])

    from notification.models import Notification
    from notification.services.notifier import notifier

    course = litige.course
    for personne in (course.client, course.transporteur):
        notifier(personne, Notification.TypeNotification.LITIGE, "Litige résolu",
                 f"Course #{course.pk} : {decision}", course_id=course.pk)


@admin.action(description="Résoudre : livraison validée, prix versé au transporteur")
def resoudre_validation(modeladmin, request, queryset):
    from paiement.services import escrow

    nombre = 0
    for litige in queryset.filter(statut__in=STATUTS_OUVERTS).select_related("course"):
        course = litige.course
        course.mettre_a_jour_statut(course.StatutCourse.LIVREE, request.user)
        paiement = getattr(course, "paiement", None)
        if paiement is not None:
            escrow.liberer(paiement)
        _resoudre(litige, "Livraison validée : le prix de la course est versé au transporteur.")
        nombre += 1
    modeladmin.message_user(request, f"{nombre} litige(s) résolu(s) en faveur du transporteur.")


@admin.action(description="Résoudre : course annulée, prix remboursé au client")
def resoudre_remboursement(modeladmin, request, queryset):
    from paiement.services import escrow

    nombre = 0
    for litige in queryset.filter(statut__in=STATUTS_OUVERTS).select_related("course"):
        course = litige.course
        course.statut = course.StatutCourse.ANNULEE
        course.motif_annulation = course.MotifAnnulation.ADMIN
        course.save(update_fields=["statut", "motif_annulation"])
        paiement = getattr(course, "paiement", None)
        if paiement is not None:
            escrow.rembourser(paiement)
        _resoudre(litige, "Course annulée : le prix de la course est remboursé au client.")
        nombre += 1
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