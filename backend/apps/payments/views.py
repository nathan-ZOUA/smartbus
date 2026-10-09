from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.bookings.models import Booking
from apps.core.permissions import user_has_role
from apps.core.workflows import bus_has_active_bookings
from apps.fleet.models import Bus
from apps.sales.models import SaleOrder

from .models import PaymentAttempt
from .serializers import PaymentAttemptSerializer, PaymentInstructionsSerializer


PAYMENT_MANAGER_ROLES = {
    "SUPER_ADMIN",
    "ADMIN",
    "FLEET_MANAGER",
    "SALES_AGENT",
}


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def instructions(request):
    data = PaymentInstructionsSerializer(instance={}).data
    return Response(data)


class PaymentAttemptViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentAttemptSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = PaymentAttempt.objects.select_related(
            "customer",
            "booking__bus",
            "sale_order__bus",
            "reviewed_by",
        )
        if user_has_role(self.request.user, PAYMENT_MANAGER_ROLES):
            return queryset
        return queryset.filter(customer=self.request.user)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def verify(self, request, pk=None):
        if not user_has_role(request.user, PAYMENT_MANAGER_ROLES):
            return Response(
                {"detail": "Réservé au gestionnaire des paiements."},
                status=status.HTTP_403_FORBIDDEN,
            )
        payment = PaymentAttempt.objects.select_for_update().get(
            pk=self.get_object().pk
        )
        if payment.status != PaymentAttempt.Status.PENDING:
            raise ValidationError(
                {"status": "Seuls les paiements en attente peuvent être vérifiés."}
            )

        if payment.booking_id:
            booking = Booking.objects.select_for_update().get(pk=payment.booking_id)
            if booking.status not in {
                Booking.Status.PENDING,
                Booking.Status.CONFIRMED,
            }:
                raise ValidationError(
                    {"booking": "La réservation ne peut plus être payée."}
                )
            if payment.amount != booking.total_price:
                raise ValidationError(
                    {"amount": "Le montant de la réservation a changé."}
                )
            booking.status = Booking.Status.PAID
            booking.save(update_fields=["status"])
        else:
            sale_order = SaleOrder.objects.select_for_update().get(
                pk=payment.sale_order_id
            )
            bus = Bus.objects.select_for_update().get(pk=sale_order.bus_id)
            if sale_order.status != SaleOrder.Status.APPROVED:
                raise ValidationError(
                    {"sale_order": "La vente doit être approuvée avant le paiement."}
                )
            if payment.amount != sale_order.amount:
                raise ValidationError(
                    {"amount": "Le montant de la vente a changé."}
                )
            if bus.status != Bus.Status.FOR_SALE:
                raise ValidationError(
                    {"bus": "Le véhicule n'est plus disponible à la vente."}
                )
            if bus.sale_price != sale_order.amount:
                raise ValidationError(
                    {"amount": "Le prix du véhicule a changé depuis l'approbation."}
                )
            if bus_has_active_bookings(bus):
                raise ValidationError(
                    {"bus": "Une réservation active empêche de confirmer cette vente."}
                )
            sale_order.status = SaleOrder.Status.PAID
            sale_order.save(update_fields=["status", "updated_at"])
            bus.status = Bus.Status.SOLD
            bus.save(update_fields=["status", "updated_at"])

        payment.status = PaymentAttempt.Status.VERIFIED
        payment.reviewed_by = request.user
        payment.reviewed_at = timezone.now()
        payment.review_note = ""
        payment.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "review_note",
            ]
        )
        return Response(self.get_serializer(payment).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def reject(self, request, pk=None):
        if not user_has_role(request.user, PAYMENT_MANAGER_ROLES):
            return Response(
                {"detail": "Réservé au gestionnaire des paiements."},
                status=status.HTTP_403_FORBIDDEN,
            )
        payment = PaymentAttempt.objects.select_for_update().get(
            pk=self.get_object().pk
        )
        if payment.status != PaymentAttempt.Status.PENDING:
            raise ValidationError(
                {"status": "Seuls les paiements en attente peuvent être refusés."}
            )
        reason = request.data.get("reason", "").strip()
        if not reason:
            raise ValidationError(
                {"reason": "Indique la raison du refus pour informer le client."}
            )
        if len(reason) > 250:
            raise ValidationError(
                {"reason": "La raison ne peut pas dépasser 250 caractères."}
            )
        payment.status = PaymentAttempt.Status.REJECTED
        payment.reviewed_by = request.user
        payment.reviewed_at = timezone.now()
        payment.review_note = reason
        payment.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "review_note",
            ]
        )
        return Response(self.get_serializer(payment).data)
