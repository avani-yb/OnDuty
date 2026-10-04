from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import SmileCallbackView, VerificationViewSet

router = DefaultRouter()
router.register("verifications", VerificationViewSet, basename="verification")

urlpatterns = [
    path("kyc/smile-callback/", SmileCallbackView.as_view(), name="smile-callback"),
] + router.urls
