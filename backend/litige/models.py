from django.conf import settings
from django.db import models
from django.utils import timezone


class Incident(models.Model):
    """Signalement d'incident par le transporteur pendant une course (diagramme 2.10).

    Texte libre, pas de catégories prédéfinies. Visible par l'admin,
    peut servir de pièce en cas de litige ultérieur.
    """

    course = models.ForeignKey(
        "course.Course",
        on_delete=models.CASCADE,
        related_name="incidents",
    )
    transporteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="incidents_signales",
    )
    description = models.TextField()
    date_signalement = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Incident"
        verbose_name_plural = "Incidents"
        ordering = ["-date_signalement"]

    def __str__(self):
        return f"Incident #{self.pk} — Course {self.course_id} — {self.transporteur.telephone}"


class Litige(models.Model):
    """Litige déclaré par un utilisateur (client ou transporteur) sur une course (diagramme 2.11).

    Motif libre. L'admin arbitre : validation livraison, remboursement, etc.
    """

    class StatutLitige(models.TextChoices):
        OUVERT = "ouvert", "Ouvert"
        EN_COURS_ANALYSE = "en_cours_analyse", "En cours d'analyse"
        RESOLU = "resolu", "Résolu"

    course = models.ForeignKey(
        "course.Course",
        on_delete=models.CASCADE,
        related_name="litiges",
    )
    declarant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="litiges_declares",
    )
    motif = models.TextField()
    statut = models.CharField(
        max_length=20,
        choices=StatutLitige.choices,
        default=StatutLitige.OUVERT,
    )
    decision_admin = models.TextField(null=True, blank=True)
    date_declaration = models.DateTimeField(auto_now_add=True)
    date_resolution = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Litige"
        verbose_name_plural = "Litiges"
        ordering = ["-date_declaration"]

    def __str__(self):
        return f"Litige #{self.pk} — Course {self.course_id} — {self.get_statut_display()}"

    def resoudre(self, admin_user, decision):
        """Résout le litige par décision admin."""
        if not admin_user.est_admin:
            return False
        self.statut = self.StatutLitige.RESOLU
        self.decision_admin = decision
        self.date_resolution = timezone.now()
        self.save(update_fields=["statut", "decision_admin", "date_resolution"])
        return True

    def prendre_en_charge(self, admin_user):
        """Admin prend en charge le litige (passe en cours d'analyse)."""
        if not admin_user.est_admin:
            return False
        if self.statut != self.StatutLitige.OUVERT:
            return False
        self.statut = self.StatutLitige.EN_COURS_ANALYSE
        self.save(update_fields=["statut"])
        return True