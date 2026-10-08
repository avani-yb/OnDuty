from django.contrib import admin

from .models import Course, PositionTransporteur


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "demande",
        "trajet",
        "client",
        "transporteur",
        "statut",
        "date_creation",
        "date_depart_reel",
        "date_livraison",
    )
    list_filter = ("statut", "date_creation")
    search_fields = (
        "demande__client__telephone",
        "demande__origine",
        "demande__destination",
        "trajet__transporteur__telephone",
        "client__telephone",
        "transporteur__telephone",
    )
    readonly_fields = ("date_creation", "date_depart_reel", "date_livraison")
    list_editable = ("statut",)
    date_hierarchy = "date_creation"

@admin.register(PositionTransporteur)
class PositionTransporteurAdmin(admin.ModelAdmin):
    """Trajet parcouru par le transporteur (utile en cas de litige)."""

    list_display = ("course", "latitude", "longitude", "precision_m", "date")
    list_filter = ("date",)
    search_fields = ("course__id",)
    readonly_fields = ("course", "latitude", "longitude", "precision_m", "date")

    def has_add_permission(self, request):
        return False
