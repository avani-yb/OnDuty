import logging

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from onduty_backend.services_externes import ServiceExterneErreur

from .models import ContestationRejet, ControleIA, Demande
from .permissions import (
    CreerDemandeProfileBase,
    EstProprietaireDemandeOuAdmin,
    SeulAdminTraiteContestation,
)
from .serializers import (
    ContestationRejetSerializer,
    ControleIASerializer,
    DemandeSerializer,
    TraiterContestationSerializer,
)
from .services.ia import obtenir_controleur

logger = logging.getLogger(__name__)


def executer_controle(demande: Demande) -> ControleIA:
    """Exécute le pipeline IA et enregistre une nouvelle tentative de contrôle.

    Met à jour le statut de la demande (publiée si validée, rejetée sinon)
    et retourne le ControleIA créé.
    """
    controleur = obtenir_controleur()
    resultat = controleur.executer(demande)

    numero = (
        ControleIA.objects.filter(demande=demande).count() + 1
    )
    controle = ControleIA.objects.create(
        demande=demande,
        numero_tentative=numero,
        resultat_detection_objets=resultat["detection_objets"],
        resultat_coherence=resultat["coherence"],
        verdict=resultat["verdict"],
        motif_rejet=resultat["motif_rejet"],
        duree_traitement_secondes=resultat["duree_traitement_secondes"],
    )

    if controle.verdict == ControleIA.Verdict.VALIDE:
        demande.statut = Demande.StatutDemande.PUBLIEE
    else:
        demande.statut = Demande.StatutDemande.REJETEE
    demande.save(update_fields=["statut"])

    return controle


class DemandeViewSet(viewsets.ModelViewSet):
    """Gestion des demandes d'expédition et de leur contrôle IA.

    Flux :
    - `POST /demandes/` : créer une demande → déclenche le contrôle IA
      (statut) et renvoie demande + contrôle.
    - `POST /demandes/{id}/relancer/` : nouvelle tentative après rejet (BF-07).
    - `POST /demandes/{id}/contester/` : remettre en cause le rejet (BF-08).
    - `GET /demandes/{id}/controles/` : historique des tentatives (BF-09).
    - `PATCH /demandes/{id}/` : modification (règles ci-dessous).
    - `DELETE /demandes/{id}/` : suppression, si aucune course n'est en cours.

    Modification (décision du 04/10/2026) :
    - sans course en cours : tout est modifiable ; une nouvelle description
      ou une nouvelle vidéo relance le contrôle IA ;
    - avec une course en cours : seuls la date, le prix proposé (tant que le
      transporteur n'a pas répondu) et le numéro du destinataire ; le
      transporteur est notifié.
    """

    CHAMPS_APRES_RESERVATION = {"date_souhaitee", "montant_propose", "telephone_destinataire"}

    serializer_class = DemandeSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        CreerDemandeProfileBase,
        EstProprietaireDemandeOuAdmin,
    ]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        utilisateur = self.request.user
        qs = Demande.objects.exclude(statut=Demande.StatutDemande.SUPPRIMEE).select_related("destinataire")
        if utilisateur.est_admin:
            return qs
        return qs.filter(client=utilisateur)

    @staticmethod
    def _course_active(demande):
        return demande.courses.exclude(statut="annulee").select_related("transporteur").first()

    def partial_update(self, request, *args, **kwargs):
        from course.models import Course
        from notification.models import Notification
        from notification.services.notifier import notifier

        demande = self.get_object()
        champs = set(request.data.keys())
        course = self._course_active(demande)

        if course is not None:
            if course.statut in (Course.StatutCourse.LIVREE, Course.StatutCourse.EN_LITIGE):
                return Response(
                    {"detail": "Cette demande ne peut plus être modifiée."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            interdits = champs - self.CHAMPS_APRES_RESERVATION
            if interdits:
                return Response(
                    {
                        "detail": (
                            "Une course est en cours : seuls la date, le prix proposé et "
                            "le numéro du destinataire peuvent être modifiés."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if "montant_propose" in champs and course.statut != Course.StatutCourse.RESERVEE:
                return Response(
                    {"detail": "Le prix est déjà convenu avec le transporteur."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        ancienne_description = demande.description
        serializer = self.get_serializer(demande, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        demande = serializer.save()

        if course is not None:
            if "montant_propose" in champs:
                course.montant_convenu = demande.montant_propose
                course.save(update_fields=["montant_convenu"])
            notifier(
                course.transporteur, Notification.TypeNotification.COURSE_STATUT,
                "Demande modifiée",
                f"Le client a modifié sa demande pour la course #{course.pk} "
                f"({demande.origine} → {demande.destination}).",
                course_id=course.pk,
            )
            return Response(DemandeSerializer(demande).data)

        # Nouvelle description ou nouvelle vidéo : nouveau contrôle IA.
        if "video" in champs or demande.description != ancienne_description:
            return self._controler(demande, status.HTTP_200_OK)
        return Response(DemandeSerializer(demande).data)

    def destroy(self, request, *args, **kwargs):
        demande = self.get_object()
        if self._course_active(demande) is not None:
            return Response(
                {"detail": "Une course est en cours pour cette demande : annulez-la d'abord."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        demande.statut = Demande.StatutDemande.SUPPRIMEE
        demande.save(update_fields=["statut"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _controler(self, demande, statut_succes):
        """Lance le contrôle IA ; en cas de panne d'un service tiers, la
        demande reste « en cours de contrôle » et le client reçoit une
        erreur 503 explicite (BNF-03). Il pourra relancer le contrôle."""
        try:
            controle = executer_controle(demande)
        except ServiceExterneErreur as exc:
            logger.error("Contrôle IA de la demande %s impossible : %s", demande.pk, exc)
            demande.statut = Demande.StatutDemande.EN_COURS_CONTROLE
            demande.save(update_fields=["statut"])
            return Response(
                {
                    "detail": exc.message_utilisateur,
                    "demande": DemandeSerializer(demande).data,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(
            {
                "demande": DemandeSerializer(demande).data,
                "controle_ia": ControleIASerializer(controle).data,
            },
            status=statut_succes,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        demande = serializer.save(client=request.user)
        return self._controler(demande, status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def relancer(self, request, pk=None):
        """Relance le contrôle IA (BF-07).

        Possible sur une demande rejetée, ou restée « en cours de contrôle »
        après une panne d'un service tiers. Le client peut fournir une
        nouvelle description, un nouveau poids et/ou une nouvelle vidéo
        (fichier `video`, multipart).
        """
        demande = self.get_object()
        if demande.statut not in (
            Demande.StatutDemande.REJETEE,
            Demande.StatutDemande.EN_COURS_CONTROLE,
        ):
            return Response(
                {
                    "detail": (
                        "La relance n'est possible que sur une demande rejetée "
                        "ou en attente de contrôle."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        champs = {
            k: v for k, v in request.data.items()
            if k in ("description", "poids_estime_kg", "video")
        }
        serializer = self.get_serializer(demande, data=champs, partial=True)
        serializer.is_valid(raise_exception=True)
        demande = serializer.save()
        # Réponse identique à la création : {"demande", "controle_ia"}.
        return self._controler(demande, status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def contester(self, request, pk=None):
        """Crée une contestation de rejet pour revue manuelle (BF-08)."""
        demande = self.get_object()
        if demande.statut != Demande.StatutDemande.REJETEE:
            return Response(
                {
                    "detail": (
                        "Seule une demande rejetée peut faire l'objet d'une "
                        "contestation."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        dernier_controle = demande.controles.order_by("-numero_tentative").first()
        if not dernier_controle:
            return Response(
                {"detail": "Aucun contrôle IA trouvé pour cette demande."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if ContestationRejet.objects.filter(
            controle_ia=dernier_controle
        ).exists():
            return Response(
                {
                    "detail": (
                        "Une contestation existe déjà pour ce contrôle."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        contestation = ContestationRejet.objects.create(
            controle_ia=dernier_controle,
            client=request.user,
        )
        return Response(
            ContestationRejetSerializer(contestation).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"])
    def controles(self, request, pk=None):
        """Historique des tentatives de contrôle IA d'une demande (BF-09)."""
        demande = self.get_object()
        controles = demande.controles.order_by("numero_tentative")
        return Response(
            ControleIASerializer(controles, many=True).data,
            status=status.HTTP_200_OK,
        )


class ContestationRejetViewSet(viewsets.ModelViewSet):
    """Contestations de rejet et leur traitement administratif."""

    permission_classes = [
        permissions.IsAuthenticated,
        SeulAdminTraiteContestation,
    ]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        utilisateur = self.request.user
        if utilisateur.est_admin:
            return ContestationRejet.objects.all()
        return ContestationRejet.objects.filter(client=utilisateur)

    def get_serializer_class(self):
        if self.action == "partial_update":
            return TraiterContestationSerializer
        return ContestationRejetSerializer
