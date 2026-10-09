from django.db import transaction
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.core.permissions import user_has_role
from apps.core.workflows import bus_has_active_bookings
from apps.fleet.models import Bus

from .models import SaleOrder
from .serializers import SaleOrderSerializer


SALES_MANAGER_ROLES = {
    "SUPER_ADMIN",
    "ADMIN",
    "FLEET_MANAGER",
    "SALES_AGENT",
}


class SaleOrderViewSet(viewsets.ModelViewSet):
    serializer_class = SaleOrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = SaleOrder.objects.select_related("bus", "customer")
        if user_has_role(self.request.user, SALES_MANAGER_ROLES):
            return queryset
        return queryset.filter(customer=self.request.user)

    @transaction.atomic
    def perform_create(self, serializer):
        bus = Bus.objects.select_for_update().get(
            pk=serializer.validated_data["bus"].pk
        )
        if (
            bus.status != Bus.Status.FOR_SALE
            or bus.sale_price is None
            or bus.sale_price <= 0
        ):
            raise ValidationError(
                {"bus": "Ce véhicule n'est pas proposé à la vente."}
            )
        active_order = SaleOrder.objects.filter(bus=bus).exclude(
            status__in=[SaleOrder.Status.CANCELLED]
        )
        if active_order.exists():
            raise ValidationError(
                {"bus": "Une demande est déjà en cours pour ce véhicule."}
            )
        serializer.save(
            customer=self.request.user,
            amount=bus.sale_price,
            currency="XAF",
        )

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def approve(self, request, pk=None):
        if not user_has_role(request.user, SALES_MANAGER_ROLES):
            return Response(
                {"detail": "Réservé à un gestionnaire commercial."},
                status=403,
            )
        order = self.get_object()
        order = SaleOrder.objects.select_for_update().select_related(
            "bus"
        ).get(pk=order.pk)
        bus = Bus.objects.select_for_update().get(pk=order.bus_id)
        if order.status != SaleOrder.Status.REQUESTED:
            raise ValidationError(
                {"status": "Seules les demandes en attente peuvent être approuvées."}
            )
        if bus.status != Bus.Status.FOR_SALE:
            raise ValidationError(
                {"bus": "Le véhicule n'est plus disponible à la vente."}
            )
        if bus_has_active_bookings(bus):
            raise ValidationError(
                {"bus": "Une réservation active empêche d'approuver cette vente."}
            )
        order.status = SaleOrder.Status.APPROVED
        order.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def cancel(self, request, pk=None):
        order = self.get_object()
        if order.customer_id != request.user.pk and not user_has_role(
            request.user, SALES_MANAGER_ROLES
        ):
            return Response({"detail": "Permission refusée."}, status=403)
        order = SaleOrder.objects.select_for_update().get(pk=order.pk)
        if order.status not in {
            SaleOrder.Status.REQUESTED,
            SaleOrder.Status.APPROVED,
        }:
            raise ValidationError(
                {"status": "Cette vente ne peut plus être annulée ici."}
            )
        if order.payment_attempts.filter(status="PENDING").exists():
            raise ValidationError(
                {"status": "Fais d'abord refuser la référence de paiement en attente."}
            )
        order.status = SaleOrder.Status.CANCELLED
        order.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(order).data)
