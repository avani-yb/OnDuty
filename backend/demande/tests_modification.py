"""Modification et suppression d'une demande (décision du 04/10/2026)."""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from notification.models import Notification
from onduty_backend import tests_outils as f

from .models import Demande


@override_settings(IA_FOURNISSEUR="simulation")
class ModificationDemandeTests(TestCase):
    def setUp(self):
        self.client_u = f.utilisateur("690000001")
        self.transporteur = f.utilisateur("690000002", transporteur=True)
        self.demande = f.demande(self.client_u, montant=5000)
        self.api = APIClient()
        self.api.force_authenticate(self.client_u)

    def patch(self, **donnees):
        return self.api.patch(f"/api/demandes/{self.demande.pk}/", donnees, format="json")

    def test_sans_course_tout_modifiable(self):
        reponse = self.patch(poids_estime_kg="12", destination="Kribi")
        self.assertEqual(reponse.status_code, 200, reponse.data)
        self.assertEqual(reponse.data["destination"], "Kribi")

    def test_nouvelle_description_relance_le_controle(self):
        reponse = self.patch(description="Carton de munitions")
        self.assertEqual(reponse.data["controle_ia"]["verdict"], "rejete")
        self.assertEqual(reponse.data["demande"]["statut"], "rejetee")

    def test_apres_reservation_champs_limites_et_transporteur_notifie(self):
        course = f.course(self.demande, f.trajet(self.transporteur), statut="reservee")
        self.assertEqual(self.patch(description="Autre").status_code, 400)

        date = (timezone.now() + timedelta(days=5)).isoformat()
        reponse = self.patch(montant_propose="5500", date_souhaitee=date, telephone_destinataire="690000099")
        self.assertEqual(reponse.status_code, 200, reponse.data)
        course.refresh_from_db()
        self.assertEqual(course.montant_convenu, Decimal("5500"))
        self.assertTrue(Notification.objects.filter(utilisateur=self.transporteur, titre="Demande modifiée").exists())

    def test_prix_bloque_une_fois_accepte(self):
        f.course(self.demande, f.trajet(self.transporteur), statut="en_attente_paiement")
        self.assertEqual(self.patch(montant_propose="9000").status_code, 400)
        self.assertEqual(self.patch(telephone_destinataire="690000099").status_code, 200)

    def test_suppression(self):
        course = f.course(self.demande, f.trajet(self.transporteur), statut="reservee")
        self.assertEqual(self.api.delete(f"/api/demandes/{self.demande.pk}/").status_code, 400)
        course.statut = "annulee"
        course.save()
        self.assertEqual(self.api.delete(f"/api/demandes/{self.demande.pk}/").status_code, 204)
        self.assertEqual(Demande.objects.get().statut, "supprimee")
        self.assertEqual(self.api.get("/api/demandes/").data, [])

    def test_contestation_et_resultat_notifie(self):
        self.patch(description="Carton de munitions")
        contestation = self.api.post(f"/api/demandes/{self.demande.pk}/contester/").data
        admin = f.utilisateur("690000000")
        admin.type_compte = "admin"
        admin.save()
        api_admin = APIClient()
        api_admin.force_authenticate(admin)
        reponse = api_admin.patch(
            f"/api/contestations/{contestation['id']}/", {"statut": "infirmee"}, format="json"
        )
        self.assertEqual(reponse.status_code, 200, reponse.data)
        self.demande.refresh_from_db()
        self.assertEqual(self.demande.statut, "publiee")
        self.assertTrue(Notification.objects.filter(utilisateur=self.client_u, titre="Contestation acceptée").exists())
