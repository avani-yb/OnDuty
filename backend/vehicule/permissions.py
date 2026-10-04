from rest_framework.permissions import BasePermission


class EstProprietaireVehiculeOuAdmin(BasePermission):
    """Autorise uniquement le propriétaire du véhicule ou l'administrateur."""

    def has_object_permission(self, request, view, obj):
        if getattr(request.user, "est_admin", False):
            return True
        # Un véhicule appartient à son utilisateur
        return obj.utilisateur_id == request.user.id
