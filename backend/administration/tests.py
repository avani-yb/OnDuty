"""Site d'administration /gestion/ : accès, tableau de bord, utilisateurs, litiges."""

from unittest import mock

from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from comptes.models import Utilisateur
from course.models import Course
from litige.models import Litige
from onduty_backend import tests_outils as f
from paiement.models import Paiement, Versement
from paiement.services import campay


# En test, pas de collectstatic : stockage statique simple (sans manifeste).
STORAGES_TEST = {
    **settings.STORAGES,
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=STORAGES_TEST)
class BaseGestion(TestCase):
    def setUp(self):
        self.admin = f.utilisateur("690000000", "Admin")
        self.admin.type_compte = Utilisateur.TypeCompte.ADMIN
        self.admin.save()
        self.client.force_login(self.admin)


class AccesTests(BaseGestion):
    def test_reserve_au_compte_admin(self):
        self.client.logout()
        reponse = self.client.get("/gestion/")
        self.assertEqual(reponse.status_code, 302)
        self.assertIn("/gestion/connexion/", reponse["Location"])

        simple = f.utilisateur("690000001")
        self.client.force_login(simple)
        self.assertEqual(self.client.get("/gestion/").status_code, 302)

    def test_connexion_par_telephone(self):
        self.client.logout()
        reponse = self.client.post("/gestion/connexion/", {"telephone": "690 00 00 00", "mot_de_passe": "motdepasse-123"})
        self.assertRedirects(reponse, "/gestion/")

        f.utilisateur("690000002")
        self.client.logout()
        reponse = self.client.post("/gestion/connexion/", {"telephone": "690000002", "mot_de_passe": "motdepasse-123"})
        self.assertContains(reponse, "non administrateur")

    def test_redirection_externe_refusee(self):
        self.client.logout()
        reponse = self.client.post(
            "/gestion/connexion/?suivant=https://pirate.example/",
            {"telephone": "690000000", "mot_de_passe": "motdepasse-123"},
        )
        self.assertRedirects(reponse, "/gestion/")


class TableauDeBordTests(BaseGestion):
    def test_chiffres_et_courses_en_cours(self):
        client = f.utilisateur("690000001", "Client")
        transporteur = f.utilisateur("690000002", "Chauffeur", transporteur=True)
        course = f.course(f.demande(client), f.trajet(transporteur), statut="payee")
        reponse = self.client.get("/gestion/")
        self.assertEqual(reponse.status_code, 200)
        chiffres = reponse.context["chiffres"]
        self.assertEqual((chiffres["clients"], chiffres["transporteurs"], chiffres["demandes"]), (2, 1, 1))
        self.assertEqual(list(reponse.context["courses_en_cours"]), [course])
        self.assertEqual(self.client.get(f"/gestion/courses/{course.pk}/").status_code, 200)


class UtilisateursTests(BaseGestion):
    def setUp(self):
        super().setUp()
        self.u = f.utilisateur("690000001", "Paul")

    def test_liste_et_recherche(self):
        f.utilisateur("690000002", "Marie")
        reponse = self.client.get("/gestion/utilisateurs/?q=Paul")
        self.assertEqual([u.pk for u in reponse.context["page"].object_list], [self.u.pk])
        self.assertEqual(self.client.get(f"/gestion/utilisateurs/{self.u.pk}/").status_code, 200)

    def test_bloquer_empeche_l_api(self):
        api = APIClient()
        api.force_authenticate(self.u)
        self.client.post(f"/gestion/utilisateurs/{self.u.pk}/bloquer/")
        self.u.refresh_from_db()
        self.assertEqual((self.u.statut_compte, self.u.is_active), ("suspendu", False))
        # Connexion par l'application refusée
        reponse = APIClient().post("/api/token/", {"telephone": "690000001", "password": "motdepasse-123"})
        self.assertEqual(reponse.status_code, 401)

        self.client.post(f"/gestion/utilisateurs/{self.u.pk}/debloquer/")
        self.u.refresh_from_db()
        self.assertTrue(self.u.is_active)
        reponse = APIClient().post("/api/token/", {"telephone": "690000001", "password": "motdepasse-123"})
        self.assertEqual(reponse.status_code, 200)

    def test_suppression_sans_historique(self):
        self.client.post(f"/gestion/utilisateurs/{self.u.pk}/supprimer/", {"confirmation": "690000001"})
        self.assertFalse(Utilisateur.objects.filter(pk=self.u.pk).exists())

    def test_confirmation_obligatoire(self):
        self.client.post(f"/gestion/utilisateurs/{self.u.pk}/supprimer/", {"confirmation": "faux"})
        self.assertTrue(Utilisateur.objects.filter(pk=self.u.pk).exists())

    def test_anonymisation_si_historique(self):
        transporteur = f.utilisateur("690000002", transporteur=True)
        course = f.course(f.demande(self.u), f.trajet(transporteur), statut="livree")
        self.client.post(f"/gestion/utilisateurs/{self.u.pk}/supprimer/", {"confirmation": "690000001"})
        self.u.refresh_from_db()
        self.assertEqual((self.u.telephone, self.u.is_active), (f"supprime-{self.u.pk}", False))
        self.assertEqual(self.u.nom, "supprimé")
        self.assertTrue(Course.objects.filter(pk=course.pk).exists())  # historique conservé

    def test_course_en_cours_bloque_la_suppression(self):
        transporteur = f.utilisateur("690000002", transporteur=True)
        f.course(f.demande(self.u), f.trajet(transporteur), statut="payee")
        self.client.post(f"/gestion/utilisateurs/{self.u.pk}/supprimer/", {"confirmation": "690000001"})
        self.u.refresh_from_db()
        self.assertTrue(self.u.is_active)

    def test_admin_non_supprimable(self):
        self.client.post(f"/gestion/utilisateurs/{self.admin.pk}/supprimer/", {"confirmation": "690000000"})
        self.assertTrue(Utilisateur.objects.filter(pk=self.admin.pk).exists())


class LitigesTests(BaseGestion):
    def setUp(self):
        super().setUp()
        self.client_u = f.utilisateur("690000001", "Client")
        self.transporteur = f.utilisateur("690000002", "Chauffeur", transporteur=True)
        self.course = f.course(f.demande(self.client_u, montant=2000), f.trajet(self.transporteur), statut="en_litige")
        Paiement.objects.create(
            course=self.course, montant_course=2000, commission=100, frais=80, montant=2180,
            statut=Paiement.StatutPaiement.BLOQUE_ESCROW, reference_transaction="ref-litige",
        )
        self.litige = Litige.objects.create(course=self.course, declarant=self.client_u, motif="Colis abîmé")

    def test_liste_et_fiche(self):
        reponse = self.client.get("/gestion/litiges/")
        self.assertEqual(list(reponse.context["page"].object_list), [self.litige])
        reponse = self.client.get(f"/gestion/litiges/{self.litige.pk}/")
        self.assertContains(reponse, "Colis abîmé")
        self.assertContains(reponse, "2 180 FCFA")

    @mock.patch.object(campay, "envoyer", return_value={"reference": "v", "status": "SUCCESSFUL"})
    def test_valider_livraison(self, envoyer):
        self.client.post(f"/gestion/litiges/{self.litige.pk}/prendre_en_charge/")
        self.client.post(f"/gestion/litiges/{self.litige.pk}/valider_livraison/", {"commentaire": "Photos probantes"})
        self.litige.refresh_from_db()
        self.course.refresh_from_db()
        self.assertEqual((self.litige.statut, self.course.statut), ("resolu", "livree"))
        self.assertIn("Photos probantes", self.litige.decision_admin)
        versement = Versement.objects.get()
        self.assertEqual((versement.type_versement, versement.beneficiaire), ("transporteur", self.transporteur))

    @mock.patch.object(campay, "envoyer", return_value={"reference": "v", "status": "SUCCESSFUL"})
    def test_rembourser(self, envoyer):
        self.client.post(f"/gestion/litiges/{self.litige.pk}/rembourser/")
        self.course.refresh_from_db()
        self.assertEqual((self.course.statut, self.course.motif_annulation), ("annulee", "admin"))
        self.assertEqual(Versement.objects.get().beneficiaire, self.client_u)
        # Une seconde décision est refusée
        self.client.post(f"/gestion/litiges/{self.litige.pk}/valider_livraison/")
        self.assertEqual(Versement.objects.count(), 1)

    def test_actions_en_post_seulement(self):
        self.assertEqual(self.client.get(f"/gestion/litiges/{self.litige.pk}/rembourser/").status_code, 405)
