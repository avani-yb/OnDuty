from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from demande.models import Demande
from trajet.models import Trajet
from trajet.services import type_vehicule

from .serializers import (
    ResultatClientSerializer,
    ResultatTransporteurSerializer,
)
from .services.matching import (
    demande_a_une_course_active,
    matching_pour_client,
    matching_pour_transporteur,
)


class MatchingDemandeView(APIView):
    """Liste des transporteurs/trajets proposés pour une demande publiée.

    BF-10 (client) — la demande doit être publiée (RM-01 : aucune demande
    non valide n'entre en matching). Réservé au client propriétaire ou admin.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            demande = Demande.objects.get(pk=pk)
        except Demande.DoesNotExist:
            return Response(
                {"detail": "Demande introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not request.user.est_admin and demande.client_id != request.user.id:
            return Response(
                {"detail": "Vous n'avez pas accès à cette demande."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if demande.statut != Demande.StatutDemande.PUBLIEE:
            return Response(
                {
                    "detail": (
                        "Le matching n'est disponible que pour une demande "
                        "publiée (validée par le contrôle IA)."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if demande_a_une_course_active(demande):
            return Response(
                {"detail": "Cette demande a déjà une course en cours."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        resultats = matching_pour_client(demande)
        data = [
            {
                "score": r["score"],
                "trajet": {
                    "id": r["trajet"].id,
                    "origine": r["trajet"].origine,
                    "destination": r["trajet"].destination,
                    "date_depart": r["trajet"].date_depart,
                    "capacite_disponible_kg": r["trajet"].capacite_restante_kg,
                    "transporteur": {
                        "id": r["trajet"].transporteur.id,
                        "nom": r["trajet"].transporteur.nom,
                        "prenom": r["trajet"].transporteur.prenom,
                        "telephone": r["trajet"].transporteur.telephone,
                        "score_fiabilite": r["trajet"].transporteur.score_fiabilite,
                    },
                    "type_vehicule": type_vehicule(r["trajet"].transporteur),
                },
            }
            for r in resultats
        ]
        return Response(
            ResultatClientSerializer(data, many=True).data,
            status=status.HTTP_200_OK,
        )


class MatchingTrajetView(APIView):
    """Demandes issues du matching pour un trajet.

    BF-27 (transporteur) — le transporteur consulte les demandes compatibles
    avec son trajet. Réservé au transporteur propriétaire ou admin.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            trajet = Trajet.objects.get(pk=pk)
        except Trajet.DoesNotExist:
            return Response(
                {"detail": "Trajet introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not request.user.est_admin and trajet.transporteur_id != request.user.id:
            return Response(
                {"detail": "Vous n'avez pas accès à ce trajet."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not trajet.est_modifiable:
            return Response(
                {"detail": "Le matching n'est disponible que pour un trajet actif."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if trajet.capacite_restante_kg <= 0:
            return Response(
                {"detail": "Ce trajet est complet : toute la capacité est déjà réservée."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        resultats = matching_pour_transporteur(trajet)
        return Response(
            ResultatTransporteurSerializer(resultats, many=True).data,
            status=status.HTTP_200_OK,
        )
