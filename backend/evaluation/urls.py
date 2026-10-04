from rest_framework.routers import DefaultRouter

from .views import EvaluationViewSet

router = DefaultRouter()
router.register("evaluations", EvaluationViewSet, basename="evaluation")

urlpatterns = router.urls