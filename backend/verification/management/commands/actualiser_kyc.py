"""Récupère auprès de Smile Identity les résultats KYC encore en attente.

Filet de sécurité du callback (callback non reçu, URL non publique en
développement...). À lancer manuellement ou par une tâche planifiée :

    python manage.py actualiser_kyc
"""

from django.core.management.base import BaseCommand

from onduty_backend.services_externes import ServiceExterneErreur
from verification.models import Verification
from verification.services import kyc


class Command(BaseCommand):
    help = "Interroge Smile Identity pour les vérifications KYC encore en attente."

    def handle(self, *args, **options):
        en_attente = Verification.objects.filter(
            fournisseur=Verification.Fournisseur.SMILE,
            statut=Verification.StatutVerification.EN_ATTENTE,
        ).exclude(job_id_fournisseur="")
        total = en_attente.count()

        mises_a_jour = erreurs = 0
        for verification in en_attente:
            try:
                if kyc.actualiser(verification):
                    mises_a_jour += 1
            except ServiceExterneErreur as exc:
                erreurs += 1
                self.stderr.write(f"Vérification {verification.pk} : {exc}")

        self.stdout.write(
            f"{total} en attente, {mises_a_jour} mise(s) à jour, {erreurs} erreur(s)."
        )
