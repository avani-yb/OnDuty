"""Courses : choix par le client ou par le transporteur, destinataire,
capacité restante, notifications."""

from decimal import Decimal

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from notification.models import Notification
from onduty_backend import tests_outils as f

from .models import Course


def api_de(utilisateur):
    api = APIClient()
    api.force_authenticate(utilisateur)
    return api


class ChoixParLeClientTests(TestCase):
    def setUp(self):
        self.client_u = f.utilisateur("690000001", "Client")
        self.transporteur = f.utilisateur("690000002", "Chauffeur", transporteur=True)
        self.trajet = f.trajet(self.transporteur, capacite=50)

    def reserver(self, demande):
        return api_de(self.client_u).post(
            f"/api/courses/?demande_id={demande.pk}", {"trajet_id": self.trajet.pk}
        )

    def test_reservation_notifie_le_transporteur(self):
        reponse = self.reserver(f.demande(self.client_u, poids=20))
        self.assertEqual(reponse.status_code, 201, reponse.data)
        self.assertEqual(reponse.data["role"], "client")
        notif = Notification.objects.get(utilisateur=self.transporteur)
        self.assertEqual(notif.titre, "Un client a choisi votre trajet")

    def test_capacite_restante(self):
        self.assertEqual(self.reserver(f.demande(self.client_u, poids=40)).status_code, 201)
        reponse = self.reserver(f.demande(self.client_u, poids=20))
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("Capacité", str(reponse.data))
        self.trajet.refresh_from_db()
        self.assertEqual(self.trajet.capacite_restante_kg, Decimal("10"))

    def test_une_seule_course_active_par_demande_mais_reprise_apres_annulation(self):
        demande = f.demande(self.client_u, poids=5)
        course_id = self.reserver(demande).data["id"]
        self.assertEqual(self.reserver(demande).status_code, 400)
        api_de(self.client_u).post(f"/api/courses/{course_id}/annuler/")
        self.assertEqual(self.reserver(demande).status_code, 201)


class ChoixParLeTransporteurTests(TestCase):
    def setUp(self):
        self.client_u = f.utilisateur("690000001", "Client")
        self.transporteur = f.utilisateur("690000002", "Chauffeur", transporteur=True)
        self.trajet = f.trajet(self.transporteur)
        self.demande = f.demande(self.client_u, montant=5000)

    def proposer(self, **extra):
        return api_de(self.transporteur).post(
            "/api/courses/proposer/",
            {"demande_id": self.demande.pk, "trajet_id": self.trajet.pk, **extra},
        )

    def test_proposition_puis_acceptation_par_le_client(self):
        reponse = self.proposer(montant="6000")
        self.assertEqual(reponse.status_code, 201, reponse.data)
        self.assertEqual(
            (reponse.data["statut"], reponse.data["initiee_par"], reponse.data["montant_convenu"]),
            ("proposition_montant", "transporteur", Decimal("6000")),
        )
        notif = Notification.objects.get(utilisateur=self.client_u)
        self.assertEqual(notif.titre, "Un transporteur a choisi votre demande")
        self.assertIn("prix modifié", notif.corps)

        reponse = api_de(self.client_u).post(f"/api/courses/{reponse.data['id']}/valider-montant/")
        self.assertEqual(reponse.data["statut"], "en_attente_paiement")

    def test_prix_du_client_par_defaut_et_refus(self):
        reponse = self.proposer()
        self.assertEqual(reponse.data["montant_convenu"], Decimal("5000"))
        api_de(self.client_u).post(f"/api/courses/{reponse.data['id']}/annuler/")
        self.assertTrue(
            Notification.objects.filter(utilisateur=self.transporteur, titre="Proposition refusée").exists()
        )
        # La demande revient dans le matching du trajet
        matching = api_de(self.transporteur).get(f"/api/matching/trajet/{self.trajet.pk}/").data
        self.assertEqual([r["demande"]["id"] for r in matching], [self.demande.pk])

    def test_demande_deja_prise_absente_du_matching(self):
        self.proposer()
        matching = api_de(self.transporteur).get(f"/api/matching/trajet/{self.trajet.pk}/").data
        self.assertEqual(matching, [])
        self.assertEqual(self.proposer().status_code, 400)

    def test_seul_le_proprietaire_du_trajet(self):
        autre = f.utilisateur("690000009", transporteur=True)
        reponse = api_de(autre).post(
            "/api/courses/proposer/", {"demande_id": self.demande.pk, "trajet_id": self.trajet.pk}
        )
        self.assertEqual(reponse.status_code, 400)

    def test_client_simple_refuse(self):
        reponse = api_de(f.utilisateur("690000008")).post(
            "/api/courses/proposer/", {"demande_id": self.demande.pk, "trajet_id": self.trajet.pk}
        )
        self.assertEqual(reponse.status_code, 403)


class DestinataireTests(TestCase):
    def setUp(self):
        self.client_u = f.utilisateur("690000001", "Client")
        self.transporteur = f.utilisateur("690000002", "Chauffeur", transporteur=True)
        self.destinataire = f.utilisateur("237690000003", "Dest")
        self.course = f.course(f.demande(self.client_u), f.trajet(self.transporteur), statut="payee")

    def lier_destinataire(self):
        demande = self.course.demande
        demande.destinataire = self.destinataire
        demande.save()

    def test_destinataire_voit_la_course_et_recoit_le_suivi(self):
        self.lier_destinataire()
        api = api_de(self.destinataire)
        donnees = api.get("/api/courses/").data
        self.assertEqual(([c["id"] for c in donnees], donnees[0]["role"]), ([self.course.pk], "destinataire"))

        api_de(self.transporteur).post(f"/api/courses/{self.course.pk}/depart/")
        self.assertTrue(Notification.objects.filter(utilisateur=self.destinataire, titre="Colis en route").exists())

        Course.objects.filter(pk=self.course.pk).update(statut="arrivee")
        self.assertTrue(api.get(f"/api/courses/{self.course.pk}/").data["peut_confirmer_reception"])
        self.assertEqual(api.post(f"/api/courses/{self.course.pk}/confirmer_reception/").status_code, 200)
        self.assertTrue(Notification.objects.filter(utilisateur=self.client_u, titre="Course terminée").exists())

    def test_destinataire_ne_peut_pas_annuler(self):
        self.lier_destinataire()
        self.assertEqual(api_de(self.destinataire).post(f"/api/courses/{self.course.pk}/annuler/").status_code, 403)

    def test_non_destinataire_ne_voit_rien(self):
        self.assertEqual(api_de(self.destinataire).get("/api/courses/").data, [])

    @override_settings(IA_FOURNISSEUR="simulation")
    def test_numero_resolu_a_la_creation_de_la_demande(self):
        from datetime import timedelta

        from django.utils import timezone

        reponse = api_de(self.client_u).post("/api/demandes/", {
            "origine": "Douala", "destination": "Yaoundé",
            "date_souhaitee": (timezone.now() + timedelta(days=2)).isoformat(),
            "description": "Sac", "poids_estime_kg": "5", "montant_propose": "3000",
            "video_url": "https://exemple.org/v.mp4",
            "telephone_destinataire": "+237 6 90 00 00 03",
        })
        self.assertEqual(reponse.status_code, 201, reponse.data)
        self.assertEqual(reponse.data["demande"]["destinataire"]["id"], self.destinataire.pk)


class NotificationsTests(TestCase):
    def test_enregistree_sans_jeton_firebase_et_compteur(self):
        utilisateur = f.utilisateur("690000001")
        from notification.services.notifier import notifier

        notifier(utilisateur, "generique", "Titre", "Corps", course_id=3)
        api = api_de(utilisateur)
        self.assertEqual(api.get("/api/notifications/compteur/").data, {"non_lues": 1})
        self.assertEqual(api.get("/api/notifications/").data[0]["data"], {"course_id": "3"})
        api.post("/api/notifications/tout_marquer_lu/")
        self.assertEqual(api.get("/api/notifications/compteur/").data, {"non_lues": 0})


class IncidentEtLitigeTests(TestCase):
    def setUp(self):
        self.client_u = f.utilisateur("690000001", "Client")
        self.transporteur = f.utilisateur("690000002", "Chauffeur", transporteur=True)
        self.course = f.course(f.demande(self.client_u), f.trajet(self.transporteur), statut="payee")

    def test_incident_notifie_le_client(self):
        reponse = api_de(self.transporteur).post(
            "/api/incidents/", {"course_id": self.course.pk, "description": "Pneu crevé"}
        )
        self.assertEqual(reponse.status_code, 201, reponse.data)
        notif = Notification.objects.get(utilisateur=self.client_u)
        self.assertIn("Pneu crevé", notif.corps)

    def test_litige_notifie_l_autre_partie(self):
        reponse = api_de(self.client_u).post(
            "/api/litiges/", {"course_id": self.course.pk, "motif": "Colis abîmé"}
        )
        self.assertEqual(reponse.status_code, 201, reponse.data)
        self.assertTrue(
            Notification.objects.filter(utilisateur=self.transporteur, titre="Litige ouvert sur une course").exists()
        )
