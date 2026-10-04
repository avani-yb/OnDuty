from django.db import models
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from demande.models import Demande
from notification.models import Notification
from notification.services.notifier import notifier

from .models import Course
from .permissions import (
    EstClientCourse,
    EstParticipantCourseOuAdmin,
    EstTransporteurCourse,
)
from .serializers import (
    CourseCreerSerializer,
    CourseProposerSerializer,
    CourseSerializer,
    ProposerMontantSerializer,
)

TYPE_COURSE = Notification.TypeNotification.COURSE_STATUT


def _trajet_txt(course):
    return f"{course.demande.origine} → {course.demande.destination}"


def _fcfa(valeur):
    return f"{int(valeur):,}".replace(",", " ") + " FCFA"


class CourseViewSet(viewsets.ModelViewSet):
    """Gestion du cycle de vie d'une course (réservation + suivi).

    Flux :
    - POST /courses/?demande_id= : le client choisit un trajet du matching
    - POST /courses/proposer/ : le transporteur choisit une demande du matching
    - POST /courses/{id}/accepter/ : le transporteur accepte la réservation telle quelle
    - POST /courses/{id}/proposer-montant/ : le transporteur propose une autre somme
    - POST /courses/{id}/valider-montant/ : le client accepte la proposition du transporteur
    - POST /courses/{id}/annuler/ : le client annule ou refuse (RM-02), remboursement du prix
    - POST /courses/{id}/depart/ | en_route/ | arrivee/ : suivi par le transporteur
    - POST /courses/{id}/confirmer_reception/ : expéditeur ou destinataire inscrit →
      versement au transporteur
    """

    queryset = Course.objects.select_related(
        "demande", "demande__destinataire", "trajet", "trajet__transporteur",
        "client", "transporteur",
    ).all()
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated, EstParticipantCourseOuAdmin]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        utilisateur = self.request.user
        if utilisateur.est_admin:
            return self.queryset
        return self.queryset.filter(
            models.Q(client=utilisateur)
            | models.Q(transporteur=utilisateur)
            | models.Q(demande__destinataire=utilisateur)
        ).distinct()

    def get_serializer_class(self):
        if self.action == "create":
            return CourseCreerSerializer
        if self.action == "proposer":
            return CourseProposerSerializer
        return CourseSerializer

    def get_permissions(self):
        if self.action in ("accepter", "depart", "en_route", "arrivee", "proposer_montant"):
            return [permissions.IsAuthenticated(), EstTransporteurCourse()]
        if self.action in ("annuler", "valider_montant"):
            return [permissions.IsAuthenticated(), EstClientCourse()]
        return super().get_permissions()

    def _reponse(self, course, code=status.HTTP_200_OK):
        course.refresh_from_db()
        return Response(CourseSerializer(course, context=self.get_serializer_context()).data, status=code)

    @staticmethod
    def _erreur(message):
        return Response({"detail": message}, status=status.HTTP_400_BAD_REQUEST)

    # --- Création --------------------------------------------------------

    def create(self, request, *args, **kwargs):
        """Le client choisit un trajet du matching. Body : { "trajet_id": <int> }, ?demande_id="""
        demande_id = request.query_params.get("demande_id")
        if not demande_id:
            return self._erreur("Paramètre 'demande_id' requis.")
        try:
            demande = Demande.objects.get(pk=demande_id)
        except Demande.DoesNotExist:
            return Response({"detail": "Demande introuvable."}, status=status.HTTP_404_NOT_FOUND)
        if not request.user.est_admin and demande.client_id != request.user.id:
            return Response(
                {"detail": "Vous n'êtes pas le client de cette demande."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.context["demande"] = demande
        serializer.is_valid(raise_exception=True)
        course = serializer.save()

        notifier(
            course.transporteur, Notification.TypeNotification.MATCHING,
            "Un client a choisi votre trajet",
            f"{course.client.prenom} {course.client.nom} souhaite expédier "
            f"{course.demande.poids_estime_kg} kg ({_trajet_txt(course)}) pour "
            f"{_fcfa(course.montant_convenu)}. Acceptez ou proposez un autre prix.",
            course_id=course.pk, trajet_id=course.trajet_id,
        )
        return self._reponse(course, status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def proposer(self, request):
        """Le transporteur choisit une demande compatible avec son trajet.

        Body : { "demande_id", "trajet_id", "montant" (facultatif) }. Le client
        doit accepter (puis payer) ou refuser.
        """
        if not request.user.est_transporteur:
            return Response(
                {"detail": "Seul un transporteur peut choisir une demande."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course = serializer.save()

        prix = _fcfa(course.montant_convenu)
        modifie = course.montant_convenu != course.demande.montant_propose
        notifier(
            course.client, Notification.TypeNotification.MATCHING,
            "Un transporteur a choisi votre demande",
            f"{course.transporteur.prenom} {course.transporteur.nom} propose de transporter "
            f"votre colis ({_trajet_txt(course)}) pour {prix}"
            + (" (prix modifié)" if modifie else "")
            + ". Acceptez pour passer au paiement, ou refusez.",
            course_id=course.pk,
        )
        return self._reponse(course, status.HTTP_201_CREATED)

    # --- Négociation -----------------------------------------------------

    @action(detail=True, methods=["post"])
    def accepter(self, request, pk=None):
        """Le transporteur accepte la réservation telle quelle (passe à en_attente_paiement)."""
        course = self.get_object()
        if not course.accepter_par_transporteur(request.user):
            return self._erreur(
                "Impossible d'accepter : vous n'êtes pas le transporteur "
                "ou la course n'est plus à l'état 'réservée'."
            )
        notifier(
            course.client, TYPE_COURSE, "Réservation acceptée",
            f"Le transporteur a accepté votre course ({_trajet_txt(course)}). "
            f"Vous pouvez payer {_fcfa(course.montant_convenu)} (hors commission et frais).",
            course_id=course.pk,
        )
        return self._reponse(course)

    @action(detail=True, methods=["post"], url_path="proposer-montant")
    def proposer_montant(self, request, pk=None):
        """Le transporteur propose une nouvelle somme avant d'accepter. Body : { "montant" }"""
        course = self.get_object()
        serializer = ProposerMontantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not course.proposer_nouveau_montant(request.user, serializer.validated_data["montant"]):
            return self._erreur(
                "Impossible de proposer un nouveau montant : vous n'êtes pas le "
                "transporteur ou la course n'est plus à l'état 'réservée'."
            )
        notifier(
            course.client, TYPE_COURSE, "Nouveau prix proposé",
            f"Le transporteur propose {_fcfa(course.montant_convenu)} pour votre course "
            f"({_trajet_txt(course)}). Acceptez ou refusez.",
            course_id=course.pk,
        )
        return self._reponse(course)

    @action(detail=True, methods=["post"], url_path="valider-montant")
    def valider_montant(self, request, pk=None):
        """Le client accepte la proposition du transporteur et passe au paiement."""
        course = self.get_object()
        if not course.valider_montant(request.user):
            return self._erreur(
                "Impossible de valider : vous n'êtes pas le client ou aucune "
                "proposition n'est en attente pour cette course."
            )
        notifier(
            course.transporteur, TYPE_COURSE, "Proposition acceptée",
            f"Le client a accepté {_fcfa(course.montant_convenu)} pour la course #{course.pk}. "
            "En attente de son paiement.",
            course_id=course.pk,
        )
        return self._reponse(course)

    @action(detail=True, methods=["post"])
    def annuler(self, request, pk=None):
        """Le client annule la course, ou refuse la proposition du transporteur.

        Si les fonds sont en escrow, le prix de la course est remboursé
        (commission et frais restent acquis à OnDuty).
        """
        from paiement.services import escrow

        course = self.get_object()
        statut_avant = course.statut
        if not course.annuler(request.user):
            return self._erreur(
                "Impossible d'annuler : vous n'êtes pas le client ou la course ne "
                "peut plus être annulée (déjà livrée, annulée ou en litige)."
            )
        paiement = getattr(course, "paiement", None)
        if paiement is not None:
            escrow.rembourser(paiement)
        if statut_avant == Course.StatutCourse.PROPOSITION_MONTANT:
            titre, corps = "Proposition refusée", (
                f"Le client a refusé votre proposition pour la course #{course.pk}."
            )
        else:
            titre, corps = "Course annulée", (
                f"Le client a annulé la course #{course.pk} ({_trajet_txt(course)})."
            )
        notifier(course.transporteur, TYPE_COURSE, titre, corps, course_id=course.pk)
        return self._reponse(course)

    # --- Suivi -----------------------------------------------------------

    def _avancer(self, request, nouveau_statut, titre, corps):
        course = self.get_object()
        if not course.mettre_a_jour_statut(nouveau_statut, request.user):
            return self._erreur("Transition invalide ou non autorisée.")
        for personne in {course.client, course.demande.destinataire} - {None}:
            notifier(personne, TYPE_COURSE, titre, corps.format(course=course), course_id=course.pk)
        return self._reponse(course)

    @action(detail=True, methods=["post"])
    def depart(self, request, pk=None):
        return self._avancer(
            request, Course.StatutCourse.DEPART, "Colis en route",
            "Le transporteur est parti avec le colis de la course #{course.pk}.",
        )

    @action(detail=True, methods=["post"])
    def en_route(self, request, pk=None):
        return self._avancer(
            request, Course.StatutCourse.EN_ROUTE, "Colis en route",
            "Le colis de la course #{course.pk} est en route.",
        )

    @action(detail=True, methods=["post"])
    def arrivee(self, request, pk=None):
        return self._avancer(
            request, Course.StatutCourse.ARRIVEE, "Colis arrivé",
            "Le colis de la course #{course.pk} est arrivé à destination. "
            "Confirmez sa réception pour libérer le paiement du transporteur.",
        )

    @action(detail=True, methods=["post"])
    def confirmer_reception(self, request, pk=None):
        """Expéditeur ou destinataire inscrit : réception confirmée → course
        terminée et prix versé au transporteur."""
        from paiement.services import escrow

        course = self.get_object()
        if not course.confirmer_reception(request.user):
            return self._erreur(
                "Seul l'expéditeur ou le destinataire peut confirmer la réception "
                "d'une course arrivée à destination."
            )
        paiement = getattr(course, "paiement", None)
        if paiement is not None:
            escrow.liberer(paiement)

        notifier(
            course.transporteur, TYPE_COURSE, "Course terminée",
            f"La réception de la course #{course.pk} est confirmée. Le prix de la course "
            "est envoyé sur votre Mobile Money.",
            course_id=course.pk,
        )
        if request.user.pk != course.client_id:
            notifier(
                course.client, TYPE_COURSE, "Course terminée",
                f"Le destinataire a confirmé la réception de votre colis (course #{course.pk}).",
                course_id=course.pk,
            )
        return self._reponse(course)
