from rest_framework.permissions import BasePermission


class EstProprietaireOuAdmin(BasePermission):
    """Autorise uniquement le propriétaire de l'objet ou l'administrateur.

    Le mobile n'étant pas découpé en rôles exclusifs, chaque utilisateur ne
    doit pouvoir accéder qu'à SON profil (et pas à celui des autres),
    sauf s'il s'agit de l'administrateur unique.
    """

    def has_object_permission(self, request, view, obj):
        # L'administrateur peut tout consulter
        if getattr(request.user, "est_admin", False):
            return True
        # Sinon, uniquement son propre compte
        return obj == request.user
