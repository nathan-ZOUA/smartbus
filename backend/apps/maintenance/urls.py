from rest_framework.routers import DefaultRouter

from .views import MaintenanceOrderViewSet


router = DefaultRouter()
router.register("orders", MaintenanceOrderViewSet, basename="maintenance-order")
urlpatterns = router.urls
