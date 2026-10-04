from django.conf import settings
from django.db import models
from django.utils import timezone


class Paiement(models.Model):
    """Paiement d'une course, encaissé via CamPay et bloqué en escrow.

    Montants (FCFA) :
    - `montant_course` : prix convenu entre client et transporteur ;
    - `commission` : commission OnDuty (5 % jusqu'à 10 000, 10 % au-delà) ;
    - `frais` : frais CamPay (2 × le taux CamPay, calculés sur le prix) ;
    - `montant` : total payé par le client.

    Cycle de vie :
    en_attente (validation sur le téléphone) → echoue (nouvel essai possible)
                                             → bloque_escrow → libere (versé au transporteur)
                                                             → rembourse (prix rendu au client)
    """

    class MethodePaiement(models.TextChoices):
        MTN_MOMO = "mtn_momo", "MTN MoMo"
        ORANGE_MONEY = "orange_money", "Orange Money"

    class StatutPaiement(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente de validation"
        ECHOUE = "echoue", "Échoué"
        BLOQUE_ESCROW = "bloque_escrow", "Bloqué en escrow"
        LIBERE = "libere", "Libéré au transporteur"
        REMBOURSE = "rembourse", "Remboursé au client"

    course = models.OneToOneField(
        "course.Course",
        on_delete=models.PROTECT,
        related_name="paiement",
    )
    montant_course = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    frais = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    montant = models.DecimalField(
        max_digits=12, decimal_places=2, help_text="Total payé par le client."
    )
    methode = models.CharField(
        max_length=20,
        choices=MethodePaiement.choices,
        blank=True,
        help_text="Opérateur détecté par CamPay.",
    )
    numero_payeur = models.CharField(max_length=20, blank=True)
    statut = models.CharField(
        max_length=20,
        choices=StatutPaiement.choices,
        default=StatutPaiement.EN_ATTENTE,
    )
    reference_transaction = models.CharField(
        max_length=100,
        unique=True,
        help_text="Référence OnDuty transmise à CamPay (external_reference).",
    )
    reference_campay = models.CharField(max_length=100, blank=True, db_index=True)
    code_ussd = models.CharField(max_length=30, blank=True)
    message_erreur = models.TextField(blank=True)
    historique = models.JSONField(
        default=list,
        blank=True,
        help_text="Tentatives précédentes (échouées) de paiement.",
    )
    date_paiement = models.DateTimeField(null=True, blank=True)
    date_liberation = models.DateTimeField(null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"
        ordering = ["-date_creation"]

    def __str__(self):
        return f"Paiement #{self.pk} — Course {self.course_id} — {self.get_statut_display()} ({self.montant} FCFA)"


class Versement(models.Model):
    """Envoi d'argent par CamPay (/withdraw/) : au transporteur après la
    livraison, ou au client en cas d'annulation. Un échec est conservé et
    peut être relancé par l'administrateur."""

    class TypeVersement(models.TextChoices):
        TRANSPORTEUR = "transporteur", "Paiement du transporteur"
        REMBOURSEMENT = "remboursement", "Remboursement du client"

    class StatutVersement(models.TextChoices):
        EN_COURS = "en_cours", "En cours"
        EFFECTUE = "effectue", "Effectué"
        ECHOUE = "echoue", "Échoué"

    paiement = models.ForeignKey(Paiement, on_delete=models.PROTECT, related_name="versements")
    type_versement = models.CharField(max_length=20, choices=TypeVersement.choices)
    beneficiaire = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="versements_recus"
    )
    numero = models.CharField(max_length=20)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    statut = models.CharField(
        max_length=20,
        choices=StatutVersement.choices,
        default=StatutVersement.EN_COURS,
    )
    reference_externe = models.CharField(max_length=100, unique=True)
    reference_campay = models.CharField(max_length=100, blank=True, db_index=True)
    message_erreur = models.TextField(blank=True)
    nb_tentatives = models.PositiveIntegerField(default=0)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_effectue = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Versement"
        verbose_name_plural = "Versements"
        ordering = ["-date_creation"]

    def __str__(self):
        return (
            f"{self.get_type_versement_display()} #{self.pk} — {self.montant} FCFA "
            f"→ {self.numero} ({self.get_statut_display()})"
        )

    def marquer_effectue(self):
        self.statut = self.StatutVersement.EFFECTUE
        self.date_effectue = timezone.now()
        self.message_erreur = ""
        self.save(update_fields=["statut", "date_effectue", "message_erreur"])
