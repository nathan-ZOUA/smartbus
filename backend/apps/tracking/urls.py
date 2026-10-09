from rest_framework.routers import DefaultRouter

from .views import GPSPositionViewSet


router = DefaultRouter()
router.register("positions", GPSPositionViewSet, basename="position")
urlpatterns = router.urls
