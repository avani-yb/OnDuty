"""
Configuration des URL pour le projet onduty_backend.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path("admin/", admin.site.urls),

    # Racine de l'API (socle)
    path("api/", include("comptes.urls")),
    path("api/", include("vehicule.urls")),
    path("api/", include("verification.urls")),
    path("api/", include("trajet.urls")),
    path("api/", include("demande.urls")),
    path("api/", include("matching.urls")),
    path("api/", include("course.urls")),
    path("api/", include("paiement.urls")),
    path("api/", include("litige.urls")),
    path("api/", include("evaluation.urls")),
    path("api/", include("notification.urls")),
    path("api/", include("administration.urls")),

    # Authentification JWT
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]

# Service des médias en développement (ex. photos de profil uploadées)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
