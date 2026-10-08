"""Routes du site d'administration (/gestion/)."""

from django.urls import path

from . import gestion

app_name = "gestion"

urlpatterns = [
    path("", gestion.tableau_de_bord, name="tableau_de_bord"),
    path("connexion/", gestion.connexion, name="connexion"),
    path("deconnexion/", gestion.deconnexion, name="deconnexion"),
    path("utilisateurs/", gestion.utilisateurs, name="utilisateurs"),
    path("utilisateurs/<int:pk>/", gestion.utilisateur_detail, name="utilisateur"),
    path("utilisateurs/<int:pk>/<str:action>/", gestion.utilisateur_action, name="utilisateur_action"),
    path("litiges/", gestion.litiges, name="litiges"),
    path("litiges/<int:pk>/", gestion.litige_detail, name="litige"),
    path("litiges/<int:pk>/<str:action>/", gestion.litige_action, name="litige_action"),
    path("courses/<int:pk>/", gestion.course_detail, name="course"),
]
