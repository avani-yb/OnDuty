from rest_framework.routers import DefaultRouter

from .views import IncidentViewSet, LitigeViewSet

router = DefaultRouter()
router.register("incidents", IncidentViewSet, basename="incident")
router.register("litiges", LitigeViewSet, basename="litige")

urlpatterns = router.urls