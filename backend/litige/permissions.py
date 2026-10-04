from rest_framework.permissions import BasePermission


class EstTransporteurCourseOuAdmin(BasePermission):
    """Le transporteur de la course peut créer/voir les incidents."""

    def has_object_permission(self, request, view, obj):
        if request.user.est_admin:
            return True
        return obj.course.transporteur_id == request.user.id


class EstParticipantCourseOuAdmin(BasePermission):
    """Client ou transporteur de la course peut créer/voir les litiges."""

    def has_object_permission(self, request, view, obj):
        if request.user.est_admin:
            return True
        return obj.course.client_id == request.user.id or obj.course.transporteur_id == request.user.id


class EstAdminSeul(BasePermission):
    """Seul l'admin peut traiter (résoudre, prendre en charge) un litige."""

    message = "Seul l'administrateur peut traiter un litige."

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.est_admin

    def has_object_permission(self, request, view, obj):
        return request.user.est_admin