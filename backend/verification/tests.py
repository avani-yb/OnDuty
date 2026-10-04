"""Tests du KYC (validation manuelle et Smile Identity).

Aucun appel réseau : `requests.request` et les fonctions Smile sont simulés.
"""

import io
import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from unittest import mock

import requests
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient
from smile_id_core.Signature import Signature

from comptes.models import Utilisateur
from onduty_backend.services_externes import (
    ReponseInvalide,
    ServiceIndisponible,
    ServiceNonConfigure,
    ServiceTimeout,
)

from .models import Verification
from .services import smile_identity

DOSSIER_PRIVE = tempfile.mkdtemp()
SMILE = {
    "SMILE_PARTNER_ID": "1234",
    "SMILE_API_KEY": "cle-de-test",
    "SMILE_ENV": "sandbox",
    "SMILE_CALLBACK_URL": "https://exemple.org/api/kyc/smile-callback/",
    "SMILE_TIMEOUT_SECONDS": 7,
}


def photo(nom="photo.jpg"):
    tampon = io.BytesIO()
    Image.new("RGB", (40, 30), (120, 80, 60)).save(tampon, "JPEG")
    return SimpleUploadedFile(nom, tampon.getvalue(), content_type="image/jpeg")


def signature():
    return dict(Signature(SMILE["SMILE_PARTNER_ID"], SMILE["SMILE_API_KEY"]).generate_signature())


class BaseKYC(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(DOSSIER_PRIVE, ignore_errors=True)

    def setUp(self):
        # Le stockage privé est résolu au chargement du modèle : on redirige
        # les champs vers un dossier temporaire pour ne rien écrire ailleurs.
        stockage = FileSystemStorage(location=DOSSIER_PRIVE)
        for champ in ("cni_recto", "cni_verso", "selfie"):
            patcher = mock.patch.object(Verification._meta.get_field(champ), "storage", stockage)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.api = APIClient()
        self.utilisateur = Utilisateur.objects.create_user(
            telephone="690000010", nom="Test", prenom="Kyc", password="motdepasse-123"
        )
        self.api.force_authenticate(self.utilisateur)

    def soumettre(self, **photos):
        donnees = {"type_verification": "cni", "cni_recto": photo(), "selfie": photo(), "cni_verso": photo()}
        donnees.update(photos)
        donnees = {k: v for k, v in donnees.items() if v is not None}
        return self.api.post("/api/verifications/", donnees, format="multipart")


@override_settings(KYC_FOURNISSEUR="manuel")
class SoumissionManuelleTests(BaseKYC):
    def test_soumission_cni(self):
        reponse = self.soumettre()
        self.assertEqual(reponse.status_code, 201, reponse.data)
        self.assertEqual(reponse.data["statut"], "en_attente")
        self.assertEqual(reponse.data["fournisseur"], "manuel")
        self.assertEqual(sorted(reponse.data["documents"]), ["cni_recto", "cni_verso", "selfie"])
        self.assertNotIn("cni_recto", reponse.data)  # jamais d'URL renvoyée
        verification = Verification.objects.get()
        self.assertTrue(verification.cni_recto.path.startswith(str(Path(DOSSIER_PRIVE))))

    def test_selfie_obligatoire(self):
        reponse = self.soumettre(selfie=None)
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("selfie", reponse.data)

    def test_pas_de_double_soumission(self):
        self.soumettre()
        reponse = self.soumettre()
        self.assertEqual(reponse.status_code, 400)
        self.assertEqual(Verification.objects.count(), 1)

    def test_nouvelle_tentative_apres_rejet(self):
        self.soumettre()
        Verification.objects.update(statut=Verification.StatutVerification.REJETEE)
        reponse = self.soumettre()
        self.assertEqual(reponse.status_code, 201)
        self.assertEqual(reponse.data["numero_tentative"], 2)

    def test_document_accessible_au_seul_proprietaire(self):
        pk = self.soumettre().data["id"]
        reponse = self.api.get(f"/api/verifications/{pk}/document/selfie/")
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse["Content-Type"], "image/jpeg")

        autre = Utilisateur.objects.create_user(
            telephone="690000011", nom="Autre", prenom="User", password="motdepasse-123"
        )
        self.api.force_authenticate(autre)
        self.assertEqual(self.api.get(f"/api/verifications/{pk}/document/selfie/").status_code, 404)

    def test_document_pas_dans_media_public(self):
        pk = self.soumettre().data["id"]
        verification = Verification.objects.get(pk=pk)
        self.assertNotIn(str(settings.MEDIA_ROOT), verification.selfie.path)


@override_settings(KYC_FOURNISSEUR="smile", **SMILE)
class SoumissionSmileTests(BaseKYC):
    @mock.patch.object(smile_identity, "soumettre", return_value="onduty-1-abcd1234")
    def test_soumission_envoyee_a_smile(self, soumettre):
        reponse = self.soumettre()
        self.assertEqual(reponse.status_code, 201)
        self.assertEqual(reponse.data["fournisseur"], "smile")
        self.assertEqual(Verification.objects.get().job_id_fournisseur, "onduty-1-abcd1234")
        soumettre.assert_called_once()

    @mock.patch.object(smile_identity, "soumettre", side_effect=ServiceIndisponible("smile_identity", "panne"))
    def test_panne_smile_503_sans_trace(self, _):
        reponse = self.soumettre()
        self.assertEqual(reponse.status_code, 503)
        self.assertIn("indisponible", reponse.data["detail"])
        self.assertEqual(Verification.objects.count(), 0)
        fichiers = [f for _, _, noms in __import__("os").walk(DOSSIER_PRIVE) for f in noms]
        self.assertEqual(fichiers, [])

    @mock.patch.object(smile_identity, "soumettre", return_value="onduty-1-abcd1234")
    def test_document_vehicule_reste_manuel(self, soumettre):
        reponse = self.api.post("/api/verifications/", {"type_verification": "vehicule"}, format="multipart")
        self.assertEqual(reponse.status_code, 201)
        self.assertEqual(reponse.data["fournisseur"], "manuel")
        soumettre.assert_not_called()


@override_settings(KYC_FOURNISSEUR="smile", KYC_REQUIS_TRANSPORTEUR=True, **SMILE)
class CallbackSmileTests(BaseKYC):
    def setUp(self):
        super().setUp()
        with mock.patch.object(smile_identity, "soumettre", return_value="onduty-7-cafe0000"):
            self.verification = Verification.objects.get(pk=self.soumettre().data["id"])
        self.anonyme = APIClient()

    def callback(self, code="0810", job_id="onduty-7-cafe0000", sig=None):
        donnees = {
            "ResultCode": code,
            "ResultText": "Document Verified",
            "SmileJobID": "0000001",
            "PartnerParams": {"job_id": job_id, "user_id": "onduty-user-1", "job_type": 6},
            **(sig or signature()),
        }
        return self.anonyme.post("/api/kyc/smile-callback/", donnees, format="json")

    def test_callback_valide_debloque_transporteur(self):
        self.assertEqual(self.callback().status_code, 200)
        self.verification.refresh_from_db()
        self.assertEqual(self.verification.statut, "validee")
        self.assertIsNotNone(self.verification.date_traitement)
        self.assertEqual(self.verification.resultat_brut["ResultCode"], "0810")

        reponse = self.api.post("/api/vehicules/", {
            "type_vehicule": "camion", "marque": "Isuzu", "modele": "NPR",
            "immatriculation": "LT-1", "capacite_max_kg": 1000,
        })
        self.assertEqual(reponse.status_code, 201)

    def test_callback_rejet_puis_ignore_les_doublons(self):
        self.callback(code="0811")
        self.callback(code="0810")  # second callback ignoré
        self.verification.refresh_from_db()
        self.assertEqual(self.verification.statut, "rejetee")

    def test_callback_provisoire_a_revoir(self):
        self.callback(code="0814")
        self.verification.refresh_from_db()
        self.assertEqual(self.verification.statut, "a_revoir")
        self.assertIsNone(self.verification.date_traitement)

    def test_signature_invalide(self):
        reponse = self.callback(sig={"signature": "faux", "timestamp": "2026-10-03T10:00:00Z"})
        self.assertEqual(reponse.status_code, 403)
        self.verification.refresh_from_db()
        self.assertEqual(self.verification.statut, "en_attente")

    def test_job_inconnu(self):
        self.assertEqual(self.callback(job_id="inconnu").status_code, 404)

    @mock.patch.object(smile_identity, "consulter_statut", return_value={"ResultCode": "0810"})
    def test_actualiser_par_job_status(self, _):
        reponse = self.api.post(f"/api/verifications/{self.verification.pk}/actualiser/")
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.data["statut"], "validee")

    @mock.patch.object(smile_identity, "consulter_statut", return_value={"ResultCode": "0810"})
    def test_commande_actualiser_kyc(self, _):
        from django.core.management import call_command

        sortie = io.StringIO()
        call_command("actualiser_kyc", stdout=sortie)
        self.assertIn("1 mise(s) à jour", sortie.getvalue())


@override_settings(KYC_FOURNISSEUR="manuel", **SMILE)
class ClientSmileTests(BaseKYC):
    """Appels HTTP de smile_identity (requests simulé)."""

    def setUp(self):
        super().setUp()
        self.soumettre()
        self.verification = Verification.objects.get()

    @staticmethod
    def reponse(code=200, donnees=None):
        r = mock.Mock(status_code=code, text=json.dumps(donnees or {}))
        r.json.return_value = donnees or {}
        return r

    @mock.patch("verification.services.smile_identity.requests.request")
    def test_soumettre(self, requete):
        requete.side_effect = [
            self.reponse(200, {"upload_url": "https://envoi.exemple/zip", "smile_job_id": "42"}),
            self.reponse(200),
        ]
        job_id = smile_identity.soumettre(self.verification)
        self.assertTrue(job_id.startswith(f"onduty-{self.verification.pk}-"))

        (methode, url), kwargs = requete.call_args_list[0]
        self.assertEqual((methode, url), ("POST", "https://testapi.smileidentity.com/v1/upload"))
        self.assertEqual(kwargs["timeout"], 7)
        self.assertEqual(kwargs["json"]["partner_params"]["job_type"], 6)
        self.assertEqual(kwargs["json"]["callback_url"], SMILE["SMILE_CALLBACK_URL"])

        (methode, url), kwargs = requete.call_args_list[1]
        self.assertEqual((methode, url), ("PUT", "https://envoi.exemple/zip"))
        self.assertEqual(kwargs["timeout"], 7)
        with zipfile.ZipFile(io.BytesIO(kwargs["data"])) as archive:
            info = json.loads(archive.read("info.json"))
        self.assertEqual(info["id_info"], {"country": "CM", "id_type": "IDENTITY_CARD"})
        self.assertEqual(sorted(i["image_type_id"] for i in info["images"]), [2, 3, 7])

    @mock.patch("verification.services.smile_identity.requests.request", side_effect=requests.Timeout())
    def test_timeout(self, _):
        with self.assertRaises(ServiceTimeout):
            smile_identity.soumettre(self.verification)

    @mock.patch("verification.services.smile_identity.requests.request", side_effect=requests.ConnectionError())
    def test_reseau(self, _):
        with self.assertRaises(ServiceIndisponible):
            smile_identity.soumettre(self.verification)

    @mock.patch("verification.services.smile_identity.requests.request")
    def test_cle_refusee(self, requete):
        requete.return_value = self.reponse(401, {"error": "unauthorized"})
        with self.assertRaises(ServiceNonConfigure):
            smile_identity.soumettre(self.verification)

    @override_settings(SMILE_API_KEY="")
    def test_cle_absente(self):
        with self.assertRaises(ServiceNonConfigure):
            smile_identity.soumettre(self.verification)

    @mock.patch("verification.services.smile_identity.requests.request")
    def test_job_status(self, requete):
        self.verification.job_id_fournisseur = "onduty-1-x"
        requete.return_value = self.reponse(200, {
            "job_complete": True, "result": {"ResultCode": "0810"}, **signature(),
        })
        self.assertEqual(smile_identity.consulter_statut(self.verification), {"ResultCode": "0810"})

        requete.return_value = self.reponse(200, {"job_complete": False, **signature()})
        self.assertIsNone(smile_identity.consulter_statut(self.verification))

        requete.return_value = self.reponse(200, {"job_complete": True, "signature": "faux", "timestamp": "t"})
        with self.assertRaises(ReponseInvalide):
            smile_identity.consulter_statut(self.verification)

    def test_interpreter(self):
        attendus = {"0810": "validee", "0811": "rejetee", "0813": "rejetee", "0816": "rejetee",
                    "0812": "a_revoir", "0814": "a_revoir", "": "a_revoir", "9999": "a_revoir"}
        for code, statut in attendus.items():
            self.assertEqual(smile_identity.interpreter({"ResultCode": code})[0], statut, code)
