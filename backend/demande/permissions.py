from rest_framework.permissions import BasePermission


class CreerDemandeProfileBase(BasePermission):
    """Tout client authentifié peut soumettre une demande ; l'admin aussi."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
        )


class EstProprietaireDemandeOuAdmin(BasePermission):
    """Le client ne voit que ses demandes ; l'admin voit tout."""

    def has_object_permission(self, request, view, obj):
        if request.user.est_admin:
            return True
        return obj.client_id == request.user.id


class SeulAdminTraiteContestation(BasePermission):
    """Seul l'admin traite (confirme/infirme) une contestation de rejet."""

    message = "Seul l'administrateur peut traiter une contestation."

    def has_object_permission(self, request, view, obj):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            # Lecture : l'admin ou le client concerné.
            return (
                request.user.est_admin
                or obj.client_id == request.user.id
            )
        # Écriture (traitement) : admin uniquement.
        return request.user.est_admin
