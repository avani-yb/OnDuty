from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Utilisateur
from .permissions import EstProprietaireOuAdmin
from .serializers import (
    InscriptionSerializer,
    ModificationMotDePasseSerializer,
    UtilisateurSerializer,
)


class InscriptionVue(generics.CreateAPIView):
    """Inscription d'un nouveau compte (Visiteur → Client).

    Endpoint public : aucune authentification requise pour créer un compte.
    """

    serializer_class = InscriptionSerializer
    permission_classes = [permissions.AllowAny]


class ProfilVue(generics.RetrieveUpdateAPIView):
    """Consultation et modification de son propre profil (BF-19).

    GET  /api/comptes/{id}/   → consulter le profil
    PUT/PATCH /api/comptes/{id}/ → modifier son profil
    """

    queryset = Utilisateur.objects.all()
    serializer_class = UtilisateurSerializer
    permission_classes = [permissions.IsAuthenticated, EstProprietaireOuAdmin]


class ModifierMotDePasseVue(APIView):
    """Modification de son propre mot de passe (BF-18).

    POST /api/comptes/changer-mot-de-passe/
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ModificationMotDePasseSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "Mot de passe modifié avec succès."},
            status=status.HTTP_200_OK,
        )
