from django.conf import settings
from django.core.files.storage import storages
from django.db import models


def stockage_prive():
    """Stockage des documents KYC, sans URL publique (cf. settings.STORAGES)."""
    return storages["prive"]


class Verification(models.Model):
    """Vérification d'identité / documents (KYC).

    Concerne la vérification CNI (activable par tout utilisateur) et la
    vérification des documents véhicule (obligatoire pour le rôle Transporteur).
    Chaque tentative est enregistrée (`numero_tentative`) pour conserver
    l'historique complet des essais (cf. `10-diagramme-classes.md`, 2.3) —
    une seule vérification "activée" à un instant donné.

    Les images (CNI, selfie) sont conservées de façon permanente (docs/14,
    section 5) dans un stockage privé, jamais exposé par une URL publique.
    """

    class TypeVerification(models.TextChoices):
        CNI = "cni", "Carte nationale d'identité"
        VEHICULE = "vehicule", "Documents véhicule"

    class StatutVerification(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente"
        VALIDEE = "validee", "Validée"
        REJETEE = "rejetee", "Rejetée"
        A_REVOIR = "a_revoir", "À revoir par l'administrateur"

    class Fournisseur(models.TextChoices):
        MANUEL = "manuel", "Validation manuelle (admin)"
        SMILE = "smile", "Smile Identity"

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="verifications",
    )
    type_verification = models.CharField(
        max_length=20, choices=TypeVerification.choices
    )
    statut = models.CharField(
        max_length=20,
        choices=StatutVerification.choices,
        default=StatutVerification.EN_ATTENTE,
    )
    date_soumission = models.DateTimeField(auto_now_add=True)
    date_traitement = models.DateTimeField(null=True, blank=True)
    resultat_brut = models.JSONField(
        null=True,
        blank=True,
        help_text="Réponse brute du fournisseur (Smile Identity ou fallback OCR).",
    )
    numero_tentative = models.PositiveIntegerField(
        default=1,
        help_text="Numéro de la tentative pour le même utilisateur/type.",
    )

    # Documents soumis (stockage privé)
    cni_recto = models.ImageField(
        storage=stockage_prive, upload_to="kyc/%Y/%m/", null=True, blank=True
    )
    cni_verso = models.ImageField(
        storage=stockage_prive, upload_to="kyc/%Y/%m/", null=True, blank=True
    )
    selfie = models.ImageField(
        storage=stockage_prive, upload_to="kyc/%Y/%m/", null=True, blank=True
    )

    # Traitement par le fournisseur
    fournisseur = models.CharField(
        max_length=20,
        choices=Fournisseur.choices,
        default=Fournisseur.MANUEL,
    )
    job_id_fournisseur = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text="Identifiant du traitement transmis au fournisseur (job_id OnDuty).",
    )
    motif = models.TextField(
        blank=True,
        help_text="Explication du résultat, affichable à l'utilisateur.",
    )

    class Meta:
        verbose_name = "Vérification"
        verbose_name_plural = "Vérifications"

    def __str__(self):
        return (
            f"{self.get_type_verification_display()} - "
            f"{self.utilisateur.telephone} - {self.get_statut_display()} "
            f"(tentative {self.numero_tentative})"
        )
