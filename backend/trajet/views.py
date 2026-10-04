from rest_framework import permissions, status, viewsets
from rest_framework.response import Response

from . import services
from .models import Trajet
from .permissions import (
    EstProprietaireTrajetOuAdmin,
    EstTransporteurOuAdmin,
)
from .serializers import TrajetSerializer

# Ordre d'affichage : actifs (date à venir), puis en cours (aujourd'hui),
# puis passés ; les autres statuts (complet, expiré) en dernier.
ORDRE_ETATS = {Trajet.ETAT_ACTIF: 0, Trajet.ETAT_EN_COURS: 1, Trajet.ETAT_PASSE: 2}


class TrajetViewSet(viewsets.ModelViewSet):
    """Gestion des trajets publiés par les transporteurs (BF-25, BF-26).

    - Un transporteur publie et gère ses propres trajets.
    - Un simple client ne peut pas publier de trajet.
    - L'administrateur peut voir et traiter l'ensemble.
    - Modification et suppression : trajets « actifs » uniquement.
    """

    serializer_class = TrajetSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        EstTransporteurOuAdmin,
        EstProprietaireTrajetOuAdmin,
    ]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        # Les trajets "supprimés" (suppression logique) sont cachés de l'API ;
        # ils restent accessibles en base pour l'audit (admin Django).
        utilisateur = self.request.user
        qs = Trajet.objects.exclude(statut=Trajet.StatutTrajet.SUPPRIME).select_related(
            "transporteur", "transporteur__informations_vehicule"
        ).prefetch_related("courses", "courses__demande", "courses__client")
        if utilisateur.est_admin:
            return qs
        return qs.filter(transporteur=utilisateur)

    def list(self, request, *args, **kwargs):
        trajets = list(self.get_queryset())
        # Actifs et en cours : du plus proche au plus lointain ; passés : du
        # plus récent au plus ancien.
        trajets.sort(key=lambda t: (
            ORDRE_ETATS.get(t.etat, 3),
            -t.date_depart.timestamp() if t.etat == Trajet.ETAT_PASSE else t.date_depart.timestamp(),
        ))
        return Response(self.get_serializer(trajets, many=True).data)

    def perform_create(self, serializer):
        serializer.save(transporteur=self.request.user)

    def destroy(self, request, *args, **kwargs):
        trajet = self.get_object()
        if not trajet.est_modifiable:
            return Response(
                {"detail": "Seul un trajet actif (dont la date n'est pas encore arrivée) peut être supprimé."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        nb_annulees = services.supprimer(trajet)
        return Response({"courses_annulees": nb_annulees}, status=status.HTTP_200_OK)
