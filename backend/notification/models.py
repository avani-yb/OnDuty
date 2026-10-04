from django.conf import settings
from django.db import models
from django.utils import timezone


class FCMToken(models.Model):
    """Token FCM (Firebase Cloud Messaging) pour un utilisateur.

    Un utilisateur peut avoir plusieurs tokens (plusieurs appareils).
    """

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="fcm_tokens",
    )
    token = models.TextField(help_text="Token FCM fourni par Firebase")
    device_id = models.CharField(max_length=100, blank=True, help_text="Identifiant unique de l'appareil")
    platform = models.CharField(
        max_length=20,
        choices=[("android", "Android"), ("ios", "iOS"), ("web", "Web")],
        default="android",
    )
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_derniere_utilisation = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Token FCM"
        verbose_name_plural = "Tokens FCM"
        unique_together = ["utilisateur", "token"]

    def __str__(self):
        return f"FCM {self.platform} - {self.utilisateur.telephone} ({'actif' if self.actif else 'inactif'})"


class Notification(models.Model):
    """Notification push envoyée à un utilisateur (historique).

    Conformément à la doc 11 (diagramme de communication 2.8) :
    - Résultat contrôle IA
    - Résultat KYC
    - Confirmation paiement
    - Mise à jour statut course (départ/arrivée/livré)
    - Résultat litige/contestation
    """

    class TypeNotification(models.TextChoices):
        CONTROLE_IA = "controle_ia", "Résultat contrôle IA"
        KYC = "kyc", "Résultat vérification KYC"
        PAIEMENT = "paiement", "Confirmation paiement"
        COURSE_STATUT = "course_statut", "Mise à jour statut course"
        LITIGE = "litige", "Résultat litige/contestation"
        INCIDENT = "incident", "Nouvel incident signalé"
        MATCHING = "matching", "Nouvelle proposition matching"
        GENERIQUE = "generique", "Notification générique"

    class StatutEnvoi(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente"
        ENVOYEE = "envoyee", "Envoyée"
        ECHEC = "echec", "Échec"

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    type_notification = models.CharField(
        max_length=20,
        choices=TypeNotification.choices,
        default=TypeNotification.GENERIQUE,
    )
    titre = models.CharField(max_length=200)
    corps = models.TextField()
    data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Données additionnelles (ex: course_id, demande_id, etc.)",
    )
    statut_envoi = models.CharField(
        max_length=20,
        choices=StatutEnvoi.choices,
        default=StatutEnvoi.EN_ATTENTE,
    )
    fcm_message_id = models.CharField(max_length=200, blank=True, null=True)
    date_envoi = models.DateTimeField(null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    lue = models.BooleanField(
        default=False,
        help_text="Indique si l'utilisateur a consulté cette notification côté application.",
    )
    date_lecture = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-date_creation"]

    def __str__(self):
        return f"Notification {self.get_type_notification_display()} → {self.utilisateur.telephone} ({self.get_statut_envoi_display()})"

    def marquer_envoyee(self, fcm_message_id=None):
        """Marque la notification comme envoyée avec succès."""
        self.statut_envoi = self.StatutEnvoi.ENVOYEE
        self.date_envoi = timezone.now()
        if fcm_message_id:
            self.fcm_message_id = fcm_message_id
        self.save(update_fields=["statut_envoi", "date_envoi", "fcm_message_id"])

    def marquer_echec(self):
        """Marque la notification comme échouée."""
        self.statut_envoi = self.StatutEnvoi.ECHEC
        self.save(update_fields=["statut_envoi"])

    def marquer_lue(self):
        """Marque la notification comme lue par l'utilisateur (idempotent)."""
        if self.lue:
            return
        self.lue = True
        self.date_lecture = timezone.now()
        self.save(update_fields=["lue", "date_lecture"])