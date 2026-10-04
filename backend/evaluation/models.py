from django.conf import settings
from django.db import models
from django.utils import timezone


class Evaluation(models.Model):
    """Évaluation d'un transporteur par un client après une course (diagramme 2.12).

    Relation 1-1 avec Course. Alimente le score_fiabilite du transporteur.
    """

    course = models.OneToOneField(
        "course.Course",
        on_delete=models.CASCADE,
        related_name="evaluation",
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="evaluations_donnees",
    )
    transporteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="evaluations_reçues",
    )
    note = models.PositiveSmallIntegerField(
        help_text="Note de 1 à 5"
    )
    commentaire = models.TextField(blank=True, null=True)
    date_evaluation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Évaluation"
        verbose_name_plural = "Évaluations"
        ordering = ["-date_evaluation"]

    def __str__(self):
        return f"Évaluation #{self.pk} — Course {self.course_id} — {self.note}/5"

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)
        if creating:
            # Recalculer le score de fiabilité du transporteur
            from .services.fiabilite import calculer_score_fiabilite
            calculer_score_fiabilite(self.transporteur)