from rest_framework.permissions import BasePermission


class EstProprietaireOuAdmin(BasePermission):
    """Autorise l'accès en lecture à son propre historique, ou à l'admin."""

    def has_object_permission(self, request, view, obj):
        if getattr(request.user, "est_admin", False):
            return True
        return obj.utilisateur_id == request.user.id


class SeulAdminPeutTraiter(BasePermission):
    """Seul l'administrateur peut modifier/traiter une vérification.

    L'utilisateur peut soumettre et consulter, mais pas valider/rejeter
    lui-même (l'arbitrage KYC est une action admin — UC-27).
    """

    message = "Seul l'administrateur peut traiter une vérification."

    def has_object_permission(self, request, view, obj):
        # L'utilisateur peut lire son objet, l'admin peut aussi le modifier
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return (
                getattr(request.user, "est_admin", False)
                or obj.utilisateur_id == request.user.id
            )
        # Demander le résultat au fournisseur : le propriétaire peut le faire.
        if getattr(view, "action", None) == "actualiser":
            return (
                getattr(request.user, "est_admin", False)
                or obj.utilisateur_id == request.user.id
            )
        # Les écritures (PUT/PATCH) sont réservées à l'admin
        return getattr(request.user, "est_admin", False)
