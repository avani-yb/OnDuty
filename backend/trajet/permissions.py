from rest_framework.permissions import BasePermission


class EstTransporteurOuAdmin(BasePermission):
    """Autorise les actions sur les trajets.

    - Un transporteur gère ses propres trajets.
    - L'administrateur gère l'ensemble (traitement métier, suppressions).
    - Un simple client ne peut pas publier de trajet.
    """

    message = "Seul un transporteur peut publier un trajet."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # Admin accède à tout
        if request.user.est_admin:
            return True
        # Un transporteur peut créer/lister
        if request.user.est_transporteur:
            return True
        return False


class EstProprietaireTrajetOuAdmin(BasePermission):
    """Un transporteur ne manipule que ses propres trajets, l'admin tout."""

    def has_object_permission(self, request, view, obj):
        if request.user.est_admin:
            return True
        return obj.transporteur_id == request.user.id
