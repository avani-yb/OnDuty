from rest_framework.routers import DefaultRouter

from .views import TrajetViewSet

router = DefaultRouter()
router.register("trajets", TrajetViewSet, basename="trajet")

urlpatterns = router.urls
