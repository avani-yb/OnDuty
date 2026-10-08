"""Suivi GPS : envoi par le transporteur, lecture par les clients de la course."""

from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from onduty_backend import tests_outils as f

from .models import Course, PositionTransporteur


def api_de(utilisateur):
    api = APIClient()
    api.force_authenticate(utilisateur)
    return api


class SuiviTests(TestCase):
    def setUp(self):
        self.client_u = f.utilisateur("690000001", "Client")
        self.destinataire = f.utilisateur("690000003", "Dest")
        self.transporteur = f.utilisateur("690000002", "Chauffeur", transporteur=True)
        demande = f.demande(self.client_u)
        demande.destinataire = self.destinataire
        demande.save()
        self.course = f.course(demande, f.trajet(self.transporteur), statut="payee")
        self.api_t = api_de(self.transporteur)

    def envoyer(self, lat=4.05, lng=9.7):
        return self.api_t.post("/api/positions/", {"latitude": lat, "longitude": lng, "precision": 12})

    def test_pas_de_suivi_avant_le_depart(self):
        self.assertFalse(self.api_t.get("/api/positions/").data["suivi_actif"])
        self.assertEqual(self.envoyer().data["courses"], [])
        self.assertFalse(api_de(self.client_u).get(f"/api/courses/{self.course.pk}/suivi/").data["actif"])

    def test_suivi_du_depart_a_la_livraison(self):
        Course.objects.filter(pk=self.course.pk).update(statut="depart")
        reponse = self.envoyer()
        self.assertEqual((reponse.status_code, reponse.data["courses"]), (201, [self.course.pk]))

        # Envoi trop rapproché : ignoré
        self.assertEqual(self.envoyer(4.06, 9.71).data["courses"], [])
        PositionTransporteur.objects.update(date=timezone.now() - timedelta(minutes=1))
        self.envoyer(4.07, 9.72)

        for personne in (self.client_u, self.destinataire):
            donnees = api_de(personne).get(f"/api/courses/{self.course.pk}/suivi/").data
            self.assertTrue(donnees["actif"])
            self.assertEqual(donnees["derniere_position"]["latitude"], 4.07)
            self.assertEqual(donnees["trace"], [[4.05, 9.7], [4.07, 9.72]])
        self.assertTrue(api_de(self.client_u).get(f"/api/courses/{self.course.pk}/").data["suivi_disponible"])

        # Livrée : plus de suivi, le téléphone peut arrêter d'envoyer
        Course.objects.filter(pk=self.course.pk).update(statut="livree")
        self.assertFalse(api_de(self.client_u).get(f"/api/courses/{self.course.pk}/suivi/").data["actif"])
        self.assertFalse(self.envoyer().data["suivi_actif"])

    def test_inaccessible_aux_autres(self):
        Course.objects.filter(pk=self.course.pk).update(statut="en_route")
        autre = f.utilisateur("690000009")
        self.assertEqual(api_de(autre).get(f"/api/courses/{self.course.pk}/suivi/").status_code, 404)

    def test_coordonnees_invalides(self):
        Course.objects.filter(pk=self.course.pk).update(statut="depart")
        self.assertEqual(self.envoyer(lat=120).status_code, 400)

    def test_purge_apres_un_mois(self):
        import io

        from django.core.management import call_command

        Course.objects.filter(pk=self.course.pk).update(statut="depart")
        self.envoyer()
        il_y_a_40_jours = timezone.now() - timedelta(days=40)
        PositionTransporteur.objects.update(date=il_y_a_40_jours)
        Course.objects.filter(pk=self.course.pk).update(statut="livree", date_livraison=il_y_a_40_jours)
        sortie = io.StringIO()
        call_command("purger_positions", stdout=sortie)
        self.assertIn("1 position", sortie.getvalue())
        self.assertFalse(PositionTransporteur.objects.exists())


class LocalitesTests(TestCase):
    def test_liste_publique(self):
        donnees = APIClient().get("/api/localites/").data
        noms = [l["nom"] for l in donnees]
        self.assertIn("Yaoundé", noms)
        self.assertIn("Yagoua", noms)

    def test_nom_officiel_impose(self):
        transporteur = f.utilisateur("690000002", transporteur=True)
        api = api_de(transporteur)
        reponse = api.post("/api/trajets/", {
            "origine": "yaounde", "destination": "DOUALA",
            "date_depart": (timezone.now() + timedelta(days=2)).isoformat(),
            "capacite_disponible_kg": 100,
        })
        self.assertEqual(reponse.status_code, 201, reponse.data)
        self.assertEqual((reponse.data["origine"], reponse.data["destination"]), ("Yaoundé", "Douala"))
        reponse = api.post("/api/trajets/", {
            "origine": "Yaoundee", "destination": "Douala",
            "date_depart": (timezone.now() + timedelta(days=2)).isoformat(),
            "capacite_disponible_kg": 100,
        })
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("origine", reponse.data)


class JetonsFirebaseTests(TestCase):
    def test_un_telephone_change_de_compte(self):
        from notification.models import FCMToken

        ancien = f.utilisateur("690000001")
        nouveau = f.utilisateur("690000002")
        api_de(ancien).post("/api/fcm-tokens/", {"token": "jeton-tel"})
        api_de(nouveau).post("/api/fcm-tokens/", {"token": "jeton-tel"})
        self.assertFalse(FCMToken.objects.get(utilisateur=ancien).actif)
        self.assertTrue(FCMToken.objects.get(utilisateur=nouveau).actif)

        api_de(nouveau).post("/api/fcm-tokens/oublier/", {"token": "jeton-tel"})
        self.assertFalse(FCMToken.objects.get(utilisateur=nouveau).actif)

    def test_token_perime_desactive(self):
        from notification.models import FCMToken
        from notification.services import fcm

        utilisateur = f.utilisateur("690000001")
        FCMToken.objects.create(utilisateur=utilisateur, token="perime")
        with mock.patch.object(fcm.fcm_service, "envoyer_notification", return_value=(False, None, "unregistered", True)):
            fcm.envoyer_notification_utilisateur(utilisateur, "generique", "T", "C")
        self.assertFalse(FCMToken.objects.get().actif)
