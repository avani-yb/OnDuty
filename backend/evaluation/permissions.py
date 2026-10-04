from rest_framework.permissions import BasePermission


class EstClientEvaluationOuAdmin(BasePermission):
    """Le client qui a donné l'évaluation ou le transporteur évalué ou l'admin peuvent voir."""

    def has_object_permission(self, request, view, obj):
        if request.user.est_admin:
            return True
        return obj.client_id == request.user.id or obj.transporteur_id == request.user.id


class EstClientCourse(BasePermission):
    """Le client de la course peut évaluer le transporteur."""

    message = "Seul le client de la course peut laisser une évaluation."

    def has_object_permission(self, request, view, obj):
        return obj.course.client_id == request.user.id


class PeutCreerEvaluation(BasePermission):
    """Le client peut créer une évaluation pour sa course livrée."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)