from django.conf import settings
from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from verification.models import Verification

from .models import InformationsVehicule
from .permissions import EstProprietaireVehiculeOuAdmin
from .serializers import InformationsVehiculeSerializer


class InformationsVehiculeViewSet(viewsets.ModelViewSet):
    """CRUD des informations véhicule d'un transporteur.

    - Chaque utilisateur ne gère que SON véhicule (le champ `utilisateur`
      est forcé côté serveur lors de la création).
    - L'administrateur peut tout consulter/modifier.
    """

    serializer_class = InformationsVehiculeSerializer
    permission_classes = [permissions.IsAuthenticated, EstProprietaireVehiculeOuAdmin]

    def get_queryset(self):
        utilisateur = self.request.user
        if utilisateur.est_admin:
            return InformationsVehicule.objects.all()
        # Un utilisateur classique ne voit que son propre véhicule
        return InformationsVehicule.objects.filter(utilisateur=utilisateur)

    def perform_create(self, serializer):
        # Le rôle Transporteur exige une CNI vérifiée (docs/03, section 5).
        # Désactivable via KYC_REQUIS_TRANSPORTEUR=False dans le .env.
        utilisateur = self.request.user
        if settings.KYC_REQUIS_TRANSPORTEUR and not utilisateur.est_admin:
            cni_validee = Verification.objects.filter(
                utilisateur=utilisateur,
                type_verification=Verification.TypeVerification.CNI,
                statut=Verification.StatutVerification.VALIDEE,
            ).exists()
            if not cni_validee:
                raise PermissionDenied(
                    "Votre CNI doit être vérifiée avant de devenir "
                    "transporteur. Rendez-vous dans Profil > Vérifier ma CNI."
                )
        # Le véhicule est rattaché à l'utilisateur connecté. Déclarer un
        # véhicule correspond à l'action "devenir transporteur" (BF-22,
        # cf. docs/03-acteurs-parties-prenantes.md) : le rôle Transporteur
        # est donc activé automatiquement sur le compte à cette occasion.
        serializer.save(utilisateur=self.request.user)
        if not self.request.user.est_transporteur:
            self.request.user.activer_role_transporteur()
