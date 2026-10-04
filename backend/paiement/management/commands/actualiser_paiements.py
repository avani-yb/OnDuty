"""Demande à CamPay le statut des paiements et versements encore en cours.

Filet de sécurité du webhook (webhook non reçu, URL non publique en
développement...). À lancer manuellement ou par une tâche planifiée :

    python manage.py actualiser_paiements
"""

from django.core.management.base import BaseCommand

from onduty_backend.services_externes import ServiceExterneErreur
from paiement.models import Paiement, Versement
from paiement.services import escrow


class Command(BaseCommand):
    help = "Interroge CamPay pour les paiements et versements encore en cours."

    def handle(self, *args, **options):
        a_verifier = [
            (escrow.actualiser, p)
            for p in Paiement.objects.filter(statut=Paiement.StatutPaiement.EN_ATTENTE).exclude(reference_campay="")
        ] + [
            (escrow.actualiser_versement, v)
            for v in Versement.objects.filter(statut=Versement.StatutVersement.EN_COURS).exclude(reference_campay="")
        ]

        mis_a_jour = erreurs = 0
        for fonction, objet in a_verifier:
            try:
                if fonction(objet):
                    mis_a_jour += 1
            except ServiceExterneErreur as exc:
                erreurs += 1
                self.stderr.write(f"{objet} : {exc}")

        self.stdout.write(
            f"{len(a_verifier)} en cours, {mis_a_jour} mis à jour, {erreurs} erreur(s)."
        )
