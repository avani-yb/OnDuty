from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models


class UtilisateurManager(BaseUserManager):
    """Manager personnalisé : les comptes sont identifiés par leur téléphone.

    L'AbstractUser fournit par défaut un manager basé sur `username`.
    Comme OnDuty se connecte par téléphone (USERNAME_FIELD = "telephone"),
    on redéfinit les méthodes de création pour adapter la signature.
    """

    use_in_migrations = True

    def _create_user(self, telephone, nom, prenom, password, **extra_fields):
        if not telephone:
            raise ValueError("Le numéro de téléphone est obligatoire.")
        utilisateur = self.model(
            telephone=telephone, nom=nom, prenom=prenom, **extra_fields
        )
        utilisateur.set_password(password)
        utilisateur.save(using=self._db)
        return utilisateur

    def create_user(self, telephone, nom, prenom, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(telephone, nom, prenom, password, **extra_fields)

    def create_superuser(self, telephone, nom, prenom, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("type_compte", "admin")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Un superuser doit avoir is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Un superuser doit avoir is_superuser=True.")

        return self._create_user(telephone, nom, prenom, password, **extra_fields)


class Utilisateur(AbstractUser):
    """Modèle utilisateur OnDuty.

    Un utilisateur unique peut cumuler les rôles Client et Transporteur.
    L'identifiant de connexion est le numéro de téléphone (USERNAME_FIELD).
    Le champ `type_compte` distingue le compte admin unique du reste.
    """

    class TypeCompte(models.TextChoices):
        CLIENT_STANDARD = "client_standard", "Client standard"
        ADMIN = "admin", "Administrateur"

    class StatutCompte(models.TextChoices):
        ACTIF = "actif", "Actif"
        SUSPENDU = "suspendu", "Suspendu"

    # On désactive le champ `username` hérité d'AbstractUser :
    # la connexion se fait par téléphone, pas par nom d'utilisateur.
    username = None

    # Identité
    nom = models.CharField(max_length=50)
    prenom = models.CharField(max_length=50)
    telephone = models.CharField(max_length=20, unique=True)
    email = models.EmailField(blank=True)
    numero_mobile_money = models.CharField(
        max_length=20,
        blank=True,
        help_text=(
            "Numéro MTN MoMo / Orange Money qui reçoit les versements et "
            "remboursements. Vide : le téléphone du compte est utilisé."
        ),
    )

    # Profil et rôle
    photo_profil = models.ImageField(
        upload_to="photos_profil/", blank=True, null=True
    )
    est_transporteur = models.BooleanField(
        default=False,
        help_text="Indique si le rôle Transporteur est activé sur ce compte.",
    )

    # Type de compte (distingué l'admin unique des comptes standards)
    type_compte = models.CharField(
        max_length=20,
        choices=TypeCompte.choices,
        default=TypeCompte.CLIENT_STANDARD,
    )

    # Fiabilité (recalculée après chaque course) et statut du compte
    score_fiabilite = models.DecimalField(
        max_digits=4, decimal_places=2, default=0.00
    )
    statut_compte = models.CharField(
        max_length=20,
        choices=StatutCompte.choices,
        default=StatutCompte.ACTIF,
    )

    # Horodatage de création du compte
    date_creation = models.DateTimeField(auto_now_add=True)

    # L'identifiant de connexion est le téléphone
    USERNAME_FIELD = "telephone"
    REQUIRED_FIELDS = ["nom", "prenom"]

    # Manager personnalisé pour la création des comptes par téléphone
    objects = UtilisateurManager()

    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.telephone})"

    @property
    def numero_versement(self):
        """Numéro Mobile Money qui reçoit l'argent (versements, remboursements)."""
        return self.numero_mobile_money or self.telephone

    @property
    def est_admin(self):
        """Indique si le compte est le compte administrateur unique."""
        return self.type_compte == self.TypeCompte.ADMIN

    def activer_role_transporteur(self):
        """Active le rôle Transporteur sur le compte (méthode conceptuelle)."""
        self.est_transporteur = True
        self.save(update_fields=["est_transporteur"])


def chercher_par_telephone(numero):
    """Compte OnDuty correspondant à un numéro camerounais, quel que soit son
    format (6XXXXXXXX, 2376XXXXXXXX, +237 6 XX XX XX XX), ou None."""
    chiffres = "".join(c for c in (numero or "") if c.isdigit())
    if chiffres.startswith("00237"):
        chiffres = chiffres[2:]
    local = chiffres[3:] if chiffres.startswith("237") and len(chiffres) == 12 else chiffres
    if not local:
        return None
    return Utilisateur.objects.filter(telephone__in=[local, "237" + local]).first()
