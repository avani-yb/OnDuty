"""Tests du contrôle IA des demandes (simulation, Groq, Google Cloud Vision).

Aucun appel réseau : Groq et Vision sont remplacés par des mocks.
"""

import shutil
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest import mock

import cv2
import numpy as np
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from comptes.models import Utilisateur
from onduty_backend.services_externes import (
    ReponseInvalide,
    ServiceIndisponible,
    ServiceNonConfigure,
    ServiceTimeout,
)

from .models import Demande
from .services import analyse_groq, vision_google

MEDIA_TEST = tempfile.mkdtemp()


def video_test():
    """Petite vidéo valide (10 images unies) générée à la volée."""
    chemin = Path(MEDIA_TEST) / "source.avi"
    ecrivain = cv2.VideoWriter(str(chemin), cv2.VideoWriter_fourcc(*"MJPG"), 5, (64, 64))
    for i in range(10):
        ecrivain.write(np.full((64, 64, 3), i * 20, dtype=np.uint8))
    ecrivain.release()
    return SimpleUploadedFile("article.avi", chemin.read_bytes(), content_type="video/x-msvideo")


def groq_ok(objets=(), coherent=True, motif_incoherence=None, alteration=False, motif_alteration=None):
    return {
        "objets_detectes": [
            {"objet": o, "categorie": c, "confiance": conf} for o, c, conf in objets
        ],
        "coherent": coherent,
        "motif_incoherence": motif_incoherence,
        "alteration_suspecte": alteration,
        "motif_alteration": motif_alteration,
        "details_visuels": {
            "type": "sac", "marque": None, "couleur": "noir", "etat": "neuf", "contenant": "sac plastique",
        },
    }


def vision_ok(*etiquettes):
    return {
        "etiquettes": [{"nom": n, "score": s} for n, s in etiquettes],
        "nb_images_analysees": 5,
    }


@override_settings(MEDIA_ROOT=MEDIA_TEST)
class ControleIATests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEST, ignore_errors=True)

    def setUp(self):
        # Groq est simulé dans tous les tests (réponse « valide » par défaut).
        patcher = mock.patch.object(analyse_groq, "analyser", return_value=groq_ok())
        self.groq = patcher.start()
        self.addCleanup(patcher.stop)
        self.api = APIClient()
        self.utilisateur = Utilisateur.objects.create_user(
            telephone="690000001", nom="Test", prenom="Client", password="motdepasse-123"
        )
        self.api.force_authenticate(self.utilisateur)

    def donnees(self, description="Sac de vêtements", video=True):
        donnees = {
            "origine": "Douala",
            "destination": "Yaoundé",
            "date_souhaitee": (timezone.now() + timedelta(days=2)).isoformat(),
            "description": description,
            "poids_estime_kg": "5",
            "montant_propose": "3000",
        }
        if video:
            donnees["video"] = video_test()
        return donnees

    def creer(self, **kwargs):
        return self.api.post("/api/demandes/", self.donnees(**kwargs), format="multipart")

    # --- Simulation (mode par défaut) ---

    @override_settings(IA_FOURNISSEUR="simulation")
    def test_simulation_valide(self):
        reponse = self.creer()
        self.assertEqual(reponse.status_code, 201)
        self.assertEqual(reponse.data["demande"]["statut"], "publiee")
        self.groq.assert_not_called()

    @override_settings(IA_FOURNISSEUR="simulation")
    def test_simulation_rejette_mot_interdit(self):
        reponse = self.creer(description="Carton de munitions")
        self.assertEqual(reponse.data["controle_ia"]["verdict"], "rejete")

    # --- Mode réel, Groq seul (IA_DETECTION=groq, défaut) ---

    @override_settings(IA_FOURNISSEUR="reel")
    def test_reel_video_obligatoire(self):
        reponse = self.creer(video=False)
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("video", reponse.data)

    @override_settings(IA_FOURNISSEUR="reel", IA_DETECTION="groq")
    @mock.patch.object(vision_google, "analyser_images")
    def test_groq_seul_valide_et_garde_details(self, vision):
        reponse = self.creer()
        self.assertEqual(reponse.status_code, 201)
        controle = reponse.data["controle_ia"]
        self.assertEqual(controle["verdict"], "valide")
        self.assertEqual(controle["resultat_coherence"]["verdict_coherence"], "coherent")
        self.assertEqual(controle["resultat_coherence"]["détails_visuels"]["couleur"], "noir")
        vision.assert_not_called()
        images, description = self.groq.call_args.args
        self.assertEqual(description, "Sac de vêtements")
        self.assertTrue(images and all(isinstance(i, bytes) for i in images))

    @override_settings(IA_FOURNISSEUR="reel", IA_DETECTION="groq", GROQ_SEUIL_CONFIANCE=0.6)
    def test_groq_objet_interdit(self):
        self.groq.return_value = groq_ok(objets=[("pistolet", "interdit", 0.9)])
        reponse = self.creer()
        controle = reponse.data["controle_ia"]
        self.assertEqual(controle["verdict"], "rejete")
        self.assertIn("pistolet", controle["motif_rejet"])
        self.assertEqual(reponse.data["demande"]["statut"], "rejetee")

    @override_settings(IA_FOURNISSEUR="reel", IA_DETECTION="groq", GROQ_SEUIL_CONFIANCE=0.6)
    def test_groq_interdit_peu_sur_et_sensible_non_rejetes(self):
        self.groq.return_value = groq_ok(
            objets=[("pistolet", "interdit", 0.3), ("médicaments", "sensible", 0.9)]
        )
        controle = self.creer().data["controle_ia"]
        self.assertEqual(controle["verdict"], "valide")
        self.assertEqual(len(controle["resultat_detection_objets"]["objets_detectes"]), 2)

    @override_settings(IA_FOURNISSEUR="reel", IA_DETECTION="groq")
    def test_groq_incoherence(self):
        self.groq.return_value = groq_ok(coherent=False, motif_incoherence="On voit des bouteilles.")
        controle = self.creer().data["controle_ia"]
        self.assertEqual(controle["verdict"], "rejete")
        self.assertIn("bouteilles", controle["motif_rejet"])

    @override_settings(IA_FOURNISSEUR="reel", IA_DETECTION="groq")
    def test_groq_alteration(self):
        self.groq.return_value = groq_ok(alteration=True, motif_alteration="Scellé déchiré.")
        controle = self.creer().data["controle_ia"]
        self.assertEqual(controle["verdict"], "rejete")
        self.assertIn("Scellé déchiré", controle["motif_rejet"])

    @override_settings(IA_FOURNISSEUR="reel", IA_DETECTION="groq")
    def test_reel_video_illisible_rejetee(self):
        donnees = self.donnees(video=False)
        donnees["video"] = SimpleUploadedFile("x.mp4", b"pas une video", content_type="video/mp4")
        reponse = self.api.post("/api/demandes/", donnees, format="multipart")
        self.assertEqual(reponse.data["controle_ia"]["verdict"], "rejete")
        self.assertIn("illisible", reponse.data["controle_ia"]["motif_rejet"])
        self.groq.assert_not_called()

    @override_settings(IA_FOURNISSEUR="reel", IA_DETECTION="groq")
    def test_panne_groq_503_puis_relance(self):
        self.groq.side_effect = ServiceIndisponible("groq", "limite de débit")
        reponse = self.creer()
        self.assertEqual(reponse.status_code, 503)
        self.assertIn("indisponible", reponse.data["detail"])
        demande = Demande.objects.get(pk=reponse.data["demande"]["id"])
        self.assertEqual(demande.statut, Demande.StatutDemande.EN_COURS_CONTROLE)
        self.assertEqual(demande.controles.count(), 0)

        self.groq.side_effect = None
        reponse = self.api.post(f"/api/demandes/{demande.pk}/relancer/")
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.data["demande"]["statut"], "publiee")

    @override_settings(IA_FOURNISSEUR="reel", IA_DETECTION="groq")
    def test_relance_avec_nouvelle_video(self):
        self.groq.return_value = groq_ok(objets=[("fusil", "interdit", 0.99)])
        demande_id = self.creer().data["demande"]["id"]
        self.groq.return_value = groq_ok()
        reponse = self.api.post(
            f"/api/demandes/{demande_id}/relancer/",
            {"video": video_test(), "description": "Sac de riz"},
            format="multipart",
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.data["controle_ia"]["numero_tentative"], 2)
        self.assertEqual(reponse.data["demande"]["description"], "Sac de riz")

    @override_settings(IA_FOURNISSEUR="simulation")
    def test_relance_refusee_si_publiee(self):
        demande_id = self.creer().data["demande"]["id"]
        reponse = self.api.post(f"/api/demandes/{demande_id}/relancer/")
        self.assertEqual(reponse.status_code, 400)

    # --- Mode réel avec Google Vision en plus (IA_DETECTION=google) ---

    @override_settings(IA_FOURNISSEUR="reel", IA_DETECTION="google", VISION_SEUIL_CONFIANCE=0.7)
    @mock.patch.object(vision_google, "analyser_images")
    def test_vision_valide_et_transmet_etiquettes_a_groq(self, analyser):
        analyser.return_value = vision_ok(("bag", 0.95), ("textile", 0.9))
        reponse = self.creer()
        self.assertEqual(reponse.data["demande"]["statut"], "publiee")
        self.assertEqual(self.groq.call_args.kwargs["etiquettes_vision"][0]["nom"], "bag")

    @override_settings(IA_FOURNISSEUR="reel", IA_DETECTION="google", VISION_SEUIL_CONFIANCE=0.7)
    @mock.patch.object(vision_google, "analyser_images")
    def test_vision_rejette_arme_detectee(self, analyser):
        analyser.return_value = vision_ok(("gun", 0.93), ("bag", 0.8))
        controle = self.creer().data["controle_ia"]
        self.assertEqual(controle["verdict"], "rejete")
        self.assertIn("gun", controle["motif_rejet"])

    @override_settings(IA_FOURNISSEUR="reel", IA_DETECTION="google", VISION_SEUIL_CONFIANCE=0.7)
    @mock.patch.object(vision_google, "analyser_images")
    def test_vision_ignore_score_sous_le_seuil(self, analyser):
        analyser.return_value = vision_ok(("gun", 0.4))
        controle = self.creer().data["controle_ia"]
        self.assertEqual(controle["verdict"], "valide")

    @override_settings(IA_FOURNISSEUR="reel", IA_DETECTION="google")
    @mock.patch.object(vision_google, "analyser_images")
    def test_panne_vision_503(self, analyser):
        analyser.side_effect = ServiceTimeout("google_vision", "pas de réponse")
        reponse = self.creer()
        self.assertEqual(reponse.status_code, 503)
        self.groq.assert_not_called()


class VisionGoogleTests(TestCase):
    """Traduction des erreurs du SDK Google en erreurs internes."""

    def setUp(self):
        vision_google._client = None

    def tearDown(self):
        vision_google._client = None

    @override_settings(GOOGLE_APPLICATION_CREDENTIALS="")
    def test_cle_absente(self):
        with self.assertRaises(ServiceNonConfigure):
            vision_google.analyser_images([b"x"], timeout=5)

    @override_settings(GOOGLE_APPLICATION_CREDENTIALS="secrets/inexistant.json")
    def test_fichier_cle_introuvable(self):
        with self.assertRaises(ServiceNonConfigure):
            vision_google.analyser_images([b"x"], timeout=5)

    def _avec_erreur(self, erreur):
        client = mock.Mock()
        client.batch_annotate_images.side_effect = erreur
        vision_google._client = client
        return vision_google.analyser_images([b"x"], timeout=5)

    def test_timeout(self):
        from google.api_core import exceptions as gexc

        with self.assertRaises(ServiceTimeout):
            self._avec_erreur(gexc.DeadlineExceeded("lent"))

    def test_indisponible(self):
        from google.api_core import exceptions as gexc

        with self.assertRaises(ServiceIndisponible):
            self._avec_erreur(gexc.ServiceUnavailable("panne"))

    def test_authentification_refusee(self):
        from google.api_core import exceptions as gexc

        with self.assertRaises(ServiceNonConfigure):
            self._avec_erreur(gexc.PermissionDenied("API non activée"))

    def test_agregation_score_max(self):
        def reponse_image(nom, score):
            annotation = mock.Mock(description=nom, score=score)
            resultat = mock.Mock(label_annotations=[annotation], localized_object_annotations=[])
            resultat.error.message = ""
            return resultat

        client = mock.Mock()
        client.batch_annotate_images.return_value = mock.Mock(
            responses=[reponse_image("Gun", 0.6), reponse_image("Gun", 0.9)]
        )
        vision_google._client = client

        resultat = vision_google.analyser_images([b"a", b"b"], timeout=5)
        self.assertEqual(resultat["etiquettes"], [{"nom": "gun", "score": 0.9}])
        self.assertEqual(resultat["nb_images_analysees"], 2)


class AnalyseGroqTests(TestCase):
    """Validation des réponses et traduction des erreurs du SDK Groq."""

    def setUp(self):
        analyse_groq._client = None

    def tearDown(self):
        analyse_groq._client = None

    def test_reponse_normalisee(self):
        resultat = analyse_groq.valider_reponse(
            'Voici : {"objets_detectes": [{"objet": "fusil", "categorie": "INTERDIT", "confiance": 1.7},'
            ' {"objet": "x", "categorie": "inconnue", "confiance": "abc"}],'
            ' "coherent": false, "motif_incoherence": "  ", "details_visuels": {"couleur": "rouge"}}'
        )
        self.assertEqual(
            resultat["objets_detectes"][0],
            {"objet": "fusil", "categorie": "interdit", "confiance": 1.0},
        )
        self.assertEqual(resultat["objets_detectes"][1]["categorie"], "autorise")
        self.assertEqual(resultat["objets_detectes"][1]["confiance"], 0.0)
        self.assertFalse(resultat["coherent"])
        self.assertIsNone(resultat["motif_incoherence"])
        self.assertFalse(resultat["alteration_suspecte"])
        self.assertEqual(resultat["details_visuels"]["couleur"], "rouge")
        self.assertIsNone(resultat["details_visuels"]["marque"])

    def test_reponse_invalide(self):
        for contenu in ("pas du json", '{"objets_detectes": []}', '{"coherent": "oui"}', ""):
            with self.assertRaises(ReponseInvalide):
                analyse_groq.valider_reponse(contenu)

    @override_settings(GROQ_API_KEY="")
    def test_cle_absente(self):
        with self.assertRaises(ServiceNonConfigure):
            analyse_groq.analyser([b"x"], "sac", timeout=5)

    def _avec_erreur(self, erreur):
        client = mock.Mock()
        client.chat.completions.create.side_effect = erreur
        analyse_groq._client = client
        return analyse_groq.analyser([b"x"], "sac", timeout=5)

    @staticmethod
    def _erreur_http(classe, code):
        import httpx

        requete = httpx.Request("POST", "https://api.groq.com")
        return classe("erreur", response=httpx.Response(code, request=requete), body=None)

    def test_timeout(self):
        import groq
        import httpx

        with self.assertRaises(ServiceTimeout):
            self._avec_erreur(groq.APITimeoutError(request=httpx.Request("POST", "https://api.groq.com")))

    def test_limite_debit(self):
        import groq

        from onduty_backend.services_externes import ServiceSature

        with self.assertRaises(ServiceSature) as ctx:
            self._avec_erreur(self._erreur_http(groq.RateLimitError, 429))
        self.assertIn("minute", ctx.exception.message_utilisateur)

    def test_cle_refusee(self):
        import groq

        with self.assertRaises(ServiceNonConfigure):
            self._avec_erreur(self._erreur_http(groq.AuthenticationError, 401))

    def test_modele_incompatible(self):
        import groq

        with self.assertRaises(ServiceNonConfigure):
            self._avec_erreur(self._erreur_http(groq.BadRequestError, 400))

    def test_erreur_serveur(self):
        import groq

        with self.assertRaises(ServiceIndisponible):
            self._avec_erreur(self._erreur_http(groq.InternalServerError, 503))
