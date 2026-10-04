from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import CampayWebhookView, PaiementViewSet

router = DefaultRouter()
router.register("paiements", PaiementViewSet, basename="paiement")

urlpatterns = [
    path("paiements/campay/webhook/", CampayWebhookView.as_view(), name="campay-webhook"),
] + router.urls
