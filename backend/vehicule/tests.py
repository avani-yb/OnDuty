from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from comptes.models import Utilisateur
from verification.models import Verification

VEHICULE = {
    "type_vehicule": "camion",
    "marque": "Isuzu",
    "modele": "NPR",
    "immatriculation": "LT-123-AB",
    "capacite_max_kg": 3000,
}


class DevenirTransporteurTests(TestCase):
    """Le rôle Transporteur exige une CNI validée (docs/03, section 5)."""

    def setUp(self):
        self.api = APIClient()
        self.utilisateur = Utilisateur.objects.create_user(
            telephone="690000002", nom="Test", prenom="Chauffeur", password="motdepasse-123"
        )
        self.api.force_authenticate(self.utilisateur)

    @override_settings(KYC_REQUIS_TRANSPORTEUR=True)
    def test_refuse_sans_cni_validee(self):
        reponse = self.api.post("/api/vehicules/", VEHICULE)
        self.assertEqual(reponse.status_code, 403)
        self.utilisateur.refresh_from_db()
        self.assertFalse(self.utilisateur.est_transporteur)

    @override_settings(KYC_REQUIS_TRANSPORTEUR=True)
    def test_accepte_avec_cni_validee(self):
        Verification.objects.create(
            utilisateur=self.utilisateur,
            type_verification=Verification.TypeVerification.CNI,
            statut=Verification.StatutVerification.VALIDEE,
        )
        reponse = self.api.post("/api/vehicules/", VEHICULE)
        self.assertEqual(reponse.status_code, 201)
        self.utilisateur.refresh_from_db()
        self.assertTrue(self.utilisateur.est_transporteur)

    @override_settings(KYC_REQUIS_TRANSPORTEUR=False)
    def test_desactivable(self):
        reponse = self.api.post("/api/vehicules/", VEHICULE)
        self.assertEqual(reponse.status_code, 201)
