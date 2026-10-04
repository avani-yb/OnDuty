from rest_framework.permissions import BasePermission


class EstParticipantCourseOuAdmin(BasePermission):
    """Accès en lecture : client, transporteur ou admin de la course."""

    def has_object_permission(self, request, view, obj):
        if request.user.est_admin:
            return True
        return request.user.id in (
            obj.client_id,
            obj.transporteur_id,
            obj.demande.destinataire_id,
        )


class EstClientCourse(BasePermission):
    """Actions réservées au client de la course (annulation, confirmation réception)."""

    message = "Cette action est réservée au client de la course."

    def has_object_permission(self, request, view, obj):
        return obj.client_id == request.user.id


class EstTransporteurCourse(BasePermission):
    """Actions réservées au transporteur de la course (acceptation, maj statut transport)."""

    message = "Cette action est réservée au transporteur de la course."

    def has_object_permission(self, request, view, obj):
        return obj.transporteur_id == request.user.id
