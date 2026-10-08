from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from . import localites


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def liste_localites(request):
    """Localités du Cameroun proposées pour l'origine et la destination."""
    return Response(localites.liste())
