from rest_framework.routers import DefaultRouter

from .views import ContestationRejetViewSet, DemandeViewSet

router = DefaultRouter()
router.register("demandes", DemandeViewSet, basename="demande")
router.register("contestations", ContestationRejetViewSet, basename="contestation")

urlpatterns = router.urls
