from django.db import models
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from course.models import Course

from .models import Evaluation
from .permissions import (
    EstClientCourse,
    EstClientEvaluationOuAdmin,
    PeutCreerEvaluation,
)
from .serializers import EvaluationCreerSerializer, EvaluationSerializer


class EvaluationViewSet(viewsets.ModelViewSet):
    """Gestion des évaluations transporteur (après course livrée).

    - POST /evaluations/ : client évalue le transporteur (course livrée)
    - GET /evaluations/ : liste ses évaluations données (client) ou reçues (transporteur)
    - GET /evaluations/{id}/ : détail
    - GET /evaluations/fiabilite/ : détail score fiabilité transporteur (admin ou transporteur)
    """

    queryset = Evaluation.objects.select_related(
        "course", "client", "transporteur"
    ).all()
    serializer_class = EvaluationSerializer
    permission_classes = [permissions.IsAuthenticated, EstClientEvaluationOuAdmin]

    def get_queryset(self):
        utilisateur = self.request.user
        if utilisateur.est_admin:
            return self.queryset
        # Client voit ses évaluations données, transporteur voit celles reçues
        return self.queryset.filter(
            models.Q(client=utilisateur) | models.Q(transporteur=utilisateur)
        )

    def get_serializer_class(self):
        if self.action == "create":
            return EvaluationCreerSerializer
        return EvaluationSerializer

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated(), EstClientCourse()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        """Client évalue le transporteur après course livrée.

        Body: { "course_id": <int>, "note": 1-5, "commentaire": "..." }
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

        if not request.user.est_admin and course.client_id != request.user.id:
            return Response(
                {"detail": "Vous n'êtes pas le client de cette course."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # La course doit être livrée pour être évaluable
        if course.statut != Course.StatutCourse.LIVREE:
            return Response(
                {"detail": "Seule une course livrée peut être évaluée."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Vérifier qu'il n'y a pas déjà une évaluation
        if hasattr(course, "evaluation"):
            return Response(
                {"detail": "Cette course a déjà été évaluée."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(course=course, client=request.user, transporteur=course.transporteur)

        output_serializer = EvaluationSerializer(serializer.instance)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="fiabilite")
    def fiabilite(self, request):
        """Retourne le détail du score de fiabilité du transporteur connecté.

        Accessible au transporteur lui-même et à l'admin.
        """
        if not request.user.est_transporteur and not request.user.est_admin:
            return Response(
                {"detail": "Réservé aux transporteurs et administrateurs."},
                status=status.HTTP_403_FORBIDDEN,
            )

        from .services.fiabilite import get_details_fiabilite

        details = get_details_fiabilite(request.user)
        return Response(details, status=status.HTTP_200_OK)