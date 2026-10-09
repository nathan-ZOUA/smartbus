from django.urls import path

from .views import DashboardView, HealthView, api_root


urlpatterns = [
    path("", api_root, name="smartbus-api-root"),
    path("health/", HealthView.as_view(), name="health"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
]
