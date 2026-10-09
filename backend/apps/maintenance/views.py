from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.serializers import DecimalField

from apps.core.permissions import user_has_role
from apps.core.workflows import bus_has_active_bookings
from apps.fleet.models import Bus

from .models import MaintenanceOrder
from .serializers import MaintenanceOrderSerializer


MAINTENANCE_MANAGER_ROLES = {
    "SUPER_ADMIN",
    "ADMIN",
    "FLEET_MANAGER",
    "MAINTENANCE_MANAGER",
}


class MaintenanceOrderViewSet(viewsets.ModelViewSet):
    serializer_class = MaintenanceOrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_permissions(self):
        if not user_has_role(self.request.user, MAINTENANCE_MANAGER_ROLES):
            return [permissions.IsAdminUser()]
        return super().get_permissions()

    def get_queryset(self):
        return MaintenanceOrder.objects.select_related("bus", "created_by")

    @transaction.atomic
    def perform_create(self, serializer):
        bus = Bus.objects.select_for_update().get(
            pk=serializer.validated_data["bus"].pk
        )
        if bus.status not in {Bus.Status.AVAILABLE, Bus.Status.OFFLINE}:
            raise ValidationError(
                {"bus": "Le bus doit être disponible ou hors ligne pour maintenance."}
            )
        serializer.save(created_by=self.request.user, currency="XAF")

    def _lock_order(self, order):
        return MaintenanceOrder.objects.select_for_update().select_related(
            "bus"
        ).get(pk=order.pk)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def approve(self, request, pk=None):
        order = self._lock_order(self.get_object())
        if order.status != MaintenanceOrder.Status.REQUESTED:
            raise ValidationError(
                {"status": "Seuls les ordres demandés peuvent être approuvés."}
            )
        order.status = MaintenanceOrder.Status.APPROVED
        order.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def start(self, request, pk=None):
        order = self._lock_order(self.get_object())
        bus = Bus.objects.select_for_update().get(pk=order.bus_id)
        if order.status != MaintenanceOrder.Status.APPROVED:
            raise ValidationError(
                {"status": "Approuve l'ordre avant de démarrer les travaux."}
            )
        if bus.status not in {Bus.Status.AVAILABLE, Bus.Status.OFFLINE}:
            raise ValidationError(
                {"bus": "Le bus a été réservé ou son état ne permet pas la maintenance."}
            )
        if bus_has_active_bookings(bus):
            raise ValidationError(
                {"bus": "Une réservation active empêche de démarrer la maintenance."}
            )
        order.previous_bus_status = bus.status
        order.status = MaintenanceOrder.Status.IN_PROGRESS
        order.started_at = timezone.now()
        bus.status = Bus.Status.MAINTENANCE
        bus.save(update_fields=["status", "updated_at"])
        order.save(
            update_fields=[
                "previous_bus_status",
                "status",
                "started_at",
                "updated_at",
            ]
        )
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def complete(self, request, pk=None):
        order = self._lock_order(self.get_object())
        if order.status != MaintenanceOrder.Status.IN_PROGRESS:
            raise ValidationError(
                {"status": "Seul un ordre en cours peut être terminé."}
            )
        actual_cost = request.data.get("actual_cost")
        if actual_cost is None:
            raise ValidationError(
                {"actual_cost": "Indique le coût réel en XAF avant de terminer."}
            )
        cost_field = DecimalField(
            max_digits=12,
            decimal_places=2,
            min_value=0,
        )
        order.actual_cost = cost_field.run_validation(actual_cost)
        bus = Bus.objects.select_for_update().get(pk=order.bus_id)
        if bus.status != Bus.Status.MAINTENANCE:
            raise ValidationError(
                {"bus": "L'état du bus doit être En maintenance pour terminer cet ordre."}
            )
        if order.odometer_km is not None:
            bus.mileage_km = max(bus.mileage_km, order.odometer_km)
        bus.status = order.previous_bus_status or Bus.Status.AVAILABLE
        bus.save(update_fields=["mileage_km", "status", "updated_at"])
        order.status = MaintenanceOrder.Status.COMPLETED
        order.completed_at = timezone.now()
        order.save(
            update_fields=[
                "actual_cost",
                "status",
                "completed_at",
                "updated_at",
            ]
        )
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def cancel(self, request, pk=None):
        order = self._lock_order(self.get_object())
        if order.status not in {
            MaintenanceOrder.Status.REQUESTED,
            MaintenanceOrder.Status.APPROVED,
        }:
            raise ValidationError(
                {"status": "Cet ordre de maintenance ne peut plus être annulé."}
            )
        order.status = MaintenanceOrder.Status.CANCELLED
        order.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(order).data)
