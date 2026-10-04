from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views
from .views import ProfilVue

# Routeur DRF (préparé pour futurs ViewSets dans cette app)
router = DefaultRouter()

urlpatterns = [
    path("", include(router.urls)),
    path("inscription/", views.InscriptionVue.as_view(), name="inscription"),
    path("profil/<int:pk>/", ProfilVue.as_view(), name="profil-detail"),
    path(
        "changer-mot-de-passe/",
        views.ModifierMotDePasseVue.as_view(),
        name="changer-mot-de-passe",
    ),
]
