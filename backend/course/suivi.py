"""Suivi GPS des courses : envoi des positions par le transporteur, lecture
par les clients de la course.

- POST /api/positions/          : le téléphone du transporteur envoie sa
                                  position ; elle est rattachée à toutes ses
                                  courses en cours de transport.
- GET  /api/positions/          : le suivi doit-il tourner sur ce téléphone ?
- GET  /api/courses/{id}/suivi/ : dernière position et trajet parcouru
                                  (participants de la course uniquement).
"""

from datetime import timedelta

from django.utils import timezone
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import STATUTS_SUIVI, Course, PositionTransporteur

# Une position est ignorée si la précédente date de moins de 15 s (évite les
# envois en rafale et allège la base).
INTERVALLE_MINIMUM = timedelta(seconds=15)
# Nombre maximal de points renvoyés pour tracer le trajet parcouru.
POINTS_TRACE_MAX = 300


class PositionSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, min_value=-90, max_value=90)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, min_value=-180, max_value=180)
    precision = serializers.FloatField(required=False, allow_null=True, min_value=0)


def _courses_suivies(transporteur):
    return Course.objects.filter(transporteur=transporteur, statut__in=STATUTS_SUIVI)


class PositionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Le suivi doit-il tourner sur ce téléphone ?"""
        return Response({"suivi_actif": _courses_suivies(request.user).exists()})

    def post(self, request):
        """Position du transporteur, rattachée à ses courses en cours de transport."""
        serializer = PositionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        donnees = serializer.validated_data
        maintenant = timezone.now()

        enregistrees = []
        for course in _courses_suivies(request.user):
            derniere = course.positions.order_by("-date").first()
            if derniere is not None and maintenant - derniere.date < INTERVALLE_MINIMUM:
                continue
            PositionTransporteur.objects.create(
                course=course,
                latitude=donnees["latitude"],
                longitude=donnees["longitude"],
                precision_m=donnees.get("precision"),
                date=maintenant,
            )
            enregistrees.append(course.pk)

        actif = _courses_suivies(request.user).exists()
        return Response(
            {"suivi_actif": actif, "courses": enregistrees},
            status=status.HTTP_201_CREATED if enregistrees else status.HTTP_200_OK,
        )


def _point(position):
    return {
        "latitude": float(position.latitude),
        "longitude": float(position.longitude),
        "precision": position.precision_m,
        "date": position.date,
    }


def donnees_suivi(course):
    """Suivi visible uniquement du départ jusqu'à la livraison."""
    if course.statut not in STATUTS_SUIVI:
        return {"actif": False, "derniere_position": None, "trace": []}
    positions = list(course.positions.order_by("date").values_list("latitude", "longitude"))
    pas = max(1, len(positions) // POINTS_TRACE_MAX)
    trace = [[float(lat), float(lng)] for lat, lng in positions[::pas]]
    if positions and trace[-1] != [float(positions[-1][0]), float(positions[-1][1])]:
        trace.append([float(positions[-1][0]), float(positions[-1][1])])
    derniere = course.positions.order_by("-date").first()
    return {
        "actif": True,
        "derniere_position": _point(derniere) if derniere else None,
        "trace": trace,
    }
