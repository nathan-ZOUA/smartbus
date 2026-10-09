from rest_framework import filters, viewsets
from rest_framework.permissions import AllowAny

from .models import Bus, Driver
from .permissions import DriverManagementPermission, FleetWritePermission
from .serializers import BusSerializer, DriverSerializer


class BusViewSet(viewsets.ModelViewSet):
    queryset = Bus.objects.select_related("driver").all()
    serializer_class = BusSerializer
    permission_classes = [FleetWritePermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["registration", "make", "model"]
    ordering_fields = ["registration", "year", "daily_rate", "seats"]

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [AllowAny()]
        return super().get_permissions()


class DriverViewSet(viewsets.ModelViewSet):
    queryset = Driver.objects.all()
    serializer_class = DriverSerializer
    permission_classes = [DriverManagementPermission]
