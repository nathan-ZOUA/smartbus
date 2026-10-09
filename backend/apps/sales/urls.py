from rest_framework.routers import DefaultRouter

from .views import SaleOrderViewSet


router = DefaultRouter()
router.register("orders", SaleOrderViewSet, basename="sale-order")
urlpatterns = router.urls
