from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from course.models import Course

from .models import Incident, Litige
from .permissions import (
    EstAdminSeul,
    EstParticipantCourseOuAdmin,
    EstTransporteurCourseOuAdmin,
)
from .serializers import (
    IncidentCreerSerializer,
    IncidentSerializer,
    LitigeCreerSerializer,
    LitigeSerializer,
    LitigeTraiterSerializer,
)


class IncidentViewSet(viewsets.ModelViewSet):
    """Signalement d'incident par le transporteur (pendant une course).

    - POST /incidents/ : transporteur signale un incident (texte libre)
    - GET /incidents/ : liste des incidents (transporteur de la course + admin)
    """

    queryset = Incident.objects.select_related("course", "transporteur").all()
    serializer_class = IncidentSerializer
    permission_classes = [permissions.IsAuthenticated, EstTransporteurCourseOuAdmin]

    def get_queryset(self):
        utilisateur = self.request.user
        if utilisateur.est_admin:
            return self.queryset
        return self.queryset.filter(transporteur=utilisateur)

    def get_serializer_class(self):
        if self.action == "create":
            return IncidentCreerSerializer
        return IncidentSerializer

    def create(self, request, *args, **kwargs):
        """Transporteur signale un incident sur sa course.

        Body: { "course_id": <int>, "description": "..." }
        """
        course_id = request.data.get("course_id")
        if not course_id:
            return Response(
                {"detail": "Champ 'course_id' requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            return Response(
                {"detail": "Course introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not request.user.est_admin and course.transporteur_id != request.user.id:
            return Response(
                {"detail": "Vous n'êtes pas le transporteur de cette course."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Vérifier que la course est en cours (pas encore livrée/annulée)
        if course.statut in (
            Course.StatutCourse.LIVREE,
            Course.StatutCourse.ANNULEE,
        ):
            return Response(
                {"detail": "Impossible de signaler un incident sur une course terminée."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(course=course, transporteur=request.user)

        from notification.models import Notification
        from notification.services.notifier import notifier

        for personne in {course.client, course.demande.destinataire} - {None}:
            notifier(
                personne, Notification.TypeNotification.INCIDENT,
                "Incident signalé sur votre course",
                f"Le transporteur signale un incident sur la course #{course.pk} : "
                f"{serializer.instance.description[:200]}",
                course_id=course.pk,
            )

        output_serializer = IncidentSerializer(serializer.instance)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class LitigeViewSet(viewsets.ModelViewSet):
    """Déclaration et traitement des litiges (client ou transporteur).

    - POST /litiges/ : déclare un litige (motif libre)
    - GET /litiges/ : liste ses litiges (client/transporteur) ou tous (admin)
    - POST /litiges/{id}/traiter/ : admin prend en charge ou résout
    """

    queryset = Litige.objects.select_related("course", "declarant").all()
    serializer_class = LitigeSerializer
    permission_classes = [permissions.IsAuthenticated, EstParticipantCourseOuAdmin]

    def get_queryset(self):
        utilisateur = self.request.user
        if utilisateur.est_admin:
            return self.queryset
        return self.queryset.filter(declarant=utilisateur)

    def get_serializer_class(self):
        if self.action == "create":
            return LitigeCreerSerializer
        if self.action == "traiter":
            return LitigeTraiterSerializer
        return LitigeSerializer

    def get_permissions(self):
        if self.action in ("traiter",):
            return [permissions.IsAuthenticated(), EstAdminSeul()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        """Déclare un litige sur une course.

        Body: { "course_id": <int>, "motif": "..." }
        """
        course_id = request.data.get("course_id")
        if not course_id:
            return Response(
                {"detail": "Champ 'course_id' requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            course = Course.objects.select_related("client", "transporteur").get(pk=course_id)
        except Course.DoesNotExist:
            return Response(
                {"detail": "Course introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not request.user.est_admin and course.client_id != request.user.id and course.transporteur_id != request.user.id:
            return Response(
                {"detail": "Vous n'êtes pas participant à cette course."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Vérifier qu'il n'y a pas déjà un litige ouvert pour cette course par ce déclarant
        if Litige.objects.filter(course=course, declarant=request.user, statut=Litige.StatutLitige.OUVERT).exists():
            return Response(
                {"detail": "Vous avez déjà un litige ouvert pour cette course."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(course=course, declarant=request.user)

        # Mettre la course en statut "en_litige" si pas déjà
        if course.statut != Course.StatutCourse.EN_LITIGE:
            course.mettre_a_jour_statut(Course.StatutCourse.EN_LITIGE, request.user)

        from notification.models import Notification
        from notification.services.notifier import notifier

        autre = course.transporteur if request.user.pk == course.client_id else course.client
        notifier(
            autre, Notification.TypeNotification.LITIGE,
            "Litige ouvert sur une course",
            f"Un litige a été ouvert sur la course #{course.pk}. L'administrateur va "
            "examiner la situation ; les fonds restent bloqués d'ici là.",
            course_id=course.pk,
        )

        output_serializer = LitigeSerializer(serializer.instance)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def traiter(self, request, pk=None):
        """Admin traite le litige : prendre en charge ou résoudre.

        Body: { "action": "prendre_en_charge|resoudre", "decision": "..." }
        """
        litige = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data["action"]
        decision = serializer.validated_data.get("decision", "")

        if action == "prendre_en_charge":
            if not litige.prendre_en_charge(request.user):
                return Response(
                    {"detail": "Impossible : litige pas ouvert ou non admin."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(
                {"detail": "Litige pris en charge."},
                status=status.HTTP_200_OK,
            )

        if action == "resoudre":
            if not decision:
                return Response(
                    {"detail": "Décision requise pour résoudre."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not litige.resoudre(request.user, decision):
                return Response(
                    {"detail": "Impossible : non admin."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # Selon la décision, on peut mettre à jour la course
            # Pour l'instant, on laisse l'admin gérer via course directement
            return Response(
                {"detail": "Litige résolu.", "decision_admin": litige.decision_admin},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"detail": "Action inconnue."},
            status=status.HTTP_400_BAD_REQUEST,
        )