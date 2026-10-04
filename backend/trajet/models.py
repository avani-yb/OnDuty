from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class Trajet(models.Model):
    """Trajet publié par un transporteur (origine → destination).

    Conforme au diagramme de classes (2.4). Le transporteur déclare un trajet
    qu'il compte effectuer dans les prochains jours (BF-25) ; la fiche sert de
    base au matching avec les demandes clients (BF-27).
    """

    class StatutTrajet(models.TextChoices):
        ACTIF = "actif", "Actif"
        COMPLET = "complet", "Complet"
        EXPIRE = "expire", "Expiré"
        SUPPRIME = "supprime", "Supprimé"

    transporteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="trajets",
    )
    origine = models.CharField(max_length=255)
    destination = models.CharField(max_length=255)
    date_depart = models.DateTimeField()
    capacite_disponible_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text=(
            "Capacité totale proposée sur ce trajet (kg). La capacité restante "
            "est calculée en retirant les kg des courses non annulées."
        ),
    )
    statut = models.CharField(
        max_length=20,
        choices=StatutTrajet.choices,
        default=StatutTrajet.ACTIF,
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Trajet"
        verbose_name_plural = "Trajets"
        ordering = ["date_depart"]

    def __str__(self):
        return f"{self.origine} → {self.destination} ({self.transporteur.telephone})"

    # --- Capacité ---

    def courses_actives(self):
        return self.courses.exclude(statut="annulee")

    @property
    def kg_reserves(self) -> Decimal:
        total = self.courses_actives().aggregate(total=Sum("demande__poids_estime_kg"))["total"]
        return total or Decimal("0")

    @property
    def capacite_restante_kg(self) -> Decimal:
        return max(Decimal("0"), self.capacite_disponible_kg - self.kg_reserves)

    # --- État affiché (actif / en cours / passé) ---

    ETAT_ACTIF = "actif"
    ETAT_EN_COURS = "en_cours"
    ETAT_PASSE = "passe"

    @property
    def etat(self):
        """« actif » avant le jour du départ, « en_cours » le jour même,
        « passe » ensuite (date locale du Cameroun). Les autres statuts
        (complet, supprimé...) sont renvoyés tels quels."""
        if self.statut != self.StatutTrajet.ACTIF:
            return self.statut
        jour_depart = timezone.localdate(self.date_depart)
        aujourd_hui = timezone.localdate()
        if jour_depart > aujourd_hui:
            return self.ETAT_ACTIF
        if jour_depart == aujourd_hui:
            return self.ETAT_EN_COURS
        return self.ETAT_PASSE

    @property
    def est_modifiable(self):
        """Modifier, supprimer ou chercher des demandes : trajets « actifs » uniquement."""
        return self.etat == self.ETAT_ACTIF
