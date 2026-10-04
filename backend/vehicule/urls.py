from rest_framework.routers import DefaultRouter

from .views import InformationsVehiculeViewSet

router = DefaultRouter()
router.register("vehicules", InformationsVehiculeViewSet, basename="vehicule")

urlpatterns = router.urls
