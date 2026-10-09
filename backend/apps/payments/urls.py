from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import PaymentAttemptViewSet, instructions


router = DefaultRouter()
router.register("attempts", PaymentAttemptViewSet, basename="payment-attempt")
urlpatterns = [path("instructions/", instructions, name="payment-instructions")]
urlpatterns += router.urls
