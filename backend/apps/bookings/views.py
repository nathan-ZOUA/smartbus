from decimal import Decimal

from django.db import transaction
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.fleet.models import Bus
from .models import Booking
from .serializers import BookingSerializer


class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = Booking.objects.select_related("bus", "customer")
        if self.request.user.is_staff or getattr(getattr(self.request.user, "profile", None), "role", "") in {
            "SUPER_ADMIN", "ADMIN", "FLEET_MANAGER"
        }:
            return queryset
        return queryset.filter(customer=self.request.user)

    @transaction.atomic
    def perform_create(self, serializer):
        bus = Bus.objects.select_for_update().get(pk=serializer.validated_data["bus"].pk)
        if bus.status in {
            Bus.Status.MAINTENANCE,
            Bus.Status.OFFLINE,
            Bus.Status.RENTED,
            Bus.Status.SOLD,
            Bus.Status.FOR_SALE,
        }:
            raise ValidationError({"bus": "Ce bus n'est pas disponible à la réservation."})
        start_date = serializer.validated_data["start_date"]
        end_date = serializer.validated_data["end_date"]
        overlaps = Booking.objects.filter(
            bus=bus,
            start_date__lt=end_date,
            end_date__gt=start_date,
        ).exclude(status__in=[Booking.Status.CANCELLED, Booking.Status.COMPLETED])
        if overlaps.exists():
            raise ValidationError({"bus": "Le bus est déjà réservé sur cette période."})
        days = (end_date - start_date).days
        serializer.save(
            customer=self.request.user,
            total_price=bus.daily_rate * Decimal(days),
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        if booking.status != Booking.Status.PENDING:
            raise ValidationError({"status": "Seules les réservations en attente peuvent être annulées."})
        if booking.payment_attempts.filter(status="PENDING").exists():
            raise ValidationError(
                {"status": "Fais d'abord refuser la référence de paiement en attente."}
            )
        booking.status = Booking.Status.CANCELLED
        booking.save(update_fields=["status"])
        return Response(self.get_serializer(booking).data)
