"""Fabriques communes aux tests (utilisateurs, trajets, demandes, courses)."""

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from comptes.models import Utilisateur


def utilisateur(telephone, prenom="Test", transporteur=False, vehicule="camion"):
    u = Utilisateur.objects.create_user(
        telephone=telephone, nom="Nom", prenom=prenom, password="motdepasse-123"
    )
    if transporteur:
        from vehicule.models import InformationsVehicule

        u.est_transporteur = True
        u.save(update_fields=["est_transporteur"])
        InformationsVehicule.objects.create(
            utilisateur=u, type_vehicule=vehicule, marque="M", modele="X",
            immatriculation=f"LT-{telephone[-4:]}", capacite_max_kg=1000,
        )
    return u


def trajet(transporteur, jours=3, capacite=100, origine="Douala", destination="Yaoundé"):
    from trajet.models import Trajet

    return Trajet.objects.create(
        transporteur=transporteur,
        origine=origine,
        destination=destination,
        date_depart=timezone.now() + timedelta(days=jours),
        capacite_disponible_kg=Decimal(capacite),
    )


def demande(client, poids=10, montant=5000, telephone_destinataire="", origine="Douala", destination="Yaoundé"):
    from demande.models import Demande

    return Demande.objects.create(
        client=client,
        origine=origine,
        destination=destination,
        date_souhaitee=timezone.now() + timedelta(days=3),
        description="Sac de vêtements",
        poids_estime_kg=Decimal(poids),
        montant_propose=Decimal(montant),
        video_url="https://exemple.org/v.mp4",
        telephone_destinataire=telephone_destinataire,
        statut=Demande.StatutDemande.PUBLIEE,
    )


def course(demande_, trajet_, statut="en_attente_paiement", montant=None):
    from course.models import Course

    return Course.objects.create(
        demande=demande_,
        trajet=trajet_,
        client=demande_.client,
        transporteur=trajet_.transporteur,
        statut=statut,
        montant_convenu=montant or demande_.montant_propose,
    )
