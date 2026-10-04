from django.urls import path

from .views import dashboard_stats

urlpatterns = [
    path("dashboard/stats/", dashboard_stats, name="admin-dashboard-stats"),
]