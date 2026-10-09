from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.core.urls")),
    path("api/auth/", include("apps.authentication.urls")),
    path("api/fleet/", include("apps.fleet.urls")),
    path("api/tracking/", include("apps.tracking.urls")),
    path("api/bookings/", include("apps.bookings.urls")),
    path("api/sales/", include("apps.sales.urls")),
    path("api/payments/", include("apps.payments.urls")),
    path("api/maintenance/", include("apps.maintenance.urls")),
    path("api/contracts/", include("apps.contracts.urls")),
]
