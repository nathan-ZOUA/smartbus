from rest_framework.routers import DefaultRouter

from .views import BusViewSet, DriverViewSet


router = DefaultRouter()
router.register("buses", BusViewSet, basename="bus")
router.register("drivers", DriverViewSet, basename="driver")
urlpatterns = router.urls
