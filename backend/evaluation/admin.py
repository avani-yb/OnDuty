from django.contrib import admin

from .models import Evaluation


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "course",
        "client",
        "transporteur",
        "note",
        "date_evaluation",
    )
    list_filter = ("note", "date_evaluation")
    search_fields = (
        "course__id",
        "client__telephone",
        "transporteur__telephone",
        "commentaire",
    )
    readonly_fields = ("date_evaluation",)
    list_editable = ("note",)
    date_hierarchy = "date_evaluation"