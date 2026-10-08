from django.urls import path
from rest_framework.routers import DefaultRouter

from .suivi import PositionView
from .views import CourseViewSet

router = DefaultRouter()
router.register("courses", CourseViewSet, basename="course")

urlpatterns = [
    path("positions/", PositionView.as_view(), name="positions"),
] + router.urls
