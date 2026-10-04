from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import EnvoiNotificationView, FCMTokenViewSet, NotificationViewSet

router = DefaultRouter()
router.register("fcm-tokens", FCMTokenViewSet, basename="fcm-token")
router.register("notifications", NotificationViewSet, basename="notification")

urlpatterns = router.urls + [
    path("notifications/envoyer/", EnvoiNotificationView.as_view(), name="notification-envoyer"),
]