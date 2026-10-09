from django.db import connections
from django.db.utils import DatabaseError
from django.db.models import Sum
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.models import Booking
from apps.fleet.models import Bus


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def api_root(request):
    return Response(
        {
            "name": "SmartBus API",
            "status": "ready",
            "message": "L'API SmartBus est disponible.",
        }
    )


class HealthView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            with connections["default"].cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except DatabaseError:
            return Response({"status": "unhealthy", "database": "unavailable"}, status=503)
        return Response({"status": "ok", "database": "ok"})


class DashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        bookings = Booking.objects.all()
        if not (request.user.is_staff or getattr(getattr(request.user, "profile", None), "role", "") in {
            "SUPER_ADMIN", "ADMIN", "FLEET_MANAGER"
        }):
            bookings = bookings.filter(customer=request.user)
        return Response(
            {
                "fleet": {
                    "total": Bus.objects.count(),
                    "available": Bus.objects.filter(status=Bus.Status.AVAILABLE).count(),
                    "in_service": Bus.objects.filter(status=Bus.Status.IN_SERVICE).count(),
                    "maintenance": Bus.objects.filter(status=Bus.Status.MAINTENANCE).count(),
                },
                "bookings": {
                    "total": bookings.count(),
                    "pending": bookings.filter(status=Booking.Status.PENDING).count(),
                    "confirmed": bookings.filter(status=Booking.Status.CONFIRMED).count(),
                },
                "paid_booking_revenue": bookings.filter(
                    status__in=[Booking.Status.PAID, Booking.Status.COMPLETED]
                ).aggregate(total=Sum("total_price"))["total"] or 0,
                "currency": "XAF",
                "data_notice": "Aucune donnée de démonstration n'est créée automatiquement.",
            }
        )
