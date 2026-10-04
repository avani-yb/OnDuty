from rest_framework.permissions import BasePermission


class EstProprietaireFCMToken(BasePermission):
    """L'utilisateur ne gère que ses propres tokens FCM."""

    def has_object_permission(self, request, view, obj):
        return obj.utilisateur_id == request.user.id


class EstProprietaireNotification(BasePermission):
    """L'utilisateur ne voit que ses propres notifications."""

    def has_object_permission(self, request, view, obj):
        if request.user.est_admin:
            return True
        return obj.utilisateur_id == request.user.id


class PeutCreerFCMToken(BasePermission):
    """Tout utilisateur authentifié peut enregistrer son token FCM."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class AdminOuSystemeNotification(BasePermission):
    """Seul l'admin ou le système (via clé API) peut créer des notifications."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.est_admin or hasattr(request, "is_system"))
        )