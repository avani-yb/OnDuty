from django.conf import settings
from django.db import models
from django.utils import timezone


class Course(models.Model):
    """Entité unique fusionnant réservation et suivi (cf. diagramme de classes 2.8).

    Le statut évolue tout au long du cycle de vie :
    reservee → en_attente_paiement → payee → depart → en_route → arrivee → livree
    ou annulee / en_litige à tout moment.
    """

    class StatutCourse(models.TextChoices):
        RESERVEE = "reservee", "Réservée"
        PROPOSITION_MONTANT = "proposition_montant", "Proposition de montant en attente de validation"
        EN_ATTENTE_PAIEMENT = "en_attente_paiement", "En attente de paiement"
        PAYEE = "payee", "Payée"
        DEPART = "depart", "Départ"
        EN_ROUTE = "en_route", "En route"
        ARRIVEE = "arrivee", "Arrivée"
        LIVREE = "livree", "Livrée"
        ANNULEE = "annulee", "Annulée"
        EN_LITIGE = "en_litige", "En litige"

    demande = models.ForeignKey(
        "demande.Demande",
        on_delete=models.PROTECT,
        related_name="courses",
    )
    trajet = models.ForeignKey(
        "trajet.Trajet",
        on_delete=models.PROTECT,
        related_name="courses",
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="courses_client",
    )
    transporteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="courses_transporteur",
    )
    statut = models.CharField(
        max_length=30,
        choices=StatutCourse.choices,
        default=StatutCourse.RESERVEE,
    )
    class InitiePar(models.TextChoices):
        CLIENT = "client", "Le client a choisi le trajet"
        TRANSPORTEUR = "transporteur", "Le transporteur a choisi la demande"

    class MotifAnnulation(models.TextChoices):
        CLIENT = "client", "Annulée par le client"
        SUPPRESSION_TRAJET = "suppression_trajet", "Trajet supprimé par le transporteur"
        ADMIN = "admin", "Décision de l'administrateur"

    initiee_par = models.CharField(
        max_length=20,
        choices=InitiePar.choices,
        default=InitiePar.CLIENT,
    )
    motif_annulation = models.CharField(
        max_length=30,
        choices=MotifAnnulation.choices,
        blank=True,
    )
    montant_convenu = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text=(
            "Somme actuellement convenue pour cette course : initialisée avec "
            "le montant proposé par le client sur sa demande, modifiable une "
            "fois par le transporteur avant acceptation (le client doit alors "
            "valider la nouvelle somme avant de payer)."
        ),
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_depart_reel = models.DateTimeField(null=True, blank=True)
    date_livraison = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Course"
        verbose_name_plural = "Courses"
        ordering = ["-date_creation"]

    def __str__(self):
        return (
            f"Course #{self.pk} — {self.demande.origine} → {self.demande.destination} "
            f"({self.get_statut_display()})"
        )

    # --- Méthodes métier ---

    @property
    def est_active(self):
        """Une course annulée libère la demande et la capacité du trajet."""
        return self.statut != self.StatutCourse.ANNULEE

    @property
    def peut_etre_annulee(self):
        return self.statut not in (
            self.StatutCourse.LIVREE,
            self.StatutCourse.ANNULEE,
            self.StatutCourse.EN_LITIGE,
        )

    def annuler(self, utilisateur, motif=None):
        """Annulation (RM-02 : par le client, sans condition).

        `motif` : MotifAnnulation ; par défaut l'annulation vient du client, qui
        doit alors être `utilisateur`. Les annulations « système » (suppression
        du trajet, admin) passent utilisateur=None.
        Retourne True si l'annulation a eu lieu, False sinon.
        """
        motif = motif or self.MotifAnnulation.CLIENT
        if not self.peut_etre_annulee:
            return False
        if motif == self.MotifAnnulation.CLIENT and utilisateur != self.client:
            return False

        self.statut = self.StatutCourse.ANNULEE
        self.motif_annulation = motif
        self.save(update_fields=["statut", "motif_annulation"])
        return True

    def peut_confirmer_reception(self, utilisateur):
        """L'expéditeur, ou le destinataire s'il est inscrit sur OnDuty."""
        return utilisateur is not None and (
            utilisateur.pk == self.client_id
            or utilisateur.pk == self.demande.destinataire_id
        )

    def mettre_a_jour_statut(self, nouveau_statut, utilisateur=None):
        """Met à jour le statut avec horodatage automatique des étapes clés.

        Retourne True si la transition est valide, False sinon.
        """
        transitions_valides = {
            self.StatutCourse.RESERVEE: [
                self.StatutCourse.PROPOSITION_MONTANT,
                self.StatutCourse.EN_ATTENTE_PAIEMENT,
                self.StatutCourse.ANNULEE,
            ],
            self.StatutCourse.PROPOSITION_MONTANT: [
                self.StatutCourse.EN_ATTENTE_PAIEMENT,
                self.StatutCourse.ANNULEE,
            ],
            self.StatutCourse.EN_ATTENTE_PAIEMENT: [
                self.StatutCourse.PAYEE,
                self.StatutCourse.ANNULEE,
                self.StatutCourse.EN_LITIGE,
            ],
            self.StatutCourse.PAYEE: [
                self.StatutCourse.DEPART,
                self.StatutCourse.ANNULEE,
                self.StatutCourse.EN_LITIGE,
            ],
            self.StatutCourse.DEPART: [
                self.StatutCourse.EN_ROUTE,
                self.StatutCourse.ANNULEE,
            ],
            self.StatutCourse.EN_ROUTE: [
                self.StatutCourse.ARRIVEE,
                self.StatutCourse.ANNULEE,
            ],
            self.StatutCourse.ARRIVEE: [
                self.StatutCourse.LIVREE,
                self.StatutCourse.EN_LITIGE,
            ],
            self.StatutCourse.LIVREE: [
                self.StatutCourse.EN_LITIGE,
            ],
            self.StatutCourse.EN_LITIGE: [
                self.StatutCourse.LIVREE,
                self.StatutCourse.ANNULEE,
            ],
            self.StatutCourse.ANNULEE: [],
        }

        if nouveau_statut not in transitions_valides.get(self.statut, []):
            return False

        # Vérifications de rôle pour certaines transitions
        if nouveau_statut in (
            self.StatutCourse.DEPART,
            self.StatutCourse.EN_ROUTE,
            self.StatutCourse.ARRIVEE,
        ):
            if utilisateur != self.transporteur:
                return False

        if nouveau_statut == self.StatutCourse.LIVREE and self.statut == self.StatutCourse.ARRIVEE:
            if not self.peut_confirmer_reception(utilisateur):
                return False

        self.statut = nouveau_statut
        update_fields = ["statut"]

        if nouveau_statut == self.StatutCourse.DEPART and not self.date_depart_reel:
            self.date_depart_reel = timezone.now()
            update_fields.append("date_depart_reel")

        if nouveau_statut == self.StatutCourse.LIVREE and not self.date_livraison:
            self.date_livraison = timezone.now()
            update_fields.append("date_livraison")

        self.save(update_fields=update_fields)
        return True

    def confirmer_reception(self, utilisateur):
        """Confirmation de réception (expéditeur ou destinataire inscrit) :
        déclenche le versement au transporteur."""
        if self.statut != self.StatutCourse.ARRIVEE or not self.peut_confirmer_reception(utilisateur):
            return False
        return self.mettre_a_jour_statut(self.StatutCourse.LIVREE, utilisateur)

    def accepter_par_transporteur(self, utilisateur):
        """Le transporteur accepte la réservation telle quelle (passe à en_attente_paiement)."""
        if utilisateur != self.transporteur:
            return False
        if self.statut != self.StatutCourse.RESERVEE:
            return False
        return self.mettre_a_jour_statut(self.StatutCourse.EN_ATTENTE_PAIEMENT, utilisateur)

    def proposer_nouveau_montant(self, utilisateur, montant):
        """Le transporteur propose une nouvelle somme avant d'accepter.

        La course passe en attente de validation par le client : celui-ci
        doit explicitement valider la nouvelle somme (`valider_montant`)
        avant de pouvoir payer.
        """
        if utilisateur != self.transporteur:
            return False
        if self.statut != self.StatutCourse.RESERVEE:
            return False
        if montant <= 0:
            return False
        self.montant_convenu = montant
        self.statut = self.StatutCourse.PROPOSITION_MONTANT
        self.save(update_fields=["montant_convenu", "statut"])
        return True

    def valider_montant(self, utilisateur):
        """Le client valide la somme proposée par le transporteur et passe au paiement."""
        if utilisateur != self.client:
            return False
        if self.statut != self.StatutCourse.PROPOSITION_MONTANT:
            return False
        return self.mettre_a_jour_statut(self.StatutCourse.EN_ATTENTE_PAIEMENT, utilisateur)

    def marquer_payee(self):
        """Appelé après confirmation paiement (webhook mobile money)."""
        if self.statut != self.StatutCourse.EN_ATTENTE_PAIEMENT:
            return False
        self.statut = self.StatutCourse.PAYEE
        self.save(update_fields=["statut"])
        return True

# Statuts pendant lesquels la position du transporteur est partagée
# (décision du 04/10/2026 : du départ jusqu'à la livraison).
STATUTS_SUIVI = (
    Course.StatutCourse.DEPART,
    Course.StatutCourse.EN_ROUTE,
    Course.StatutCourse.ARRIVEE,
)


class PositionTransporteur(models.Model):
    """Position GPS envoyée par le téléphone du transporteur pendant une course.

    La dernière position est montrée aux clients de la course (expéditeur et
    destinataire inscrit) ; la suite des positions forme le trajet parcouru,
    utile en cas de litige. Purgée 1 mois après la fin de la course
    (`manage.py purger_positions`).
    """

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="positions")
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    precision_m = models.FloatField(null=True, blank=True, help_text="Précision annoncée par le GPS (mètres).")
    date = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Position du transporteur"
        verbose_name_plural = "Positions du transporteur"
        ordering = ["date"]
        indexes = [models.Index(fields=["course", "date"])]

    def __str__(self):
        return f"Course {self.course_id} — {self.latitude}, {self.longitude} ({self.date:%d/%m %H:%M})"
