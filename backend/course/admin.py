from django.contrib import admin

from .models import Course


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