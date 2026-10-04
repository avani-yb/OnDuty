from rest_framework.permissions import BasePermission


class EstClientPaiementOuAdmin(BasePermission):
    """Accès à un paiement : client ou transporteur de la course, ou admin.

    Les actions sensibles (libérer, rembourser) sont en plus réservées à
    l'administrateur dans la vue ; la confirmation d'un paiement ne vient
    que de CamPay (webhook signé + revérification par l'API).
    """

    def has_object_permission(self, request, view, obj):
        if request.user.est_admin:
            return True
        if view.action == "verifier":
            return obj.course.client_id == request.user.id
        return (
            obj.course.client_id == request.user.id
            or obj.course.transporteur_id == request.user.id
        )
