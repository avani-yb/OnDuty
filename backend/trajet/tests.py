"""Trajets : état affiché, ordre, modification, suppression (annulations,
remboursements, pénalité de fiabilité, notifications)."""

from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from course.models import Course
from notification.models import Notification
from onduty_backend import tests_outils as f
from paiement.models import Paiement
from paiement.services import campay

from .models import Trajet


class EtatEtOrdreTests(TestCase):
    def setUp(self):
        self.transporteur = f.utilisateur("690000002", transporteur=True, vehicule="pick-up")
        self.api = APIClient()
        self.api.force_authenticate(self.transporteur)

    def test_etats_et_ordre(self):
        maintenant = timezone.now()
        passe = f.trajet(self.transporteur)
        Trajet.objects.filter(pk=passe.pk).update(date_depart=maintenant - timedelta(days=2))
        aujourd_hui = f.trajet(self.transporteur)
        Trajet.objects.filter(pk=aujourd_hui.pk).update(
            date_depart=timezone.localtime().replace(hour=23, minute=59)
        )
        loin = f.trajet(self.transporteur, jours=10)
        proche = f.trajet(self.transporteur, jours=2)

        donnees = self.api.get("/api/trajets/").data
        self.assertEqual([t["id"] for t in donnees], [proche.pk, loin.pk, aujourd_hui.pk, passe.pk])
        self.assertEqual([t["etat"] for t in donnees], ["actif", "actif", "en_cours", "passe"])
        self.assertEqual(donnees[0]["type_vehicule"], "pick-up")


class ModificationTests(TestCase):
    def setUp(self):
        self.transporteur = f.utilisateur("690000002", transporteur=True)
        self.trajet = f.trajet(self.transporteur, capacite=100)
        self.api = APIClient()
        self.api.force_authenticate(self.transporteur)

    def patch(self, **donnees):
        return self.api.patch(f"/api/trajets/{self.trajet.pk}/", donnees, format="json")

    def test_sans_course_tout_est_modifiable(self):
        reponse = self.patch(destination="Bafoussam", capacite_disponible_kg=50)
        self.assertEqual(reponse.status_code, 200, reponse.data)
        self.assertEqual(reponse.data["destination"], "Bafoussam")

    def test_avec_course_seule_la_capacite(self):
        f.course(f.demande(f.utilisateur("690000001"), poids=30), self.trajet, statut="reservee")
        self.assertEqual(self.patch(destination="Bafoussam").status_code, 400)
        reponse = self.patch(capacite_disponible_kg=20)
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("30", str(reponse.data))
        reponse = self.patch(capacite_disponible_kg=40)
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.data["capacite_restante_kg"], Decimal("10"))

    def test_trajet_en_cours_non_modifiable(self):
        Trajet.objects.filter(pk=self.trajet.pk).update(date_depart=timezone.now() - timedelta(days=1))
        self.assertEqual(self.patch(capacite_disponible_kg=50).status_code, 400)
        self.assertEqual(self.api.delete(f"/api/trajets/{self.trajet.pk}/").status_code, 400)
        self.assertEqual(self.api.get(f"/api/matching/trajet/{self.trajet.pk}/").status_code, 400)

    def test_statut_non_modifiable_par_le_transporteur(self):
        self.patch(statut="complet")
        self.trajet.refresh_from_db()
        self.assertEqual(self.trajet.statut, "actif")


@override_settings(CAMPAY_USERNAME="app", CAMPAY_PASSWORD="x", CAMPAY_FRAIS_POURCENT=2)
class SuppressionTests(TestCase):
    def setUp(self):
        self.transporteur = f.utilisateur("690000002", transporteur=True)
        self.trajet = f.trajet(self.transporteur)
        self.client_paye = f.utilisateur("690000001", "Payé")
        self.client_reserve = f.utilisateur("690000003", "Réservé")
        self.course_payee = f.course(f.demande(self.client_paye, montant=2000), self.trajet, statut="payee")
        Paiement.objects.create(
            course=self.course_payee, montant_course=2000, commission=100, frais=80, montant=2180,
            statut=Paiement.StatutPaiement.BLOQUE_ESCROW, reference_transaction="ref-test",
        )
        self.course_reservee = f.course(f.demande(self.client_reserve), self.trajet, statut="reservee")
        self.api = APIClient()
        self.api.force_authenticate(self.transporteur)

    @mock.patch.object(campay, "envoyer", return_value={"reference": "r", "status": "SUCCESSFUL"})
    def test_suppression(self, envoyer):
        reponse = self.api.delete(f"/api/trajets/{self.trajet.pk}/")
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.data["courses_annulees"], 2)

        for course in (self.course_payee, self.course_reservee):
            course.refresh_from_db()
            self.assertEqual((course.statut, course.motif_annulation), ("annulee", "suppression_trajet"))
        # Remboursement du prix de la course seulement
        envoyer.assert_called_once()
        self.assertEqual(envoyer.call_args.args[:2], (Decimal("2000.00"), "690000001"))
        # Notifications aux deux clients
        for client in (self.client_paye, self.client_reserve):
            self.assertTrue(Notification.objects.filter(utilisateur=client, titre__icontains="annulée").exists())
        # Pénalité : −5 points par course annulée
        self.transporteur.refresh_from_db()
        from evaluation.services.fiabilite import get_details_fiabilite

        self.assertEqual(get_details_fiabilite(self.transporteur)["penalite_courses_annulees_trajet"], 10.0)
        # Sans historique : 50 × 0,5 (notes) + 100 × 0,3 (ponctualité) − 2 × 5 = 45
        self.assertEqual(self.transporteur.score_fiabilite, Decimal("45"))
        # Les demandes redeviennent disponibles au matching
        from matching.services.matching import demande_a_une_course_active

        self.assertFalse(demande_a_une_course_active(self.course_reservee.demande))
        self.assertFalse(Trajet.objects.exclude(statut="supprime").exists())

    def test_courses_livrees_conservees(self):
        Course.objects.filter(pk=self.course_reservee.pk).update(statut="livree")
        with mock.patch.object(campay, "envoyer", return_value={"reference": "r", "status": "SUCCESSFUL"}):
            reponse = self.api.delete(f"/api/trajets/{self.trajet.pk}/")
        self.assertEqual(reponse.data["courses_annulees"], 1)
        self.course_reservee.refresh_from_db()
        self.assertEqual(self.course_reservee.statut, "livree")
