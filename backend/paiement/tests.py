"""Tests du paiement CamPay et de l'escrow (aucun appel réseau : CamPay simulé)."""

from decimal import Decimal
from unittest import mock

import jwt
import requests
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from course.models import Course
from notification.models import Notification
from onduty_backend import tests_outils as f
from onduty_backend.services_externes import ServiceIndisponible, ServiceNonConfigure, ServiceTimeout

from .models import Paiement, Versement
from .services import campay, escrow, tarification

CAMPAY = {
    "CAMPAY_USERNAME": "app",
    "CAMPAY_PASSWORD": "secret",
    "CAMPAY_WEBHOOK_KEY": "cle-webhook-de-test-assez-longue-32o",
    "CAMPAY_ENV": "demo",
    "CAMPAY_TIMEOUT_SECONDS": 9,
    "CAMPAY_FRAIS_POURCENT": 2,
}


@override_settings(CAMPAY_FRAIS_POURCENT=2)
class TarificationTests(TestCase):
    def test_commission_5_pourcent_jusqu_a_10000(self):
        calcul = tarification.calculer(1000)
        self.assertEqual(calcul["commission"], Decimal("50"))
        self.assertEqual(calcul["frais"], Decimal("40"))  # 2 × 2 % × 1000
        self.assertEqual(calcul["total"], Decimal("1090"))
        self.assertEqual(tarification.calculer(10000)["commission"], Decimal("500"))

    def test_commission_10_pourcent_au_dela(self):
        calcul = tarification.calculer(10001)
        self.assertEqual(calcul["commission"], Decimal("1001"))  # arrondi supérieur
        self.assertEqual(calcul["frais"], Decimal("401"))
        self.assertEqual(calcul["total"], Decimal("11403"))


class NumeroTests(TestCase):
    def test_formats_acceptes(self):
        for numero in ("690000001", "237690000001", "+237 6 90 00 00 01", "00237690000001"):
            self.assertEqual(campay.normaliser_numero(numero), "237690000001")

    def test_formats_refuses(self):
        for numero in ("", "22233344", "590000001", "2376900"):
            with self.assertRaises(campay.NumeroInvalide):
                campay.normaliser_numero(numero)


def reponse(code=200, donnees=None):
    r = mock.Mock(status_code=code, text=str(donnees))
    r.json.return_value = donnees if donnees is not None else {}
    return r


@override_settings(**CAMPAY)
class ClientCampayTests(TestCase):
    def setUp(self):
        cache.clear()

    @mock.patch("paiement.services.campay.requests.request")
    def test_collecte_avec_jeton_et_timeout(self, requete):
        requete.side_effect = [
            reponse(200, {"token": "jeton-1", "expires_in": 3600}),
            reponse(200, {"reference": "ref-1", "ussd_code": "*126#", "operator": "MTN"}),
        ]
        resultat = campay.collecter(Decimal("1090"), "690000001", "OnDuty", "ext-1")
        self.assertEqual(resultat["reference"], "ref-1")

        (methode, url), kwargs = requete.call_args_list[0]
        self.assertEqual((methode, url), ("POST", "https://demo.campay.net/api/token/"))
        self.assertEqual(kwargs["json"], {"username": "app", "password": "secret"})
        (methode, url), kwargs = requete.call_args_list[1]
        self.assertEqual((methode, url), ("POST", "https://demo.campay.net/api/collect/"))
        self.assertEqual(kwargs["headers"]["Authorization"], "Token jeton-1")
        self.assertEqual(kwargs["timeout"], 9)
        self.assertEqual(kwargs["json"]["amount"], "1090")
        self.assertEqual(kwargs["json"]["from"], "237690000001")
        self.assertEqual(kwargs["json"]["external_reference"], "ext-1")

        # Le jeton est réutilisé (cache).
        requete.side_effect = [reponse(200, {"status": "PENDING", "reference": "ref-1"})]
        campay.statut_transaction("ref-1")
        self.assertEqual(requete.call_args.args, ("GET", "https://demo.campay.net/api/transaction/ref-1/"))

    @mock.patch("paiement.services.campay.requests.request", side_effect=requests.Timeout())
    def test_timeout(self, _):
        with self.assertRaises(ServiceTimeout):
            campay.statut_transaction("ref")

    @mock.patch("paiement.services.campay.requests.request")
    def test_refus_metier(self, requete):
        requete.side_effect = [
            reponse(200, {"token": "j"}),
            reponse(400, {"message": "Number not registered for mobile money"}),
        ]
        with self.assertRaises(campay.PaiementRefuse) as ctx:
            campay.collecter(100, "690000001", "x", "y")
        self.assertIn("mobile money", str(ctx.exception))

    @mock.patch("paiement.services.campay.requests.request")
    def test_identifiants_refuses(self, requete):
        requete.return_value = reponse(401, {"detail": "bad credentials"})
        with self.assertRaises(ServiceNonConfigure):
            campay.statut_transaction("ref")

    @override_settings(CAMPAY_USERNAME="")
    def test_non_configure(self):
        with self.assertRaises(ServiceNonConfigure):
            campay.statut_transaction("ref")

    def test_signature_webhook(self):
        bonne = jwt.encode({"reference": "r"}, "cle-webhook-de-test-assez-longue-32o", algorithm="HS256")
        mauvaise = jwt.encode({"reference": "r"}, "autre-cle-de-test-assez-longue-pour-hs", algorithm="HS256")
        self.assertTrue(campay.signature_webhook_valide(bonne))
        self.assertFalse(campay.signature_webhook_valide(mauvaise))
        self.assertFalse(campay.signature_webhook_valide(""))


@override_settings(**CAMPAY)
class ParcoursPaiementTests(TestCase):
    """Parcours complet : devis → paiement → escrow → livraison → versement."""

    def setUp(self):
        self.client_u = f.utilisateur("690000001", "Client")
        self.transporteur = f.utilisateur("690000002", "Chauffeur", transporteur=True)
        self.transporteur.numero_mobile_money = "237677000002"
        self.transporteur.save()
        self.destinataire = f.utilisateur("690000003", "Dest")
        self.demande = f.demande(self.client_u, montant=1000, telephone_destinataire="690000003")
        self.demande.destinataire = self.destinataire
        self.demande.save()
        self.course = f.course(self.demande, f.trajet(self.transporteur))
        self.api = APIClient()
        self.api.force_authenticate(self.client_u)

        patcher = mock.patch.multiple(
            campay,
            collecter=mock.DEFAULT,
            statut_transaction=mock.DEFAULT,
            envoyer=mock.DEFAULT,
        )
        self.cp = patcher.start()
        self.addCleanup(patcher.stop)
        self.cp["collecter"].return_value = {"reference": "col-1", "ussd_code": "*126#", "operator": "MTN"}
        self.cp["envoyer"].return_value = {"reference": "ver-1", "status": "SUCCESSFUL"}

    def payer(self):
        return self.api.post(f"/api/paiements/?course_id={self.course.pk}", {"numero": "690000001"})

    def test_devis(self):
        donnees = self.api.get(f"/api/paiements/devis/?course_id={self.course.pk}").data
        self.assertEqual(donnees["total"], Decimal("1090"))
        self.assertEqual(donnees["numero_defaut"], "690000001")

    def test_parcours_complet(self):
        reponse_ = self.payer()
        self.assertEqual(reponse_.status_code, 201, reponse_.data)
        self.assertEqual(reponse_.data["statut_affiche"], "En cours")
        self.assertEqual(reponse_.data["code_ussd"], "*126#")
        montant, numero = self.cp["collecter"].call_args.args[:2]
        self.assertEqual((montant, numero), (Decimal("1090"), "237690000001"))

        # Pas encore validé sur le téléphone
        self.cp["statut_transaction"].return_value = {"status": "PENDING"}
        paiement_id = reponse_.data["id"]
        self.assertEqual(self.api.post(f"/api/paiements/{paiement_id}/verifier/").data["statut"], "en_attente")

        # Validé : fonds en escrow, course payée
        self.cp["statut_transaction"].return_value = {"status": "SUCCESSFUL", "amount": "1090", "operator": "MTN"}
        donnees = self.api.post(f"/api/paiements/{paiement_id}/verifier/").data
        self.assertEqual((donnees["statut"], donnees["statut_affiche"]), ("bloque_escrow", "Effectué"))
        self.course.refresh_from_db()
        self.assertEqual(self.course.statut, Course.StatutCourse.PAYEE)
        self.assertTrue(Notification.objects.filter(utilisateur=self.destinataire, titre="Un colis vous est destiné").exists())

        # Côté transporteur : « En attente de livraison », sans la commission
        transporteur_api = APIClient()
        transporteur_api.force_authenticate(self.transporteur)
        vue = transporteur_api.get("/api/paiements/").data[0]
        self.assertEqual(vue["statut_affiche"], "En attente de livraison")
        self.assertNotIn("commission", vue)

        # Le transporteur ne peut ni libérer ni rembourser lui-même
        self.assertEqual(transporteur_api.post(f"/api/paiements/{paiement_id}/liberer/").status_code, 403)

        # Livraison, puis confirmation par le destinataire → versement du prix
        Course.objects.filter(pk=self.course.pk).update(statut=Course.StatutCourse.ARRIVEE)
        dest_api = APIClient()
        dest_api.force_authenticate(self.destinataire)
        self.assertEqual(dest_api.post(f"/api/courses/{self.course.pk}/confirmer_reception/").status_code, 200)
        montant, numero = self.cp["envoyer"].call_args.args[:2]
        self.assertEqual((montant, numero), (Decimal("1000"), "237677000002"))
        versement = Versement.objects.get()
        self.assertEqual(versement.statut, Versement.StatutVersement.EFFECTUE)
        self.assertEqual(transporteur_api.get("/api/paiements/").data[0]["statut_affiche"], "Reçu")

    def test_echec_puis_nouvel_essai(self):
        paiement_id = self.payer().data["id"]
        self.cp["statut_transaction"].return_value = {"status": "FAILED", "reason": "Solde insuffisant"}
        donnees = self.api.post(f"/api/paiements/{paiement_id}/verifier/").data
        self.assertEqual((donnees["statut_affiche"], donnees["message_erreur"]), ("Échoué", "Solde insuffisant"))
        self.course.refresh_from_db()
        self.assertEqual(self.course.statut, Course.StatutCourse.EN_ATTENTE_PAIEMENT)

        self.cp["collecter"].return_value = {"reference": "col-2", "operator": "ORANGE"}
        reponse_ = self.payer()
        self.assertEqual(reponse_.status_code, 201)
        paiement = Paiement.objects.get()
        self.assertEqual((paiement.reference_campay, paiement.methode), ("col-2", "orange_money"))
        self.assertEqual(paiement.historique[0]["reference_campay"], "col-1")

    def test_pas_de_double_paiement_en_attente(self):
        self.payer()
        self.assertEqual(self.payer().status_code, 400)

    def test_campay_indisponible_503(self):
        self.cp["collecter"].side_effect = ServiceIndisponible("campay", "panne")
        reponse_ = self.payer()
        self.assertEqual(reponse_.status_code, 503)
        self.assertEqual(Paiement.objects.count(), 0)

    def test_numero_invalide(self):
        reponse_ = self.api.post(f"/api/paiements/?course_id={self.course.pk}", {"numero": "12345"})
        self.assertEqual(reponse_.status_code, 400)
        self.assertIn("numero", reponse_.data)

    def test_annulation_rembourse_le_prix_seulement(self):
        paiement_id = self.payer().data["id"]
        self.cp["statut_transaction"].return_value = {"status": "SUCCESSFUL"}
        self.api.post(f"/api/paiements/{paiement_id}/verifier/")
        self.assertEqual(self.api.post(f"/api/courses/{self.course.pk}/annuler/").status_code, 200)
        montant, numero = self.cp["envoyer"].call_args.args[:2]
        self.assertEqual((montant, numero), (Decimal("1000"), "690000001"))
        self.assertEqual(Paiement.objects.get().statut, Paiement.StatutPaiement.REMBOURSE)
        self.assertEqual(Versement.objects.get().type_versement, "remboursement")

    def test_paiement_valide_apres_annulation_est_rembourse(self):
        paiement_id = self.payer().data["id"]
        self.api.post(f"/api/courses/{self.course.pk}/annuler/")
        self.cp["statut_transaction"].return_value = {"status": "SUCCESSFUL"}
        escrow.actualiser(Paiement.objects.get(pk=paiement_id))
        self.assertEqual(Paiement.objects.get().statut, Paiement.StatutPaiement.REMBOURSE)
        self.cp["envoyer"].assert_called_once()

    def test_versement_echoue_puis_relance(self):
        paiement_id = self.payer().data["id"]
        self.cp["statut_transaction"].return_value = {"status": "SUCCESSFUL"}
        self.api.post(f"/api/paiements/{paiement_id}/verifier/")
        Course.objects.filter(pk=self.course.pk).update(statut=Course.StatutCourse.ARRIVEE)
        self.cp["envoyer"].side_effect = ServiceIndisponible("campay", "panne")
        self.assertEqual(self.api.post(f"/api/courses/{self.course.pk}/confirmer_reception/").status_code, 200)
        versement = Versement.objects.get()
        self.assertEqual(versement.statut, Versement.StatutVersement.ECHOUE)

        self.cp["envoyer"].side_effect = None
        escrow.relancer_versement(versement)
        versement.refresh_from_db()
        self.assertEqual((versement.statut, versement.nb_tentatives), ("effectue", 2))

    def test_webhook(self):
        paiement_id = self.payer().data["id"]
        anonyme = APIClient()
        url = "/api/paiements/campay/webhook/"
        self.assertEqual(anonyme.get(url, {"reference": "col-1", "signature": "faux"}).status_code, 403)

        # Le webhook dit SUCCESSFUL, mais l'API (source de vérité) dit FAILED.
        self.cp["statut_transaction"].return_value = {"status": "FAILED"}
        signature = jwt.encode({"reference": "col-1"}, "cle-webhook-de-test-assez-longue-32o", algorithm="HS256")
        self.assertEqual(
            anonyme.get(url, {"reference": "col-1", "status": "SUCCESSFUL", "signature": signature}).status_code, 200
        )
        self.assertEqual(Paiement.objects.get(pk=paiement_id).statut, Paiement.StatutPaiement.ECHOUE)

    def test_autre_utilisateur_ne_peut_pas_payer(self):
        autre = APIClient()
        autre.force_authenticate(f.utilisateur("690000009"))
        self.assertEqual(
            autre.post(f"/api/paiements/?course_id={self.course.pk}", {"numero": "690000009"}).status_code, 404
        )

    def test_commande_actualiser_paiements(self):
        import io

        from django.core.management import call_command

        self.payer()
        self.cp["statut_transaction"].return_value = {"status": "SUCCESSFUL"}
        sortie = io.StringIO()
        call_command("actualiser_paiements", stdout=sortie)
        self.assertIn("1 mis à jour", sortie.getvalue())
