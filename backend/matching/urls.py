from django.urls import path

from .views import MatchingDemandeView, MatchingTrajetView

urlpatterns = [
    path(
        "matching/demande/<int:pk>/",
        MatchingDemandeView.as_view(),
        name="matching-demande",
    ),
    path(
        "matching/trajet/<int:pk>/",
        MatchingTrajetView.as_view(),
        name="matching-trajet",
    ),
]
