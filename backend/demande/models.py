from django.conf import settings
from django.db import models


class Demande(models.Model):
    """Demande d'expédition initiée par un client (BF-03).

    Chaque demande passe obligatoirement par le contrôle IA avant toute
    publication/matching (BF-04). Une même demande peut subir plusieurs
    tentatives de contrôle (`ControleIA`) — BF-07/BF-09.
    """

    class StatutDemande(models.TextChoices):
        EN_COURS_CONTROLE = "en_cours_controle", "En cours de contrôle"
        VALIDEE = "validee", "Validée"
        REJETEE = "rejetee", "Rejetée"
        PUBLIEE = "publiee", "Publiée"
        SUPPRIMEE = "supprimee", "Supprimée"

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="demandes",
    )
    origine = models.CharField(max_length=255)
    destination = models.CharField(max_length=255)
    date_souhaitee = models.DateTimeField()
    description = models.TextField(
        help_text="Description de l'objet / marchandise par le client."
    )
    poids_estime_kg = models.DecimalField(max_digits=10, decimal_places=2)
    montant_propose = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Somme que le client est prêt à payer pour cette expédition (FCFA).",
    )
    video = models.FileField(
        upload_to="demandes_videos/%Y/%m/",
        null=True,
        blank=True,
        help_text="Fichier vidéo envoyé depuis l'application mobile (capture caméra).",
    )
    video_url = models.URLField(
        blank=True,
        help_text=(
            "URL de la vidéo de l'article à expédier. Renseignée automatiquement "
            "à partir du fichier `video` si celui-ci est envoyé, ou fournie "
            "directement (vidéo déjà hébergée)."
        ),
    )
    statut = models.CharField(
        max_length=30,
        choices=StatutDemande.choices,
        default=StatutDemande.EN_COURS_CONTROLE,
    )
    telephone_destinataire = models.CharField(
        max_length=20,
        blank=True,
        help_text="Numéro de la personne qui reçoit le colis (information pour le transporteur).",
    )
    destinataire = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="colis_a_recevoir",
        help_text=(
            "Compte OnDuty du destinataire, si son numéro est inscrit : il est "
            "notifié, voit la course et peut confirmer la réception."
        ),
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Demande"
        verbose_name_plural = "Demandes"
        ordering = ["-date_creation"]

    def __str__(self):
        return (
            f"Demande #{self.pk} ({self.origine} → {self.destination}) — "
            f"{self.get_statut_display()}"
        )


class ControleIA(models.Model):
    """Résultat du contrôle IA sur une demande (historisation des tentatives).

    Conforme au diagramme de classes (2.6) : une demande peut avoir plusieurs
    ControleIA (une par tentative). Conserve la trace complète pour l'audit et
    les litiges (BF-09).
    """

    class Verdict(models.TextChoices):
        VALIDE = "valide", "Validé"
        REJETE = "rejete", "Rejeté"

    demande = models.ForeignKey(
        Demande,
        on_delete=models.CASCADE,
        related_name="controles",
    )
    numero_tentative = models.PositiveIntegerField(
        default=1,
        help_text="Numéro de la tentative de contrôle pour cette demande.",
    )
    resultat_detection_objets = models.JSONField(
        null=True,
        blank=True,
        help_text="Sortie du fournisseur Vision API (liste d'objets détectés + confiance).",
    )
    resultat_coherence = models.JSONField(
        null=True,
        blank=True,
        help_text="Sortie du fournisseur de cohérence GPT (verdict + détails visuels).",
    )
    verdict = models.CharField(max_length=10, choices=Verdict.choices)
    motif_rejet = models.TextField(null=True, blank=True)
    date_execution = models.DateTimeField(auto_now_add=True)
    duree_traitement_secondes = models.FloatField(default=0)

    class Meta:
        verbose_name = "Contrôle IA"
        verbose_name_plural = "Contrôles IA"

    def __str__(self):
        return (
            f"Contrôle #{self.pk} (demande {self.demande_id}, tentative "
            f"{self.numero_tentative}) — {self.get_verdict_display()}"
        )


class ContestationRejet(models.Model):
    """Revue manuelle par l'administrateur d'un rejet contesté (BF-08).

    Conforme au diagramme de classes (2.7) : le client estime que l'IA s'est
    trompée ; l'admin confirme ou infirme la décision.
    """

    class StatutContestation(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente"
        CONFIRMEE = "confirmee", "Confirmée"
        INFIRMEE = "infirmee", "Infirmée"

    controle_ia = models.ForeignKey(
        ControleIA,
        on_delete=models.CASCADE,
        related_name="contestations",
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="contestations",
    )
    statut = models.CharField(
        max_length=20,
        choices=StatutContestation.choices,
        default=StatutContestation.EN_ATTENTE,
    )
    commentaire_admin = models.TextField(null=True, blank=True)
    date_soumission = models.DateTimeField(auto_now_add=True)
    date_traitement = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Contestation de rejet"
        verbose_name_plural = "Contestations de rejet"

    def __str__(self):
        return (
            f"Contestation #{self.pk} — contrôle {self.controle_ia_id} — "
            f"{self.get_statut_display()}"
        )
