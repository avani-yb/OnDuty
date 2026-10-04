from django.conf import settings
from django.db import models


class InformationsVehicule(models.Model):
    """Informations véhicule du transporteur.

    Relation OneToOne : un transporteur ne déclare qu'un seul véhicule à la
    fois (cf. `03-acteurs-parties-prenantes.md`). Ce véhicule n'existe que si
    le rôle Transporteur est activé sur le compte (`est_transporteur=True`).
    """

    class TypeVehicule(models.TextChoices):
        CAMION = "camion", "Camion"
        PICKUP = "pick-up", "Pick-up"
        VOITURE = "voiture", "Voiture"

    utilisateur = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="informations_vehicule",
    )
    type_vehicule = models.CharField(
        max_length=20, choices=TypeVehicule.choices
    )
    marque = models.CharField(max_length=50)
    modele = models.CharField(max_length=50)
    immatriculation = models.CharField(max_length=20)
    capacite_max_kg = models.PositiveIntegerField(
        help_text="Capacité de chargement maximum du véhicule (en kg)."
    )

    class Meta:
        verbose_name = "Informations véhicule"
        verbose_name_plural = "Informations véhicule"

    def __str__(self):
        return (
            f"{self.marque} {self.modele} "
            f"({self.immatriculation}) - {self.utilisateur.telephone}"
        )
